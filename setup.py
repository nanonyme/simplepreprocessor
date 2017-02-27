from __future__ import absolute_import
from setuptools import setup

long_description="""TravisCI results                                        
    .. image:: https://travis-ci.org/nanonyme/simplecpreprocessor.svg
"""


setup(
    name = "simplecpreprocessor",
    author = "Seppo Yli-Olli",
    author_email = "seppo.yli-olli@iki.fi",
    description = "Simple C preprocessor for usage eg before CFFI",
    keywords = "python c preprocessor",
    license = "BSD",
    url = "https://github.com/nanonyme/simplecpreprocessor",
    py_modules=["simplecpreprocessor"],
    long_description=long_description,
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
        ],
    )
