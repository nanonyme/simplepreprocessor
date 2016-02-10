from setuptools import setup

setup(
    name = "simplecpreprocessor",
    version = "0.1.2",
    author = "Seppo Yli-Olli",
    author_email = "seppo.yli-olli@iki.fi",
    description = "Simple C preprocessor for usage eg before CFFI",
    keywords = "python c preprocessor",
    license = "BSD",
    url = "https://github.com/nanonyme/simplecpreprocessor",
    py_modules=["simplecpreprocessor"],
    long_description="""TravisCI results 
    .. image:: https://travis-ci.org/nanonyme/simplecpreprocessor.svg?branch=master""",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
        ],
    )
