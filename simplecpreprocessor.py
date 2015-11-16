import logging
from collections import OrderedDict
import os.path
import platform
import errno

logger = logging.getLogger(__name__)

class ParseError(Exception):
    pass


class HeaderHandler(object):
    def __init__(self, include_paths):
        self.include_paths = list(include_paths)

    def open_local_header(self, current_header, include_header):
        ret = os.path.join(os.path.dirname(root_dir), include_header)
        try:
            f = open(ret)
        except IOError as e:
            return None
        else:
            return ret

    def add_include_paths(self, include_paths):
        self.include_paths.extend(include_paths)

    def open_header(include_header):
        for include_path in include_paths:
            ret = os.path.join(include_path, include_header)
            try:
                f = open(ret)
            except IOError as e:
                continue
            else:
                return f
        return None

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

class Preprocessor(object):
    def __init__(self, line_ending, include_paths=(), header_handler=None,
                 platform_constants=None, ignore_headers=()):
        self.defines = {}
        self.ignore_headers = ignore_headers
        if platform_constants is None:
            system = platform.system()
            if system == "Windows":
                self.defines.update(calculate_windows_constants())
            elif system == "Linux":
                self.defines.update(calculate_linux_constants())
            else:
                raise ParseError("Unsupported platform %s" % platform)
        else:
            self.defines.update(platform_constants)
        self.constraints = []
        self.ignore = False
        self.ml_define = None
        self.line_ending = line_ending
        self.header_stack = []
        if header_handler is None:
            self.headers = HeaderHandler(include_paths)
        else:
            self.headers = header_handler
            self.headers.add_include_paths(include_paths)

    def verify_no_ml_define(self):
        if self.ml_define:
            define, line_num = self.ml_define
            s = ("Error, expected multiline define %s on "
                 "line %s to be continued")
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
                    r = ("Indirect self-reference detected "
                         "#define %s %s, line %s")
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

    def process_include(self, line, line_num):
        _, item = line.split(" ", 1)
        s = "%s on line %s includes a file that can't be found" % (line,
                                                                   line_num)
        if item.startswith("<") and item.endswith(">"):
            header = item.strip("<>")
            if header not in self.ignore_headers:
                f = self.headers.open_header(header)
                if f is None:
                    raise ParseError(s)
                with f:
                    for line in self.preprocess(f):
                        yield line
        elif item.startswith('"') and item.endswith('"'):
            current = self.header_stack[-1]
            header = item.strip('"')
            if header not in self.ignore_headers:
                f = self.headers.open_local_header(current.name, header)
                if f is None:
                    raise ParseError(s)
                with f:
                    for line in self.preprocess(f):
                        yield line
        else:
            raise ParseError("Invalid macro %s on line %s" % (line,
                                                              line_num))
        

    def preprocess(self, f_object, depth=0):
        self.header_stack.append(f_object)
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
        self.header_stack.pop()
        if not self.header_stack and self.constraints:
            name, constraint_type, line_num = self.constraints[-1]
            if constraint_type:
                fmt = "#ifdef %s from line %s left open"
            else:
                fmt = "#ifndef %s from line %s left open"
            raise ParseError(fmt % (name, line_num))


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

def preprocess(f_object, line_ending="\n", include_paths=(),
               header_handler=None, platform_constants=None,
               ignore_headers=()):
    r"""
    This preprocessor yields lines with \n at the end
    """
    preprocessor = Preprocessor(line_ending, include_paths, header_handler,
                                platform_constants, ignore_headers)
    return preprocessor.preprocess(f_object)

