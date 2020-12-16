"""
simplepreprocessor expands limited set of C preprocessor macros
"""

from simplecpreprocessor.core import preprocess
from simplecpreprocessor.version import __version__

__all__ = ["preprocess", "__version__"]
