"""Models registered by reference: a pinned `source.yaml` instead of a copied `model.yaml`.

A model directory under `src/MEDS_DEV/models/` normally holds the model's `model.yaml` and `requirements.txt`.
For a model that lives in its own GitHub repository (e.g., one generated with the MEDS algorithm template),
the directory can instead hold a `source.yaml` that points at the repository's own `model.yaml`, pinned to a
commit:

```yaml
source:
  repo: https://github.com/org/my-algo
  ref: 3f2c9e1d0b7a4c5e8f9a0b1c2d3e4f5a6b7c8d9e  # full commit SHA
  profile: probe                                # reads algorithms/probe/model.yaml (template layout)
  # path: path/to/model.yaml                    # instead of profile, for other layouts
  sha256: 9b1e...                               # SHA-256 of that model.yaml at ref
  # requirements: ["my-algo @ git+https://github.com/org/my-algo@<ref>"]  # optional override
```

The registry reads `source.yaml` without network access. The first time the model is used, its `model.yaml`
is downloaded at the pinned commit, checked against `sha256`, validated, and cached together with generated
requirements (the repository's `requirements.txt`, with `-e .` replaced by `<package> @ git+<repo>@<ref>`).
Later uses read the cache, so a fetched model also runs offline.
"""

import hashlib
import json
import logging
import os
import re
import shutil
import tempfile
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SOURCE_FILENAME = "source.yaml"
CACHE_ENV_VAR = "MEDS_DEV_SOURCE_CACHE"
TOKEN_ENV_VAR = "GITHUB_TOKEN"
COMPLETE_MARKER = ".complete"

