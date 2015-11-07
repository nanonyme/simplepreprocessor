# simplepreprocessor

Usage
---------

import simplecpreprocessor

There will be one function called preprocess. It can either be called with a file object (the assumed way) or a sequence
of lines. Line endings are normalized to unix.


Gotchas
---------

Supported macros: ifdef, ifndef, define, undef

Limitations:
 * only single-line variant of define is supported
 * indirect self-reference not supported. this now raises an error. remove when commented about
 * no magic with the semicolon. if you want a semicolon in the result, write it in your macro