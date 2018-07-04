import logging
import platform
import re
import posixpath

logger = logging.getLogger(__name__)


class ParseError(Exception):
    pass


class HeaderHandler(object):

    def __init__(self, include_paths):
        self.include_paths = list(include_paths)
        self.resolved = {}

    def _open(self, header_path):
        try:
            f = open(header_path)
        except IOError:
            return None
        else:
            return f

    def add_include_paths(self, include_paths):
        self.include_paths.extend(include_paths)

    def _resolve(self, anchor_file):
        if anchor_file is not None:
            yield posixpath.dirname(anchor_file)
        for include_path in self.include_paths:
            yield include_path

    def open_header(self, include_header, skip_file, anchor_file):
        header_path = self.resolved.get(include_header)
        if header_path is not None:
            if skip_file(header_path):
                return SKIP_FILE
            else:
                return self._open(header_path)
        for include_path in self._resolve(anchor_file):
            header_path = posixpath.join(include_path, include_header)
            f = self._open(posixpath.normpath(header_path))
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
TOKEN = re.compile((r"<\w+(?:/\w+)*(?:\.\w+)?>|\".+\"|'\w'|/\*|"
                    r"\*/|//|\b\w+\b|\s+|\W"))
DOUBLE_QUOTE = '"'
SINGLE_QUOTE = "'"
CHAR = re.compile(r"^'\w'$")
CHUNK_MARK = object()
RSTRIP = object()

def _tokenize(s):
    for match in TOKEN.finditer(s):
        yield match.group(0)


class Token(object):
    def __init__(self, line_no, value, whitespace):
        self.line_no = line_no
        self.value = value
        self.whitespace = whitespace

    @classmethod
    def from_string(cls, line_no, value):
        return cls(line_no, value, not value.strip())

    @classmethod
    def from_constant(cls, line_no, value):
        return cls(line_no, value, False)

    def __repr__(self):
        return "Line {}, value {}".format(self.line_no, self.value)
    
class TokenExpander(object):
    def __init__(self, defines):
        self.defines = defines

    def expand_tokens(self, tokens, seen=()):
        for token in tokens:
            if token.value not in self.defines or token.value in seen:
                yield token.value
            else:
                new_seen = [token.value]
                new_seen.extend(seen)
                if len(new_seen) > 20:
                    raise Exception("Stopping with stack %s" % new_seen)
                tokens = self.defines[token.value]
                for token in self.expand_tokens(tokens, new_seen):
                    yield token


class Tokenizer(object):
    def __init__(self, f_obj, line_ending):
        self.source = enumerate(f_obj)
        self.line_ending = line_ending

    def __iter__(self):
        comment = None
        for line_no, line in self.source:
            line = line.rstrip("\r\n")
            tokens = _tokenize(line)
            token = None
            for token in tokens:
                if token == "*/" and comment == "/*":
                    comment = None
                elif comment:
                    continue
                elif token in ("//", "/*"):
                    comment = token
                    yield Token.from_constant(line_no, RSTRIP)
                else:
                    yield Token.from_string(line_no, token)
            if comment == "//":
                if token != "\\":
                    comment = None
            if not comment:
                yield Token.from_string(line_no, self.line_ending)
                if token != "\\":
                    yield Token.from_constant(line_no, CHUNK_MARK)


    def read_chunks(self):
        tokens = iter(self)
        chunk = []
        whitespace_only = True
        for token in tokens:
            if token.value is RSTRIP:
                chunk = chunk[:-1]
                continue
            elif token.value is CHUNK_MARK:
                if chunk:
                    yield chunk
                chunk = []
                whitespace_only = True
                continue
            chunk.append(token)
            if token.value == "#":
                if whitespace_only:
                    chunk = [Token.from_string(token.line_no, "#")]
            elif not token.whitespace:
                whitespace_only = False


