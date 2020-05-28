import re

DEFAULT_LINE_ENDING = "\n"
TOKEN = re.compile((r"<\w+(?:/\w+)*(?:\.\w+)?>|L?\".+\"|'\w'|/\*|"
                    r"\*/|//|\b\w+\b|\r\n|\n|[ \t]+|\W"))
CHAR = re.compile(r"^'\w'$")
CHUNK_MARK = object()
RSTRIP = object()
COMMENT_START = ("/*", "//")
LINE_ENDINGS = ("\r\n", "\n")


def is_string(s):
    return re.search("^L?\".+\"$", s)


def _tokenize(line_no, line, line_ending):
    for match in TOKEN.finditer(line):
        s = match.group(0)
        if s in LINE_ENDINGS:
            s = line_ending
        yield Token.from_string(line_no, s)


class Token(object):
    __slots__ = ["line_no", "value", "whitespace", "chunk_mark"]

    def __init__(self, line_no, value, whitespace):
        self.line_no = line_no
        self.value = value
        self.whitespace = whitespace
        self.chunk_mark = False

    @classmethod
    def from_string(cls, line_no, value):
        return cls(line_no, value, not value.strip())

    @classmethod
    def from_constant(cls, line_no, value):
        return cls(line_no, value, False)

    def __repr__(self):
        return "Line {}, value {!r}".format(self.line_no,
                                            self.value)  # pragma: no cover


class TokenExpander(object):
    def __init__(self, defines):
        self.defines = defines
        self.seen = set()

    def expand_tokens(self, tokens):
        for token in tokens:
            if token.value in self.seen:
                yield token
            else:
                resolved = self.defines.get(token.value, token)
                if resolved is token:
                    yield token
                else:
                    self.seen.add(token.value)
                    for resolved in self.expand_tokens(resolved):
                        yield resolved
                    self.seen.remove(token.value)


class Tokenizer(object):
    NO_COMMENT = Token.from_constant(None, None)

    def __init__(self, f_obj, line_ending):
        self.source = enumerate(f_obj)
        self.line_ending = line_ending

    def __iter__(self):
        comment = self.NO_COMMENT
        token = None
        line_no = 0
        for line_no, line in self.source:
            tokens = _tokenize(line_no, line, self.line_ending)
            token = next(tokens)
            lookahead = None
            for lookahead in tokens:
                if (token.value != "\\" and
                        lookahead.value == self.line_ending):
                    lookahead.chunk_mark = True
                if token.value == "*/" and comment.value == "/*":
                    comment = self.NO_COMMENT
                elif comment is not self.NO_COMMENT:
                    pass
                else:
                    if token.value in COMMENT_START:
                        comment = token
                    else:
                        if token.whitespace:
                            if lookahead.value in COMMENT_START:
                                pass
                            elif lookahead.value == "#":
                                pass
                            else:
                                yield token
                        else:
                            yield token

                token = lookahead
            if comment.value == "//" and token.value != "\\":
                comment = self.NO_COMMENT
            if comment is self.NO_COMMENT:
                if lookahead is None:
                    token.chunk_mark = True
                yield token
        if token is None or not token.chunk_mark:
            token = Token.from_string(line_no, self.line_ending)
            token.chunk_mark = True
            yield token

    def read_chunks(self):
        chunk = []
        for token in self:
            chunk.append(token)
            if token.chunk_mark:
                if chunk:
                    yield chunk
                chunk = []
                continue
