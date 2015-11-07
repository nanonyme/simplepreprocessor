import logging
from collections import OrderedDict

logger = logging.getLogger(__name__)

def calculate_ignore(defines, constraints):
    defines = set(defines)
    for key, value in constraints:
        if value and key not in defines:
            return True
        if not value and key in defines:
            return True
    return False

class ParseError(Exception):
    pass


def preprocess(iterable):
    r"""
    This preprocessor yields lines with \n at the end
    """
    defines = {}
    defined = object()
    constraints = []
    ignore = calculate_ignore(defines, constraints)
    for line_num, line in enumerate(iterable):
        line = line.rstrip("\r\n").rstrip("\n")
        if line == "#endif":
            if not constraints:
                raise Exception("Unexpected #endif on line %s" % line_num)
            constraints.pop()
            ignore = calculate_ignore(defines, constraints)
        elif line.startswith("#ifdef"):
            _, define = line.split(" ")
            constraints.append((define, True))
            ignore = calculate_ignore(defines, constraints)
        elif line.startswith("#ifndef"):
            _, define = line.split(" ")
            constraints.append((define, False))
            ignore = calculate_ignore(defines, constraints)
        elif not ignore:
            if line.startswith("#define"):
                define = line.split(" ", 2)[1:]
                if len(define) == 1:
                    defines[define[0]] = defined
                else:
                    defines[define[0]] = define[1]
                ignore = calculate_ignore(defines, constraints)
            elif line.startswith("#undef"):
                _, undefine = line.split(" ")
                try:
                    del defines[undefine]
                except KeyError:
                    pass
                ignore = calculate_ignore(defines, constraints)
            elif line.startswith("#"):
                raise ParseError("%s contains unsupported macro" % line)
            else:
                for key, value in defines.items():
                    if value is not defined:
                        line = line.replace(key, value)
                yield line + "\n"
