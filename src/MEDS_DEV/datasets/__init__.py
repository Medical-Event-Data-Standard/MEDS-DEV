import dataclasses
from enum import StrEnum, auto
from importlib.resources import files

from omegaconf import OmegaConf

from ..utils import Metadata


class AccessPolicy(StrEnum):
    """Different levels of data accessibility.

    Attributes:
        PUBLIC_WITH_APPROVAL: Data that can be used (in principle) by anyone, but requires approval to access.
        PUBLIC_UNRESTRICTED: Data that can be used by anyone with no restrictions or gating.
        INSTITUTIONAL: Data that is only available within a specific institution or department, but is in
            principle accessible to all researchers within that group. This should not be used for data that
            has only been approved for a single group or a single research process.
        PRIVATE_SINGLE_USE: Data that is only available to a single research group or project, and is not
            available nor likely to ever become available outside of that limited context.
        OTHER: Any other access mode that does not fit into the above categories.
    """

    PUBLIC_WITH_APPROVAL = auto()
    PUBLIC_UNRESTRICTED = auto()
    INSTITUTIONAL = auto()
    PRIVATE_SINGLE_USE = auto()
    OTHER = auto()


@dataclasses.dataclass
class DatasetMetadata(Metadata):
    """Metadata for a dataset.

    Inherits all arguments from the base metadata as well.

    Args:
        access_policy: The level of accessibility of the dataset. Limited to the values in the AccessPolicy
            enum.
        access_details: A string describing the access policy in more detail. May be empty.

    Examples:
        >>> DatasetMetadata(description="foo", contacts=[{"name": "bar"}]) # doctest: +NORMALIZE_WHITESPACE
        DatasetMetadata(description='foo',
                        contacts=[Contact(name='bar', email=None, github_username=None)],
                        links=None,
                        access_policy=<AccessPolicy.PRIVATE_SINGLE_USE: 'private_single_use'>,
                        access_details=None)
        >>> DatasetMetadata(
        ...     description="foo", contacts=[{"name": "bar"}], access_policy="public_unrestricted",
        ...     access_details="baz"
        ... ) # doctest: +NORMALIZE_WHITESPACE
        DatasetMetadata(description='foo',
                        contacts=[Contact(name='bar', email=None, github_username=None)],
                        links=None,
                        access_policy=<AccessPolicy.PUBLIC_UNRESTRICTED: 'public_unrestricted'>,
                        access_details='baz')
        >>> DatasetMetadata(
        ...     description="foo", contacts=[{"name": "bar"}], access_policy="foo"
        ... ) # doctest: +NORMALIZE_WHITESPACE
        Traceback (most recent call last):
            ...
        ValueError: Invalid access policy foo. Must be one of
            'public_with_approval', 'public_unrestricted', 'institutional', 'private_single_use', 'other'
        >>> DatasetMetadata(description="foo", contacts=[{"name": "bar"}], access_policy=None)
        Traceback (most recent call last):
            ...
        ValueError: 'access_policy' must be an instance of AccessPolicy, got <class 'NoneType'>
        >>> DatasetMetadata(description="foo", contacts=[{"name": "bar"}], access_policy="other")
        Traceback (most recent call last):
            ...
        ValueError: access_details must be provided if access_policy is set to AccessPolicy.OTHER
    """

    access_policy: AccessPolicy = AccessPolicy.PRIVATE_SINGLE_USE
    access_details: str | None = None

    def __post_init__(self):
        super().__post_init__()

        if isinstance(self.access_policy, str):
            try:
                self.access_policy = AccessPolicy[self.access_policy.upper()]
            except KeyError:
                raise ValueError(
                    f"Invalid access policy {self.access_policy}. "
                    f"Must be one of {', '.join(repr(a.value) for a in AccessPolicy)}"
                )

        if not isinstance(self.access_policy, AccessPolicy):
            raise ValueError(
                f"'access_policy' must be an instance of AccessPolicy, got {type(self.access_policy)}"
            )
        if self.access_details is not None and not isinstance(self.access_details, str):
            raise ValueError(f"'access_details' must be a string or None, got {type(self.access_details)}")
        if self.access_policy == AccessPolicy.OTHER and self.access_details is None:
            raise ValueError("access_details must be provided if access_policy is set to AccessPolicy.OTHER")


dataset_files = files("MEDS_DEV.datasets")
CFG_YAML = files("MEDS_DEV.configs") / "_build_dataset.yaml"

DATASETS = {}
for path in dataset_files.rglob("*/dataset.yaml"):
    dataset_name = path.relative_to(dataset_files).parent.with_suffix("").as_posix()

    spec = OmegaConf.to_object(OmegaConf.load(path))
    requirements_path = path.parent / "requirements.txt"
    predicates_path = path.parent / "predicates.yaml"
    DATASETS[dataset_name] = {
        "metadata": DatasetMetadata(**spec["metadata"]),
        "commands": spec.get("commands", None),
        "predicates": predicates_path if predicates_path.exists() else None,
        "requirements": requirements_path if requirements_path.exists() else None,
    }

__all__ = ["DATASETS", "CFG_YAML"]
