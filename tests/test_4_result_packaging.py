from datetime import datetime, timedelta
from pathlib import Path

from MEDS_DEV import __version__ as MEDS_DEV_version
from MEDS_DEV.results import Result


def test_packages_result(packaged_result: Path):
    results_fp = packaged_result

    try:
        result = Result.from_json(results_fp)
    except Exception as e:
        raise AssertionError("Result should be packaged and decodable") from e

    assert result.version == MEDS_DEV_version
    assert result.timestamp < datetime.now() and result.timestamp > datetime.now() - timedelta(hours=2)
