# simplepreprocessor

Usage
---------

import simplecpreprocessor

There will be one function called preprocess. It can either be called with a file object or something that
looks sufficiently like a file object. See unit tests to find out what's enough for a compatible wrapper.
Line endings are by default normalized to unix but a parameter can be given to customize this behaviour.


Travis
-----------
![Latest travis build](https://travis-ci.org/nanonyme/simplecpreprocessor.svg?branch=master)

Gotchas
---------

Supported macros: ifdef, ifndef, define, undef, include

Limitations:
 * multiline defines supported but whitespace handling may not be 1:1 with
   real preprocessors. trailing whitespace is removed, indentation from first
   line is removed
 * indirect self-reference not supported. this now raises an error. remove
   when commented about
 * no magic with the semicolon. if you want a semicolon in the result, write
   it in your macro