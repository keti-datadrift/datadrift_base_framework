from importlib.metadata import PackageNotFoundError, version as _version

__all__ = ["__version__"]

try:
    __version__ = _version("ddoc")
except PackageNotFoundError:  # running from a source tree without installing
    __version__ = "0.0.0"
