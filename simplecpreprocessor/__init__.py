"""
simplepreprocessor expands limited set of C preprocessor macros
"""

from .core import preprocess
from .version import __version__

__all__ = ["preprocess", "__version__"]
