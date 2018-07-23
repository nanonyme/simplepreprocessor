from __future__ import absolute_import
from setuptools import setup

long_description = "http://github.com/nanonyme/simplepreprocessor"

with open("version.txt") as version_file:
    version = version_file.read().strip()

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
