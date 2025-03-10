import contextlib
import dataclasses
import hashlib
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import validators
from omegaconf import DictConfig, ListConfig

logger = logging.getLogger(__name__)


def is_valid_email(email: str) -> bool:
    """A simple function to check if an email address is valid.

    Could be replaced with a more robust solution, such as the one provided by the `email-validator` package.

    Args:
        email: Email address to validate.

    Returns:
        True if the email address is valid, False otherwise.

    Examples:
        >>> is_valid_email("foo@bar.com")
        True
        >>> is_valid_email("foo@bar")
        False
        >>> is_valid_email("foobar.com")
        False
    """
    return bool(validators.email(email))


def is_valid_url(url: str) -> bool:
    """Check if a URL is valid.

    Adds 'https://' if the URL is not valid then tries to validate the URL.

    Args:
        url: URL to validate.

    Returns:
        True if the URL is a valid url (though it need not be reachable or exist), False otherwise.

    Examples:
        >>> is_valid_url("https://www.example.com")
        True
        >>> is_valid_url("www.example.com")
        True
        >>> is_valid_url("example.com")
        True
        >>> is_valid_url("example")
        False
    """
    if urlparse(url).scheme == "":
        url = f"https://{url}"

    return bool(validators.url(url))


@dataclasses.dataclass
class Contact:
    """Type-safe representation of a contact person in task, dataset, or model metadata.

    Attributes:
        name: Name of the contact person.
        email: Email address of the contact person. Optional.
        github_username: GitHub username of the contact person. Optional.

    Examples:
        >>> Contact(name="John Doe")
        Contact(name='John Doe', email=None, github_username=None)
        >>> Contact(name="John Doe", email="foo@bar.com", github_username="johndoe")
        Contact(name='John Doe', email='foo@bar.com', github_username='johndoe')
        >>> Contact(name=None)
        Traceback (most recent call last):
            ...
        ValueError: 'name' must be a string. Got None
        >>> Contact(name="foo", email=3)
        Traceback (most recent call last):
            ...
        ValueError: If specified, 'email' must be a string. Got 3
        >>> Contact(name="John Doe", email="foobar")
        Traceback (most recent call last):
            ...
        ValueError: If specified, 'email' must be a valid email address. Got foobar
        >>> Contact(name="John Doe", github_username=3)
        Traceback (most recent call last):
            ...
        ValueError: If specified, 'github_username' must be a string. Got 3
    """

    name: str
    email: str | None = None
    github_username: str | None = None

    def __post_init__(self):
        if type(self.name) is not str:
            raise ValueError(f"'name' must be a string. Got {self.name}")
        if self.email is not None:
            if type(self.email) is not str:
                raise ValueError(f"If specified, 'email' must be a string. Got {self.email}")
            if not is_valid_email(self.email):
                raise ValueError(f"If specified, 'email' must be a valid email address. Got {self.email}")
        if self.github_username is not None and type(self.github_username) is not str:
            raise ValueError(f"If specified, 'github_username' must be a string. Got {self.github_username}")


