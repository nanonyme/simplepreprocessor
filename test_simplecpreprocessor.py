import unittest
import simplecpreprocessor

class FakeFile(object):
    def __init__(self, name, contents):
        self.name = name
        self.contents = contents

    def __iter__(self):
        for line in self.contents:
            yield line


class TestSimpleCPreprocessor(unittest.TestCase):
    def run_case(self, input_list, expected_list):
        output_list = list(simplecpreprocessor.preprocess(input_list))
        self.assertEqual(output_list, expected_list)

    def test_define(self):
        f_obj = FakeFile("header.h", ["#define FOO 1\n", "FOO"])
        expected_list = ["1\n"]
        self.run_case(f_obj, expected_list)

    def test_multiline_define(self):
        f_obj = FakeFile("header.h", ["#define FOO \\\n", "\t1\n", "FOO\n"])
        expected_list = ["1\n"]
        self.run_case(f_obj, expected_list)

    def test_define_simple_self_referential(self):
        f_obj = FakeFile("header.h", ["#define FOO FOO\n", "FOO\n"])
        expected_list = ["FOO\n"]
        self.run_case(f_obj, expected_list)

    @unittest.expectedFailure
    def test_define_indirect_self_reference(self):
        f_obj = FakeFile("header.h", ["#define x (4 + y)\n",
                                      "#define y (2 * x)\n",
                                      "x\n", "y\n"])
        expected_list = ["(4 + (2 * x))\n", "(2 * (4 + y)\n"]
        self.run_case(f_obj, expected_list)

    def test_blank_define(self):
        f_obj = FakeFile("header.h", ["#define FOO\n", "FOO\n"])
        expected_list = ["\n"]
        self.run_case(f_obj, expected_list)

    def test_undefine(self):
        f_obj = FakeFile("header.h", ["#define FOO 1\n", "#undef FOO\n", "FOO"])
        expected_list = ["FOO\n"]
        self.run_case(f_obj, expected_list)

    def test_define_undefine(self):
        f_obj = FakeFile("header.h", ["#define FOO 1\n", "#undef FOO\n", "FOO"])
        expected_list = ["FOO\n"]
        self.run_case(f_obj, expected_list)

    def test_extra_endif_causes_error(self):
        input_list = ["#endif\n"]
        with self.assertRaises(simplecpreprocessor.ParseError):
            list(simplecpreprocessor.preprocess(input_list))

    def test_ifdef_left_open_causes_error(self):
        f_obj = FakeFile("header.h", ["#ifdef FOO\n"])
        with self.assertRaises(simplecpreprocessor.ParseError):
            list(simplecpreprocessor.preprocess(f_obj))

    def test_ifndef_left_open_causes_error(self):
        f_obj = FakeFile("header.h", ["#ifndef FOO\n"])
        with self.assertRaises(simplecpreprocessor.ParseError):
            list(simplecpreprocessor.preprocess(f_obj))

    def test_unexpected_macro_gives_parse_error(self):
        f_obj = FakeFile("header.h", ["#something_unsupported foo bar\n"])
        with self.assertRaises(simplecpreprocessor.ParseError):
            list(simplecpreprocessor.preprocess(f_obj))

    def test_ifndef_unfulfilled_define_ignored(self):
        f_obj = FakeFile("header.h", ["#define FOO\n", "#ifndef FOO\n", "#define BAR 1\n",
                                      "#endif\n", "BAR\n"])
        expected_list = ["BAR\n"]
        self.run_case(f_obj, expected_list)


    def test_ifdef_unfulfilled_define_ignored(self):
        f_obj = FakeFile("header.h", ["#ifdef FOO\n", "#define BAR 1\n", "#endif\n", "BAR\n"])
        expected_list = ["BAR\n"]
        self.run_case(f_obj, expected_list)

    def test_ifndef_fulfilled_define_allowed(self):
        f_obj = FakeFile("header.h", ["#ifndef FOO\n", "#define BAR 1\n", "#endif\n", "BAR\n"])
        expected_list = ["1\n"]
        self.run_case(f_obj, expected_list)

    def test_fulfilled_ifdef_define_allowed(self):
        f_obj = FakeFile("header.h", ["#define FOO", "#ifdef FOO\n", "#define BAR 1\n",
                                      "#endif\n", "BAR\n"])
        expected_list = ["1\n"]
        self.run_case(f_obj, expected_list)
                                
    def test_lines_normalized(self):
        f_obj = FakeFile("header.h", ["foo\r\n", "bar\r\n"])
        expected_list = ["foo\n", "bar\n"]
        self.run_case(f_obj, expected_list)

    def test_lines_normalize_custom(self):
        f_obj = FakeFile("header.h", ["foo\n", "bar\n"])
        expected_list = ["foo\r\n", "bar\r\n"]
        output_list = list(simplecpreprocessor.preprocess(f_obj,
                                                          line_ending="\r\n"))
        self.assertEqual(output_list, expected_list)

    @unittest.expectedFailure
    def test_include_local_file(self):
        self.fail('FIXME: #include "foo.h"')

    @unittest.expectedFailure
    def test_include_with_path_list(self):
        self.fail('FIXME: #include <foo.h>')

