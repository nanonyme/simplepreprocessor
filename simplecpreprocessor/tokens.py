import re

DEFAULT_LINE_ENDING = "\n"
TOKEN = re.compile((r"<\w+(?:/\w+)*(?:\.\w+)?>|L?\".+\"|'\w'|/\*|"
                    r"\*/|//|\b\w+\b|\r\n|\n|[ \t]+|\W"))
DOUBLE_QUOTE = '"'
SINGLE_QUOTE = "'"
CHAR = re.compile(r"^'\w'$")
CHUNK_MARK = object()
RSTRIP = object()
COMMENT_START = ("/*", "//")
LINE_ENDINGS = ("\r\n", "\n")


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
        return "Line {}, value {!r}".format(self.line_no, self.value)


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
    NO_COMMENT = Token.from_constant(None, None)

    def __init__(self, f_obj, line_ending):
        self.source = enumerate(f_obj)
        self.line_ending = line_ending

    def __iter__(self):
        comment = self.NO_COMMENT
        for line_no, line in self.source:
            tokens = _tokenize(line_no, line, self.line_ending)
            token = next(tokens, None)
            if token is None:
                continue
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
                            if (lookahead.whitespace and
                                    lookahead.value != self.line_ending):
                                token.value += lookahead.value
                                continue
                            elif lookahead.value in COMMENT_START:
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