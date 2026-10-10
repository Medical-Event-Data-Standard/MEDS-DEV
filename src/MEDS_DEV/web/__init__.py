"""Web tooling: collate entities, aggregate results, and process result submissions."""

from .aggregate_results import aggregate_results
from .collate_entities import collate_entities
from .process_submission import extract_result_dict_from_issue_body, process_submission

__all__ = [
    "aggregate_results",
    "collate_entities",
    "extract_result_dict_from_issue_body",
    "process_submission",
]
