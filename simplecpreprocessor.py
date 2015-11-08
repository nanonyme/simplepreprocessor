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


def verify_no_ml_define(ml_define):
    if ml_define:
        define, line_num = ml_define
        s = "Error, expected multiline define %s on line %s to be continued"
        raise ParseError(s % (define, line_num))

def process_define(line, line_num, ml_define, defines):
    verify_no_ml_define(ml_define)
    if line.endswith("\\"):
        return line[:-1].rstrip(" \t"), line_num
    define = line.split(" ", 2)[1:]
    if len(define) == 1:
        defines[define[0]] = ""
    else:
        for candidate in defines:
            if candidate in define[1]:
                r = "Indirect self-reference detected #define %s %s, line %s"
                raise ParseError(r % (define[0], define[1], line_num))
        defines[define[0]] = define[1]
    return None

def process_endif(line, line_num, ml_define, constraints):
    verify_no_ml_define(ml_define)
    if not constraints:
        raise ParseError("Unexpected #endif on line %s" % line_num)
    constraints.pop()

def process_if(line, line_num, ml_define, constraints, if_type):
    verify_no_ml_define(ml_define)
    _, condition = line.split(" ")
    constraints.append((condition, if_type, line_num))

def process_undef(line, ml_define, defines):
    verify_no_ml_define(ml_define)
    _, undefine = line.split(" ")
    try:
        del defines[undefine]
    except KeyError:
        pass

def process_ml_define(line, line_num, ml_define, defines):
    define, old_line_num = ml_define
    define = "%s %s" % (define, line.lstrip(" \t"))
    if define.endswith("\\"):
        return define[:-1], old_line_num
    else:
        return process_define(define, old_line_num, None, defines)


def preprocess(iterable, line_ending="\n", strip_include=False):
    r"""
    This preprocessor yields lines with \n at the end
    """
    defines = {}
    constraints = []
    ignore = calculate_ignore(defines, constraints)
    ml_define = None
    for line_num, line in enumerate(iterable):
        line = line.rstrip("\r\n \t").rstrip("\n")
        if line == "#endif":
            process_endif(line, line_num, ml_define, constraints)
            ignore = calculate_ignore(defines, constraints)
        elif line.startswith("#ifdef"):
            process_if(line, line_num, ml_define, constraints, True)
            ignore = calculate_ignore(defines, constraints)
        elif line.startswith("#ifndef"):
            process_if(line, line_num, ml_define, constraints, False)
            ignore = calculate_ignore(defines, constraints)
        elif not ignore:
            if line.startswith("#define"):
                ml_define = process_define(line, line_num, ml_define, defines)
                ignore = calculate_ignore(defines, constraints)
            elif line.startswith("#undef"):
                process_undef(line, ml_define, defines)
                ignore = calculate_ignore(defines, constraints)
            elif line.startswith("#include"):
                if not strip_include:
                    raise ParseError("Includes not (yet) supported")
            elif line.startswith("#"):
                raise ParseError("%s contains unsupported macro" % line)
            else:
                if ml_define:
                    ml_define = process_ml_define(line, line_num,
                                                  ml_define, defines)
                else:
                    for key, value in defines.items():
                        line = line.replace(key, value)
                    yield line + line_ending
    if constraints:
        name, constraint_type, line_num = constraints[-1]
        if constraint_type:
            raise ParseError("#ifdef %s from line %s left open" % (name,
                                                                   line_num))
        else:
            raise ParseError("#ifndef %s from line %s left open" % (name,
                                                                    line_num))
