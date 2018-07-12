from __future__ import absolute_import
import platform
from simplecpreprocessor.exceptions import ParseError


def calculate_windows_constants(bitness=None):
    if bitness is None:
        bitness, _ = platform.architecture()
    constants = {
        "WIN32": "WIN32", "_WIN64": "_WIN64"}
    if bitness == "64bit":
        constants["WIN64"] = "WIN64"
        constants["_WIN64"] = "_WIN64"
    elif not bitness == "32bit":
        raise Exception("Unsupported bitness %s" % bitness)
    return constants


def calculate_linux_constants(bitness=None):
    if bitness is None:
        bitness, _ = platform.architecture()
    constants = {
        "__linux__": "__linux__"
    }
    if bitness == "32bit":
        constants["__i386__"] = "__i386__"
    elif bitness == "64bit":
        constants["__x86_64__"] = "__x86_64"
    else:
        raise Exception("Unsupported bitness %s" % bitness)
    return constants


def calculate_platform_constants():
    system = platform.system()
    if system == "Windows":
        constants = calculate_windows_constants()
    elif system == "Linux":
        constants = calculate_linux_constants()
    else:
        raise ParseError("Unsupported platform %s" % platform)
    constants["__SIZE_TYPE__"] = "size_t"
    return constants


PLATFORM_CONSTANTS = calculate_platform_constants()