@dataclasses.dataclass
class Metadata:
    """Type-safe representation of shared metadata for a task, dataset, or model.

    Attributes:
        description: Description of the task, dataset, or model.
        contacts: List of contact persons for the task, dataset, or model. Must have at least one contact.
        links: Optional list of links to additional resources.

    Examples:
        >>> Metadata(description="foo", contacts=[Contact(name="bar")]) # doctest: +NORMALIZE_WHITESPACE
        Metadata(description='foo',
                 contacts=[Contact(name='bar', email=None, github_username=None)],
                 links=None)
        >>> Metadata(description="foo", contacts=[{"name": "bar"}]) # doctest: +NORMALIZE_WHITESPACE
        Metadata(description='foo',
                 contacts=[Contact(name='bar', email=None, github_username=None)],
                 links=None)
        >>> Metadata(
        ...     description="foo", contacts=[{"name": "bar"}], links=["www.example.com"]
        ... ) # doctest: +NORMALIZE_WHITESPACE
        Metadata(description='foo',
                 contacts=[Contact(name='bar', email=None, github_username=None)],
                 links=['www.example.com'])
        >>> Metadata(description=None, contacts=[Contact(name="bar")])
        Traceback (most recent call last):
            ...
        ValueError: 'description' must be a string. Got None
        >>> Metadata(description="foo", contacts=None)
        Traceback (most recent call last):
            ...
        ValueError: 'contacts' must be a list. Got None
        >>> Metadata(description="foo", contacts=[None])
        Traceback (most recent call last):
            ...
        ValueError: Contact at index 0 must be a Contact or dictionary. Got <class 'NoneType'>
        >>> Metadata(description="foo", contacts=[{"baz": "bar"}])
        Traceback (most recent call last):
            ...
        ValueError: Contact at index 0 is invalid...
        >>> Metadata(description="foo", contacts=[{"name": "bar"}], links=3)
        Traceback (most recent call last):
            ...
        ValueError: If specified, 'links' must be a list. Got 3
        >>> Metadata(description="foo", contacts=[{"name": "bar"}], links=[3])
        Traceback (most recent call last):
            ...
        ValueError: Link at index 0 must be a string. Got <class 'int'>
        >>> Metadata(description="foo", contacts=[{"name": "bar"}], links=["3"])
        Traceback (most recent call last):
            ...
        ValueError: Link at index 0 must be a valid URL. Got 3
    """

    description: str
    contacts: list[Contact]
    links: list[str] | None = None

    def __post_init__(self):
        if type(self.description) is not str:
            raise ValueError(f"'description' must be a string. Got {self.description}")
        if not isinstance(self.contacts, (list, ListConfig)):
            raise ValueError(f"'contacts' must be a list. Got {self.contacts}")
        if len(self.contacts) == 0:
            raise ValueError("'contacts' must have at least one contact.")
        for i, contact in enumerate(self.contacts):
            if isinstance(contact, (dict, DictConfig)):
                try:
                    contact = Contact(**contact)
                except Exception as e:
                    raise ValueError(f"Contact at index {i} is invalid") from e
                self.contacts[i] = contact
            elif not isinstance(contact, Contact):
                raise ValueError(f"Contact at index {i} must be a Contact or dictionary. Got {type(contact)}")
        if self.links is not None:
            if not isinstance(self.links, (list, ListConfig)):
                raise ValueError(f"If specified, 'links' must be a list. Got {self.links}")
            for i, link in enumerate(self.links):
                if type(link) is not str:
                    raise ValueError(f"Link at index {i} must be a string. Got {type(link)}")
                if not is_valid_url(link):
                    raise ValueError(f"Link at index {i} must be a valid URL. Got {link}")


def get_venv_bin_path(venv_dir: str | Path) -> Path:
    """Get the bin/Scripts directory of the virtual environment.

    Args:
        venv_dir: Path to the virtual environment's root directory.

    Returns:
        Path to the bin/Scripts directory of the virtual environment, depending on the operating system.

    Examples:
        >>> get_venv_bin_path("path/to/venv")
        PosixPath('path/to/venv/bin')
    """
    # Windows uses "Scripts" instead of "bin"
    # TODO(mmd): Test this properly across operating systems
    if os.name == "nt":  # pragma: no cover
        return Path(venv_dir) / "Scripts"
    else:
        return Path(venv_dir) / "bin"


@contextlib.contextmanager
def tempdir_ctx(cfg: DictConfig) -> Path:
    """Provides a context manager that either yields a temporary directory or a specified directory.

    If a temporary directory is used, it is removed after the context manager exits. Pre-specified directories
    are not removed. The utility of this function is largely to normalize the interface through which
    directory contexts are used when running commands.

    Args:
        cfg: Configuration dictionary that may contain a "temp_dir" key. If the key is present, the specified
             directory is used as the temporary directory. If the key is not present or has a `None` value, a
             temporary directory is created.

    Yields:
        Path to the temporary directory. The returned directory is guaranteed to exist.

    Examples:
        >>> with tempdir_ctx({"temp_dir": None}) as temp_dir:
        ...     print(temp_dir)
        /tmp/...

    We can also specify a directory to use as the temporary directory (in this test, that directory is
    likewise specified within a temporary directory, just to ensure the test cleans up after itself; the
    specified directory can be anything):
        >>> with tempfile.TemporaryDirectory() as root:
        ...     temp_dir = Path(root) / "temp_dir"
        ...     assert not temp_dir.exists()
        ...     with tempdir_ctx({"temp_dir": str(temp_dir)}) as temp_dir:
        ...         print(str(temp_dir.relative_to(Path(root))))
        ...         assert temp_dir.exists()
        ...     assert temp_dir.exists()
        temp_dir
    """
    temp_dir = cfg.get("temp_dir", None)
    if temp_dir is None:
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    else:
        temp_dir = Path(temp_dir)
        temp_dir.mkdir(exist_ok=True, parents=True)
        yield temp_dir