GITHUB_REPO_RE = re.compile(
    r"^https://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<name>[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)
COMMIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SOURCE_KEYS = frozenset({"repo", "ref", "profile", "path", "sha256", "requirements"})
SELF_REQUIREMENT_LINES = frozenset({"-e .", "-e./", "-e ./", "."})

#: Downloads a URL and returns its bytes; raises FileNotFoundError if the URL does not exist.
Fetcher = Callable[[str], bytes]


@dataclass(frozen=True)
class ModelSource:
    """A pinned reference to a `model.yaml` in a GitHub repository.

    Examples:
        >>> source = parse_source({
        ...     "repo": "https://github.com/org/my-algo.git", "ref": "a" * 40, "profile": "probe",
        ...     "sha256": "b" * 64,
        ... })
        >>> source.owner, source.name, source.path
        ('org', 'my-algo', 'algorithms/probe/model.yaml')
        >>> source.raw_url("pyproject.toml")
        'https://raw.githubusercontent.com/org/my-algo/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/pyproject.toml'
        >>> source.pip_url
        'git+https://github.com/org/my-algo@aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
    """

    repo: str
    ref: str
    path: str
    sha256: str | None
    requirements: tuple[str, ...] | None = None

    @property
    def _match(self) -> re.Match:
        return GITHUB_REPO_RE.match(self.repo)

    @property
    def owner(self) -> str:
        return self._match["owner"]

    @property
    def name(self) -> str:
        return self._match["name"]

    @property
    def pip_url(self) -> str:
        return f"git+https://github.com/{self.owner}/{self.name}@{self.ref}"

    def raw_url(self, path: str) -> str:
        return f"https://raw.githubusercontent.com/{self.owner}/{self.name}/{self.ref}/{path}"


def parse_source(spec: Mapping[str, Any]) -> ModelSource:
    """Parses and validates the `source` block of a `source.yaml`.

    Examples:
        >>> base = {"repo": "https://github.com/org/m", "ref": "a" * 40, "profile": "probe", "sha256": "b" * 64}
        >>> def check(**changes):
        ...     spec = {k: v for k, v in {**base, **changes}.items() if v is not None}
        ...     try:
        ...         return parse_source(spec)
        ...     except ValueError as e:
        ...         print(e)
        >>> check(path="custom/model.yaml", profile=None).path
        'custom/model.yaml'
        >>> check(repo="https://gitlab.com/org/m")
        source.repo must be a GitHub repository URL (https://github.com/<owner>/<name>); got 'https://gitlab.com/org/m'.
        >>> check(ref="main")
        source.ref must be a full 40-character commit SHA, not a branch or tag; got 'main'.
        >>> check(sha256=None).sha256 is None
        True
        >>> check(path="x/model.yaml")
        Set exactly one of source.profile or source.path.
        >>> check(path="../model.yaml", profile=None)
        source.path must be a relative path inside the repository; got '../model.yaml'.
        >>> check(revision="x")
        source has unknown key(s) ['revision']; allowed keys are ['path', 'profile', 'ref', 'repo', 'requirements', 'sha256'].
        >>> check(requirements="pkg")
        source.requirements must be a list of requirement lines.
        >>> check(requirements=["pkg==1.0"]).requirements
        ('pkg==1.0',)
    """  # noqa: E501
    if not isinstance(spec, Mapping):
        raise ValueError("source.yaml must contain a `source` mapping.")
    unknown = sorted(set(spec) - SOURCE_KEYS)
    if unknown:
        raise ValueError(f"source has unknown key(s) {unknown}; allowed keys are {sorted(SOURCE_KEYS)}.")

    repo = spec.get("repo")
    if not isinstance(repo, str) or not GITHUB_REPO_RE.match(repo):
        raise ValueError(
            f"source.repo must be a GitHub repository URL (https://github.com/<owner>/<name>); got {repo!r}."
        )
    ref = spec.get("ref")
    if not isinstance(ref, str) or not COMMIT_SHA_RE.match(ref):
        raise ValueError(
            f"source.ref must be a full 40-character commit SHA, not a branch or tag; got {ref!r}."
        )
    # A missing sha256 is accepted here (so the registry still loads) but rejected when the model is fetched,
    # with the hash to review and pin.
    sha256 = spec.get("sha256")
    if sha256 is not None and (not isinstance(sha256, str) or not SHA256_RE.match(sha256)):
        raise ValueError(f"source.sha256 must be a 64-character lowercase hex SHA-256; got {sha256!r}.")

    profile, path = spec.get("profile"), spec.get("path")
    if (profile is None) == (path is None):
        raise ValueError("Set exactly one of source.profile or source.path.")
    if profile is not None:
        if not isinstance(profile, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", profile):
            raise ValueError(f"source.profile must be a profile name such as 'probe'; got {profile!r}.")
        path = f"algorithms/{profile}/model.yaml"
    if not isinstance(path, str) or path.startswith("/") or ".." in Path(path).parts or not path.strip():
        raise ValueError(f"source.path must be a relative path inside the repository; got {path!r}.")

    requirements = spec.get("requirements")
    if requirements is not None:
        if isinstance(requirements, str) or not all(isinstance(r, str) for r in requirements):
            raise ValueError("source.requirements must be a list of requirement lines.")
        requirements = tuple(requirements)

    return ModelSource(repo=repo, ref=ref, path=path, sha256=sha256, requirements=requirements)


def http_fetch(url: str, timeout: float = 60) -> bytes:
    """Downloads `url`, sending `$GITHUB_TOKEN` (if set) to GitHub hosts to allow private repositories."""
    request = urllib.request.Request(url, headers={"User-Agent": "MEDS-DEV"})
    token = os.environ.get(TOKEN_ENV_VAR)
    if token and urllib.parse.urlparse(url).hostname in {"raw.githubusercontent.com", "github.com"}:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise FileNotFoundError(f"{url} does not exist (or is private; set {TOKEN_ENV_VAR}).") from e
        raise


def default_cache_dir() -> Path:
    """Returns `$MEDS_DEV_SOURCE_CACHE`, else `$XDG_CACHE_HOME/meds_dev/sources` (default `~/.cache/...`)."""
    if os.environ.get(CACHE_ENV_VAR):
        return Path(os.environ[CACHE_ENV_VAR])
    base = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return base / "meds_dev" / "sources"


def package_name(pyproject_text: str) -> str | None:
    """Returns `[project].name` from a pyproject.toml.

    Examples:
        >>> package_name('[project]\\nname = "my-algo"\\n')
        'my-algo'
        >>> package_name('[tool.ruff]\\nline-length = 100\\n') is None
        True
    """
    return tomllib.loads(pyproject_text).get("project", {}).get("name")


def generate_requirements(source: ModelSource, fetch: Fetcher) -> str:
    """Builds the requirements that install the model at the pinned commit.

    The repository's `requirements.txt` is used with `-e .` replaced by `<package> @ git+<repo>@<ref>`; the
    package line is added if `requirements.txt` does not install the repository itself.

    Examples:
        >>> source = parse_source({"repo": "https://github.com/org/m", "ref": "a" * 40, "profile": "probe",
        ...                        "sha256": "b" * 64})
        >>> files = {
        ...     source.raw_url("pyproject.toml"): b'[project]\\nname = "my-algo"\\n',
        ...     source.raw_url("requirements.txt"): b"-e .\\ntorch==2.5.1\\n",
        ... }
        >>> def fetch(url):
        ...     if url not in files:
        ...         raise FileNotFoundError(url)
        ...     return files[url]
        >>> print(generate_requirements(source, fetch))
        my-algo @ git+https://github.com/org/m@aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
        torch==2.5.1
        >>> del files[source.raw_url("requirements.txt")]
        >>> print(generate_requirements(source, fetch))
        my-algo @ git+https://github.com/org/m@aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
        >>> del files[source.raw_url("pyproject.toml")]
        >>> generate_requirements(source, fetch)
        Traceback (most recent call last):
            ...
        ValueError: https://github.com/org/m has no pyproject.toml with a [project] name at the pinned commit,
        so MEDS-DEV cannot install it. Set source.requirements explicitly.
        >>> print(generate_requirements(parse_source({"repo": "https://github.com/org/m", "ref": "a" * 40,
        ...     "profile": "probe", "sha256": "b" * 64, "requirements": ["pkg==1.0"]}), fetch))
        pkg==1.0
    """
    if source.requirements is not None:
        return "\n".join(source.requirements) + "\n"

    try:
        name = package_name(fetch(source.raw_url("pyproject.toml")).decode())
    except FileNotFoundError:
        name = None
    if not name:
        raise ValueError(
            f"{source.repo} has no pyproject.toml with a [project] name at the pinned commit, so MEDS-DEV "
            "cannot install it. Set source.requirements explicitly."
        )
    self_line = f"{name} @ {source.pip_url}"

    try:
        lines = fetch(source.raw_url("requirements.txt")).decode().splitlines()
    except FileNotFoundError:
        lines = []
    has_self = any(line.strip() in SELF_REQUIREMENT_LINES for line in lines)
    lines = [self_line if line.strip() in SELF_REQUIREMENT_LINES else line for line in lines]
    if not has_self:
        lines.insert(0, self_line)
    return "\n".join(line for line in lines if line.strip()) + "\n"


def source_cache_dir(source: ModelSource, cache_dir: Path | None = None) -> Path:
    """Returns where a source's files are cached: `<cache>/<owner>/<name>/<ref>/<model.yaml directory>/`."""
    root = Path(cache_dir) if cache_dir else default_cache_dir()
    return root / source.owner / source.name / source.ref / Path(source.path).parent


def resolve_source(source: ModelSource, cache_dir: Path | None = None, fetch: Fetcher = http_fetch) -> Path:
    """Fetches the pinned `model.yaml` (once), verifies its hash and writes requirements next to it.

    Returns the cache directory, which holds `model.yaml`, `requirements.txt` and `source.json`.

    Examples:
        >>> model_yaml = b"metadata: {description: d, contacts: [{name: n}]}\\ncommands: {supervised: {predict: p}}\\n"
        >>> digest = hashlib.sha256(model_yaml).hexdigest()
        >>> source = parse_source({"repo": "https://github.com/org/m", "ref": "a" * 40, "profile": "probe",
        ...                        "sha256": digest, "requirements": ["pkg==1.0"]})
        >>> calls = []
        >>> def fetch(url):
        ...     calls.append(url)
        ...     return model_yaml
        >>> with tempfile.TemporaryDirectory() as d:
        ...     out = resolve_source(source, Path(d), fetch)
        ...     print(sorted(p.name for p in out.iterdir()))
        ...     _ = resolve_source(source, Path(d), fetch)  # cached: no second download
        ...     print(len(calls))
        ['.complete', 'model.yaml', 'requirements.txt', 'source.json']
        1

    A changed file at the pinned path is rejected, with the hash to review and pin:
        >>> bad = parse_source({"repo": "https://github.com/org/m", "ref": "a" * 40, "profile": "probe",
        ...                     "sha256": "0" * 64, "requirements": []})
        >>> with tempfile.TemporaryDirectory() as d:
        ...     resolve_source(bad, Path(d), fetch)
        Traceback (most recent call last):
            ...
        ValueError: The model.yaml at https://github.com/org/m@aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
        (algorithms/probe/model.yaml) has SHA-256 ..., but source.yaml expects 000.... Review the file and,
        if it is correct, set source.sha256 to ....

    So is a source without a pinned hash, which is how a new source.yaml gets its hash:
        >>> unpinned = parse_source({"repo": "https://github.com/org/m", "ref": "a" * 40, "profile": "probe"})
        >>> with tempfile.TemporaryDirectory() as d:
        ...     resolve_source(unpinned, Path(d), fetch)
        Traceback (most recent call last):
            ...
        ValueError: source.sha256 is not set. The model.yaml at https://github.com/org/m@aaaa...
        (algorithms/probe/model.yaml) has SHA-256 .... Review the file and, if it is correct, set source.sha256
        to ....
    """  # noqa: E501
    target = source_cache_dir(source, cache_dir)
    if source.sha256 is not None and (target / COMPLETE_MARKER).is_file():
        digest = hashlib.sha256((target / "model.yaml").read_bytes()).hexdigest()
        if digest == source.sha256:
            return target
        logger.warning(f"Cached {target / 'model.yaml'} does not match source.sha256; fetching it again.")

    logger.info(f"Fetching {source.path} from {source.repo}@{source.ref}")
    model_yaml = fetch(source.raw_url(source.path))
    digest = hashlib.sha256(model_yaml).hexdigest()
    if source.sha256 is None:
        raise ValueError(
            f"source.sha256 is not set. The model.yaml at {source.repo}@{source.ref} ({source.path}) has "
            f"SHA-256 {digest}. Review the file and, if it is correct, set source.sha256 to {digest}."
        )
    if digest != source.sha256:
        raise ValueError(
            f"The model.yaml at {source.repo}@{source.ref} ({source.path}) has SHA-256 {digest}, but "
            f"source.yaml expects {source.sha256}. Review the file and, if it is correct, set source.sha256 "
            f"to {digest}."
        )
    requirements = generate_requirements(source, fetch)

    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))
    try:
        (staging / "model.yaml").write_bytes(model_yaml)
        (staging / "requirements.txt").write_text(requirements)
        provenance = {"repo": source.repo, "ref": source.ref, "path": source.path, "sha256": source.sha256}
        (staging / "source.json").write_text(json.dumps(provenance, indent=2) + "\n")
        (staging / COMPLETE_MARKER).touch()
        if target.exists():
            shutil.rmtree(target)
        os.replace(staging, target)
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
    return target


def read_source_file(source_fp: Path) -> ModelSource:
    """Reads and validates a `source.yaml` file (no network access)."""
    from omegaconf import OmegaConf

    spec = OmegaConf.to_container(OmegaConf.load(source_fp), resolve=True)
    if not isinstance(spec, Mapping) or set(spec) != {"source"}:
        raise ValueError(f"{source_fp} must contain exactly one top-level key, `source`.")
    return parse_source(spec["source"])


__all__ = [
    "SOURCE_FILENAME",
    "ModelSource",
    "default_cache_dir",
    "generate_requirements",
    "http_fetch",
    "parse_source",
    "read_source_file",
    "resolve_source",
]
