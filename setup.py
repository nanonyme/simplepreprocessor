from __future__ import absolute_import
from setuptools import setup
import os

long_description = "http://github.com/nanonyme/simplepreprocessor"

test_requires = [
    "pytest", "pytest-cov", "mock", "flake8"
]

version = os.environ["VERSION"]

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
    version=version,
    extras_require={"tests": test_requires},
    entry_points={
        "console_scripts": [
            "simplecpreprocessor = simplecpreprocessor.__main__:main"
        ]
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
        ],
    )
