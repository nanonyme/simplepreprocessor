import logging
import os.path
import platform
import re
import argparse
from pkg_resources import get_distribution, DistributionNotFound
try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    from setuptools_scm import get_version
    __version__ = get_version()

logger = logging.getLogger(__name__)


class ParseError(Exception):
    pass


class HeaderHandler(object):

    def __init__(self, include_paths):
        self.include_paths = list(include_paths)
        self.resolved = {}

    def open_local_header(self, current_header, include_header, skip_file):
        header_path = os.path.join(os.path.dirname(current_header),
                                   include_header)
        if skip_file(header_path):
            return SKIP_FILE
        return self._open(header_path)

    def _open(self, header_path):
        try:
            f = open(header_path)
        except IOError:
            return None
        else:
            return f

    def add_include_paths(self, include_paths):
        self.include_paths.extend(include_paths)

    def open_header(self, include_header, skip_file):
        header_path = self.resolved.get(include_header)
        if header_path is not None:
            if skip_file(header_path):
                return SKIP_FILE
            else:
                return self._open(header_path)
        for include_path in self.include_paths:
            header_path = os.path.join(include_path, include_header)
            f = self._open(os.path.normpath(header_path))
            if f:
                self.resolved[include_header] = f.name
                break
        return f


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
DEFAULT_LINE_ENDING = "\n"
PRAGMA_ONCE = "pragma_once"
IFDEF = "ifdef"
IFNDEF = "ifndef"
ELSE = "else"
SKIP_FILE = object()


