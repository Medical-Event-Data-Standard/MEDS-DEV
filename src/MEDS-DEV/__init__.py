from importlib.metadata import PackageNotFoundError, version

__package_name__ = "MEDS-DEV"
try:
    __version__ = version(__package_name__)
except PackageNotFoundError:
    __version__ = "unknown"
