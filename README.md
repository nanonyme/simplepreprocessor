# simplepreprocessor

Usage
---------

import simplecpreprocessor

There will be one function called preprocess. It can either be called with a file object (the assumed way) or a sequence
of lines. Line endings are by default normalized to unix but a parameter can be given to customize this behaviour.


Travis
-----------
![Latest travis build](https://travis-ci.org/nanonyme/simplecpreprocessor.svg?branch=master)

Gotchas
---------

Supported macros: ifdef, ifndef, define, undef

Limitations:
 * multiline defines supported but whitespace rule may not be 1:1 with real preprocessors
 * indirect self-reference not supported. this now raises an error. remove when commented about
 * no magic with the semicolon. if you want a semicolon in the result, write it in your macro