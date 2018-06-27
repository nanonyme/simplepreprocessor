from simplecpreprocessor.core import preprocess
from pkg_resources import get_distribution, DistributionNotFound
try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    from setuptools_scm import get_version
    __version__ = get_version()                

__all__ = ["preprocess"]