def install_venv(venv_dir: Path, requirements: str | Path) -> Path:
    logger.info(f"Installing requirements from {requirements} into virtual environment.")
    subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)

    venv_bin_path = get_venv_bin_path(venv_dir)
    venv_python = venv_bin_path / "python"
    if not venv_python.exists():
        raise RuntimeError(f"Virtual environment python {venv_python} does not exist!")

    subprocess.run(
        [str(venv_python), "-m", "pip", "install", "-r", str(requirements)],
        check=True,
    )

    logger.info(f"Installed requirements from {requirements} into virtual environment.")
    return venv_bin_path


def file_hash(filepath, algorithm="sha256", chunk_size=4096):
    hash_func = hashlib.new(algorithm)
    with open(filepath, "rb") as file:
        for chunk in iter(lambda: file.read(chunk_size), b""):
            hash_func.update(chunk)
    return hash_func.hexdigest()


@contextlib.contextmanager
def temp_env(cfg: DictConfig, requirements: str | Path | None) -> tuple[Path, dict]:
    with tempdir_ctx(cfg) as build_temp_dir:
        env = os.environ.copy()
        if requirements is not None:
            if cfg.get("venv_dir", None) is not None:
                venv_dir = Path(cfg.venv_dir)
            else:
                venv_dir = build_temp_dir / ".venv"

            check_fp = venv_dir / f".installed.{file_hash(requirements)}.txt"
            venv_bin_path = get_venv_bin_path(venv_dir)

            if check_fp.exists():
                logger.info(f"Requirements already installed in {venv_dir}.")
            elif venv_bin_path.exists():
                any_check_fp = any(venv_dir.glob(".installed.*.txt"))
                if any_check_fp:
                    logger.warning(
                        f"Virtual environment {venv_dir} exists, but requirements check files differ! "
                        "Overwriting."
                    )
                else:
                    logger.warning(f"{venv_dir} exists but no requirements check files found. Overwriting.")
                shutil.rmtree(venv_dir)

            if not check_fp.exists():
                install_venv(venv_dir, requirements)
                check_fp.touch()

            env["VIRTUAL_ENV"] = str(venv_dir.resolve())
            env["PATH"] = f"{str(venv_bin_path.resolve())}{os.pathsep}{env['PATH']}"

        yield build_temp_dir, env


def run_in_env(
    cmd: str,
    output_dir: Path | str,
    env: dict[str, str] | None = None,
    do_overwrite: bool = False,
    cwd: Path | str | None = None,
    run_as_script: bool = True,
) -> subprocess.CompletedProcess:
    if type(output_dir) is str:
        output_dir = Path(output_dir)

    if do_overwrite and output_dir.exists():
        logger.info(f"Removing existing output directory: {output_dir}")
        shutil.rmtree(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    done_file = output_dir / ".done"
    if done_file.is_file():
        logger.info(f"Skipping {cmd} because {done_file} exists.")
        return

    if env is None:
        env = os.environ.copy()

    runner_kwargs = {"env": env, "capture_output": True}

    if run_as_script:
        script_file = output_dir / "cmd.sh"
        script_lines = ["#!/bin/bash", "set -e"]

        script_lines.append(cmd)
        script = "\n".join(script_lines)

        if env.get("VIRTUAL_ENV", None) is not None:
            script_lines.append(f"source {env['VIRTUAL_ENV']}/bin/activate")

        if script_file.is_file():
            if script_file.read_text() != script:
                raise RuntimeError(
                    f"Script file {script_file} already exists and is different from the current script. "
                    f"Existing file:\n{script_file.read_text()}\n"
                    f"New script:\n{script}"
                    "Consider running with do_overwrite=True."
                )
            else:
                logger.info(f"(Matching) script file already exists: {script_file}")
        else:
            script_file.write_text(script)

        script_file.chmod(0o755)

        logger.info(f"Running command in {script_file}:\n{script}")

        cmd = ["bash", str(script_file.resolve())]
        cmd_contents_error = script
        runner_kwargs["shell"] = False
    else:
        logger.info(f"Running command:\n{cmd}")
        cmd_contents_error = cmd
        runner_kwargs["shell"] = True

    if cwd is not None:
        runner_kwargs["cwd"] = cwd

    command_out = subprocess.run(cmd, **runner_kwargs)

    command_errored = command_out.returncode != 0
    if command_errored:
        raise RuntimeError(
            f"Command failed with exit code "
            f"{command_out.returncode}:\n"
            f"SCRIPT:\n{cmd_contents_error}\n"
            f"STDERR:\n{command_out.stderr.decode()}\n"
            f"STDOUT:\n{command_out.stdout.decode()}"
        )
    else:
        done_file.touch()

    return command_out
