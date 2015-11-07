import logging
from collections import OrderedDict

logger = logging.getLogger(__name__)

def calculate_ignore(defines, constraints):
    defines = set(defines)
    for key, value, _ in constraints:
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
    constraints = []
    ignore = calculate_ignore(defines, constraints)
    for line_num, line in enumerate(iterable):
        line = line.rstrip("\r\n").rstrip("\n")
        if line == "#endif":
            if not constraints:
                raise ParseError("Unexpected #endif on line %s" % line_num)
            constraints.pop()
            ignore = calculate_ignore(defines, constraints)
        elif line.startswith("#ifdef"):
            _, define = line.split(" ")
            constraints.append((define, True, line_num))
            ignore = calculate_ignore(defines, constraints)
        elif line.startswith("#ifndef"):
            _, define = line.split(" ")
            constraints.append((define, False, line_num))
            ignore = calculate_ignore(defines, constraints)
        elif not ignore:
            if line.startswith("#define"):
                define = line.split(" ", 2)[1:]
                if len(define) == 1:
                    defines[define[0]] = ""
                else:
                    for candidate in defines:
                        if candidate in define[1]:
                            r = "Indirect self-reference detected #define %s %s, line %s"
                            raise ParseError(r % (define[0], define[1], line_num))
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
                    line = line.replace(key, value)
                yield line + "\n"
    if constraints:
        name, constraint_type, line_num = constraints[-1]
        if constraint_type:
            raise ParseError("#ifdef %s from line %s left open" % (name, line_num))
        else:
            raise ParseError("#ifndef %s from line %s left open" % (name, line_num))