class Preprocessor(object):

    def __init__(self, line_ending=DEFAULT_LINE_ENDING, include_paths=(),
                 header_handler=None, platform_constants=PLATFORM_CONSTANTS,
                 ignore_headers=()):
        self.ignore_headers = ignore_headers
        self.include_once = {}
        self.defines = {key: [Token.from_string(None, value)]
                        for key, value in platform_constants.items()}
        self.constraints = []
        self.ignore = False
        self.line_ending = line_ending
        self.last_constraint = None
        self.header_stack = []
        self.token_expander = TokenExpander(self.defines)
        if header_handler is None:
            self.headers = HeaderHandler(include_paths)
        else:
            self.headers = header_handler
            self.headers.add_include_paths(include_paths)

    def process_define(self, **kwargs):
        if self.ignore:
            return
        chunk = kwargs["chunk"]
        for i, tokenized in enumerate(chunk):
            if not tokenized.whitespace:
                define_name = tokenized.value
                break
        self.defines[define_name] = chunk[i+2:-1]

    def process_endif(self, **kwargs):
        line_no = kwargs["line_no"]
        if not self.constraints:
            raise ParseError("Unexpected #endif on line %s" % line_no)
        (constraint_type, constraint, ignore,
         original_line_no) = self.constraints.pop()
        if ignore:
            self.ignore = False
        self.last_constraint = constraint, constraint_type, original_line_no

    def process_else(self, **kwargs):
        line_no = kwargs["line_no"]
        if not self.constraints:
            raise ParseError("Unexpected #else on line %s" % line_no)
        _, constraint, ignore, _ = self.constraints.pop()
        if self.ignore and ignore:
            ignore = False
            self.ignore = False
        elif not self.ignore and not ignore:
            ignore = True
            self.ignore = True
        self.constraints.append((ELSE, constraint, ignore, line_no))

    def process_ifdef(self, **kwargs):
        chunk = kwargs["chunk"]
        line_no = kwargs["line_no"]
        for token in chunk:
            if not token.whitespace:
                condition = token.value
                break
        if not self.ignore and condition not in self.defines:
            self.ignore = True
            self.constraints.append((IFDEF, condition, True, line_no))
        else:
            self.constraints.append((IFDEF, condition, False, line_no))

    def process_pragma(self, **kwargs):
        chunk = kwargs["chunk"]
        line_no = kwargs["line_no"]
        pragma = None
        for token in chunk:
            if not token.whitespace:
                method_name = "process_pragma_%s" % token.value
                pragma = getattr(self, method_name, None)
                break
        if pragma is None:
            raise Exception("Unsupported pragma %s on line %s" % (pragma_name,
                                                                  line_no))
        else:
            pragma(chunk=chunk, line_no=line_no)

    def process_pragma_once(self, **_):
        self.include_once[self.current_name()] = PRAGMA_ONCE

    def current_name(self):
        return self.header_stack[-1].name

    def process_ifndef(self, **kwargs):
        chunk = kwargs["chunk"]
        line_no = kwargs["line_no"]
        for token in chunk:
            if not token.whitespace:
                condition = token.value
                break
        if not self.ignore and condition in self.defines:
            self.ignore = True
            self.constraints.append((IFNDEF, condition, True, line_no))
        else:
            self.constraints.append((IFNDEF, condition, False, line_no))

    def process_undef(self, **kwargs):
        chunk = kwargs["chunk"]
        for token in chunk:
            if not token.whitespace:
                undefine = token.value
                break
        try:
            del self.defines[undefine]
        except KeyError:
            pass

    def process_source_chunks(self, chunk):
        if not self.ignore:
            for chunk in self.token_expander.expand_tokens(chunk):
                yield chunk

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

    def _read_header(self, header, error, anchor_file=None):
        if header not in self.ignore_headers:
            f = self.headers.open_header(header, self.skip_file, anchor_file)
            if f is None:
                raise error
            elif f is not SKIP_FILE:
                with f:
                    for line in self.preprocess(f):
                        yield line

    def process_include(self, **kwargs):
        chunk = kwargs["chunk"]
        line_no = kwargs["line_no"]
        for token in chunk:
            if not token.whitespace:
                item = token.value
                break
        s = "Line %s includes a file %s that can't be found" % (line_no,
                                                                item)
        error = ParseError(s)
        if item.startswith("<") and item.endswith(">"):
            header = item.strip("<>")
            return self._read_header(header, error)
        elif item.startswith('"') and item.endswith('"'):
            header = item.strip('"')
            return self._read_header(header, error, self.current_name())
        else:
            fmt = "Invalid include on line %s, got %r for include name"
            raise ParseError(fmt % (line_no, item))

    def check_fullfile_guard(self):
        if self.last_constraint is None:
            return
        constraint, constraint_type, begin = self.last_constraint
        if begin != 0:
            return
        self.include_once[self.current_name()] = constraint, constraint_type

    def preprocess(self, f_object, depth=0):
        self.header_stack.append(f_object)
        tokenizer = Tokenizer(f_object, self.line_ending)
        for chunk in tokenizer.read_chunks():
            self.last_constraint = None
            if chunk[0].value == "#":
                line_no = chunk[0].line_no
                macro_name = chunk[1].value
                macro_chunk = chunk[2:]
                macro = getattr(self, "process_%s" % macro_name, None)
                if macro is None:
                    fmt = "Line number %s contains unsupported macro %s"
                    raise ParseError(fmt % (line_no, macro_name))
                ret = macro(line_no=line_no, chunk=macro_chunk)
                if ret is not None:
                    for token in ret:
                        yield token
            else:
                for token in self.process_source_chunks(chunk):
                    yield token
        self.check_fullfile_guard()
        self.header_stack.pop()
        if not self.header_stack and self.constraints:
            constraint_type, name, _, line_no = self.constraints[-1]
            if constraint_type is IFDEF:
                fmt = "#ifdef %s from line %s left open"
            elif constraint_type is IFNDEF:
                fmt = "#ifndef %s from line %s left open"
            else:
                fmt = "#else from line %s left open"
            raise ParseError(fmt % (name, line_no))


def preprocess(f_object, line_ending="\n", include_paths=(),
               header_handler=None, platform_constants=PLATFORM_CONSTANTS,
               ignore_headers=()):
    r"""
    This preprocessor yields lines with \n at the end
    """
    preprocessor = Preprocessor(line_ending, include_paths, header_handler,
                                platform_constants, ignore_headers)
    return preprocessor.preprocess(f_object)