class Preprocessor(object):

    def __init__(self, line_ending=DEFAULT_LINE_ENDING, include_paths=(),
                 header_handler=None, platform_constants=PLATFORM_CONSTANTS,
                 ignore_headers=()):
        self.defines = {}
        self.ignore_headers = ignore_headers
        self.include_once = {}
        self.defines.update(platform_constants)
        self.constraints = []
        self.ignore = False
        self.ml_define = None
        self.line_ending = line_ending
        self.last_constraint = None
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
            return
        define = line.split(" ", 2)[1:]
        if len(define) == 1:
            self.defines[define[0]] = ""
        else:
            self.defines[define[0]] = define[1]

    def process_endif(self, line, line_num):
        self.verify_no_ml_define()
        if not self.constraints:
            raise ParseError("Unexpected #endif on line %s" % line_num)
        (constraint_type, constraint, ignore,
         original_line_num) = self.constraints.pop()
        if ignore:
            self.ignore = False
        self.last_constraint = constraint, constraint_type, original_line_num

    def process_else(self, line, line_num):
        self.verify_no_ml_define()
        if not self.constraints:
            raise ParseError("Unexpected #else on line %s" % line_num)
        _, constraint, ignore, _ = self.constraints.pop()
        if self.ignore and ignore:
            ignore = False
            self.ignore = False
        elif not self.ignore and not ignore:
            ignore = True
            self.ignore = True
        self.constraints.append((ELSE, constraint, ignore, line_num))

    def process_ifdef(self, line, line_num):
        self.verify_no_ml_define()
        try:
            _, condition = line.split(" ")
        except ValueError:
            raise ValueError(repr(line))
        if not self.ignore and condition not in self.defines:
            self.ignore = True
            self.constraints.append((IFDEF, condition, True, line_num))
        else:
            self.constraints.append((IFDEF, condition, False, line_num))

    def process_pragma(self, line, line_num):
        self.verify_no_ml_define()
        _, _, pragma_name = line.partition(" ")
        method_name = "process_pragma_%s" % pragma_name
        pragma = getattr(self, method_name, None)
        if pragma is None:
            raise Exception("Unsupported pragma %s on line %s" % (pragma_name,
                                                                  line_num))
        else:
            pragma(line, line_num)

    def process_pragma_once(self, line, line_num):
        self.include_once[self.current_name()] = PRAGMA_ONCE

    def current_name(self):
        return self.header_stack[-1].name

    def process_ifndef(self, line, line_num):
        self.verify_no_ml_define()
        _, condition = line.split(" ")
        if not self.ignore and condition in self.defines:
            self.ignore = True
            self.constraints.append((IFNDEF, condition, True, line_num))
        else:
            self.constraints.append((IFNDEF, condition, False, line_num))

    def process_undef(self, line, line_num):
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
        matches = set()
        line = self._recursive_transform(line, matches)
        return line + self.line_ending

    def _recursive_transform(self, line, matches):
        original_line = line
        new_matches = set()

        def transform_word(match):
            word = match.group(0)
            if word in matches:
                return word
            else:
                new_matches.add(word)
                return self.defines.get(word, word)
        line = re.sub(r"\b\w+\b", transform_word, line)
        matches.update(new_matches)
        if original_line == line:
            return line
        else:
            return self._recursive_transform(line, matches)

    def skip_file(self, name):
        item = self.include_once.get(name)
        if item is PRAGMA_ONCE:
            return True
        elif item is None:
            return False
        else:
            constraint, constraint_type = item
            if constraint_type == IFDEF:
                return constraint not in self.defines
            elif constraint_type == IFNDEF:
                return constraint in self.defines
            else:
                raise Exception("Bug, constraint type %s" % constraint_type)

    def process_include(self, line, line_num):
        _, item = line.split(" ", 1)
        s = "%s on line %s includes a file that can't be found" % (line,
                                                                   line_num)
        if item.startswith("<") and item.endswith(">"):
            header = item.strip("<>")
            if header not in self.ignore_headers:
                f = self.headers.open_header(header, self.skip_file)
                if f is None:
                    raise ParseError(s)
                elif f is not SKIP_FILE:
                    with f:
                        for line in self.preprocess(f):
                            yield line
        elif item.startswith('"') and item.endswith('"'):
            header = item.strip('"')
            if header not in self.ignore_headers:
                f = self.headers.open_local_header(self.current_name(), header,
                                                   self.skip_file)
                if f is None:
                    raise ParseError(s)
                elif f is not SKIP_FILE:
                    with f:
                        for line in self.preprocess(f):
                            yield line
        else:
            raise ParseError("Invalid macro %s on line %s" % (line,
                                                              line_num))

    def check_fullfile_guard(self):
        if self.last_constraint is None:
            return
        constraint, constraint_type, begin = self.last_constraint
        if begin != 0:
            return
        self.include_once[self.current_name()] = constraint, constraint_type

    def preprocess(self, f_object, depth=0):
        self.header_stack.append(f_object)
        for line_num, line in enumerate(f_object):
            line = line.rstrip("\r\n")
            maybe_macro, _, _ = line.partition("//")
            maybe_macro = maybe_macro.strip("\t ")
            first_item = maybe_macro.split(" ", 1)[0]
            if line:
                self.last_constraint = None
            if first_item.startswith("#"):
                macro = getattr(self, "process_%s" % first_item[1:], None)
                if macro is None:
                    fmt = "%s on line %s contains unsupported macro"
                    raise ParseError(fmt % (line, line_num))
                else:
                    ret = macro(maybe_macro, line_num)
                    if ret is not None:
                        for line in ret:
                            yield line
            elif self.ml_define:
                self.process_ml_define(line, line_num)
            elif not self.ignore:
                yield self.process_source_line(line, line_num)
        self.check_fullfile_guard()
        self.header_stack.pop()
        if not self.header_stack and self.constraints:
            constraint_type, name, _, line_num = self.constraints[-1]
            if constraint_type is IFDEF:
                fmt = "#ifdef %s from line %s left open"
            elif constraint_type is IFNDEF:
                fmt = "#ifndef %s from line %s left open"
            else:
                fmt = "#else from line %s left open"
            raise ParseError(fmt % (name, line_num))


def preprocess(f_object, line_ending="\n", include_paths=(),
               header_handler=None, platform_constants=PLATFORM_CONSTANTS,
               ignore_headers=()):
    r"""
    This preprocessor yields lines with \n at the end
    """
    preprocessor = Preprocessor(line_ending, include_paths, header_handler,
                                platform_constants, ignore_headers)
    return preprocessor.preprocess(f_object)


def split_paths(path):
    return path.split(os.pathsep)


parser = argparse.ArgumentParser()
parser.add_argument("--input-file", required=True,
                    help="Header file to parse. Can also be a shim header")
parser.add_argument("--include-path", action="append",
                    help="Include paths", dest="include_paths",
                    default=[])
parser.add_argument("--ignore-header", action="append",
                    help="Headers to ignore. Useful for eg CFFI",
                    dest="ignore_headers", default=[])
parser.add_argument("--output-file", required=True,
                    help="Output file that contains preprocessed header(s)")


def main(args=None):
    args = parser.parse_args(args)
    with open(args.input_file) as i:
        with open(args.output_file, "w") as o:
            for line in preprocess(i, include_paths=args.include_paths,
                                   ignore_headers=args.ignore_headers):
                o.write(line)


if __name__ == "__main__":
    main()
