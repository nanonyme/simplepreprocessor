from __future__ import absolute_import
from setuptools import setup

long_description = "http://github.com/nanonyme/simplepreprocessor"

setup(
    name="simplecpreprocessor",
    author="Seppo Yli-Olli",
    author_email="seppo.yli-olli@iki.fi",
    description="Simple C preprocessor for usage eg before CFFI",
    keywords="python c preprocessor",
    license="BSD",
    url="https://github.com/nanonyme/simplecpreprocessor",
    packages=["simplecpreprocessor"],
    long_description=long_description,
    use_scm_version=True,
    entry_points={
        "console_scripts": [
            "simplecpreprocessor = simplecpreprocessor:main"
        ]
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
        ],
    )
