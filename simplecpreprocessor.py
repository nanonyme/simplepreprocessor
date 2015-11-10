import logging
from collections import OrderedDict

logger = logging.getLogger(__name__)

class ParseError(Exception):
    pass

class Preprocessor(object):
    def __init__(self, line_ending, include_paths=()):
        self.defines = {}
        self.constraints = []
        self.ignore = False
        self.ml_define = None
        self.line_ending = line_ending
        self.include_paths = include_paths


    def verify_no_ml_define(self):
        if self.ml_define:
            define, line_num = self.ml_define
            s = "Error, expected multiline define %s on line %s to be continued"
            raise ParseError(s % (define, line_num))

    def process_define(self, line, line_num):
        if self.ignore:
            return
        self.verify_no_ml_define()
        if line.endswith("\\"):
            self.ml_define = line[:-1].rstrip(" \t"), line_num
        define = line.split(" ", 2)[1:]
        if len(define) == 1:
            self.defines[define[0]] = ""
        else:
            for candidate in self.defines:
                if candidate in define[1]:
                    r = "Indirect self-reference detected #define %s %s, line %s"
                    raise ParseError(r % (define[0], define[1], line_num))
            self.defines[define[0]] = define[1]

    def process_endif(self, line, line_num):
        self.verify_no_ml_define()
        if not self.constraints:
            raise ParseError("Unexpected #endif on line %s" % line_num)
        self.constraints.pop()

    def process_ifdef(self, line, line_num):
        if self.ignore:
            return
        self.verify_no_ml_define()
        _, condition = line.split(" ")
        self.constraints.append((condition, True, line_num))

    def process_ifndef(self, line, line_num):
        if self.ignore:
            return
        self.verify_no_ml_define()
        _, condition = line.split(" ")
        self.constraints.append((condition, False, line_num))

    def process_undef(self, line, line_num):
        if self.ignore:
            return
        self.verify_no_ml_define()
        _, undefine = line.split(" ")
        try:
            del self.defines[undefine]
        except KeyError:
            pass

    def process_ml_define(self, line, line_num):
        if self.ignore:
            return
        define, old_line_num = self.ml_define
        define = "%s %s" % (define, line.lstrip(" \t"))
        if define.endswith("\\"):
            self.ml_define = define[:-1], old_line_num
        else:
            self.ml_define = None
            self.process_define(define, old_line_num)


    def process_source_line(self, line, line_num):
        for key, value in self.defines.items():
            line = line.replace(key, value)
        return line + self.line_ending
        

    def preprocess(self, f_object, depth=0):
        for line_num, line in enumerate(f_object):
            line = line.rstrip("\r\n")
            first_item = line.split(" ", 1)[0]
            if first_item.startswith("#"):
                macro = getattr(self, "process_%s" % first_item[1:], None)
                if macro is None:
                    fmt = "%s on line %s contains unsupported macro"
                    raise ParseError(fmt % (line, line_num))
                else:
                    ret = macro(line, line_num)
                    if ret is not None:
                        for line in ret:
                            yield line
                    self.calculate_ignore()
            elif self.ml_define:
                self.process_ml_define(line, line_num)
                self.calculate_ignore()
            else:
                yield self.process_source_line(line, line_num)                

        if depth == 0 and self.constraints:
            name, constraint_type, line_num = self.constraints[-1]
            if constraint_type:
                fmt = "#ifdef %s from line %s left open"
                raise ParseError("#ifdef %s from line %s left open" % (name,
                                                                       line_num)
                                 )
            else:
                raise ParseError("#ifndef %s from line %s left open" % (name,
                                                                        line_num)
                                 )

    def calculate_ignore(self):
        defines = set(self.defines)
        for key, value, _ in self.constraints:
            if value and key not in defines:
                self.ignore = True
                break
            if not value and key in defines:
                self.ignore = True
                break
        else:
            self.ignore = False

def preprocess(f_object, line_ending="\n", includes=()):
    r"""
    This preprocessor yields lines with \n at the end
    """
    preprocessor = Preprocessor(line_ending, includes)
    return preprocessor.preprocess(f_object)

