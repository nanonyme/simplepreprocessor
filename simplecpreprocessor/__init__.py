from simplecpreprocessor.core import preprocess
from pkg_resources import get_distribution
__version__ = get_distribution(__name__).version

__all__ = ["preprocess", "__version__"]
