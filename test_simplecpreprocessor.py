import unittest
import simplecpreprocessor


class TestSimplecpreprocessor(unittest.TestCase):
    def run_case(self, input_list, expected_list):
        output_list = list(simplecpreprocessor.preprocess(input_list))
        self.assertEqual(output_list, expected_list)

    def test_define(self):
        input_list = ["#define FOO 1\n", "FOO"]
        expected_list = ["1\n"]
        self.run_case(input_list, expected_list)

    def test_define_simple_self_referential(self):
        input_list = ["#define FOO FOO\n", "FOO\n"]
        expected_list = ["FOO\n"]
        self.run_case(input_list, expected_list)

    @unittest.expectedFailure
    def test_define_indirect_self_reference(self):
        input_list = ["#define x (4 + y)\n",
                      "#define y (2 * x)\n",
                      "x\n", "y\n"]
        expected_list = ["(4 + (2 * x))\n", "(2 * (4 + y)\n"]
        self.run_case(input_list, expected_list)

    def test_blank_define(self):
        input_list = ["#define FOO\n", "FOO\n"]
        expected_list = ["\n"]
        self.run_case(input_list, expected_list)

    def test_undefine(self):
        input_list = ["#define FOO 1\n", "#undef FOO\n", "FOO"]
        expected_list = ["FOO\n"]
        self.run_case(input_list, expected_list)

    def test_define_undefine(self):
        input_list = ["#define FOO 1\n", "#undef FOO\n", "FOO"]
        expected_list = ["FOO\n"]
        self.run_case(input_list, expected_list)

    def test_extra_endif_causes_error(self):
        input_list = ["#endif\n"]
        with self.assertRaises(simplecpreprocessor.ParseError):
            list(simplecpreprocessor.preprocess(input_list))

    def test_ifdef_left_open_causes_error(self):
        input_list = ["#ifdef FOO\n"]
        with self.assertRaises(simplecpreprocessor.ParseError):
            list(simplecpreprocessor.preprocess(input_list))

    def test_ifndef_left_open_causes_error(self):
        input_list = ["#ifndef FOO\n"]
        with self.assertRaises(simplecpreprocessor.ParseError):
            list(simplecpreprocessor.preprocess(input_list))

    def test_unexpected_macro_gives_parse_error(self):
        input_list = ["#something_unsupported foo bar\n"]
        with self.assertRaises(simplecpreprocessor.ParseError):
            list(simplecpreprocessor.preprocess(input_list))

    def test_ifndef_unfulfilled_define_ignored(self):
        input_list = ["#define FOO\n", "#ifndef FOO\n", "#define BAR 1\n", "#endif\n", "BAR\n"]
        expected_list = ["BAR\n"]
        self.run_case(input_list, expected_list)                                

    def test_ifdef_unfulfilled_define_ignored(self):
        input_list = ["#ifdef FOO\n", "#define BAR 1\n", "#endif\n", "BAR\n"]
        expected_list = ["BAR\n"]
        self.run_case(input_list, expected_list)

    def test_ifndef_fulfilled_define_allowed(self):
        input_list = ["#ifndef FOO\n", "#define BAR 1\n", "#endif\n", "BAR\n"]
        expected_list = ["1\n"]
        self.run_case(input_list, expected_list)

    def test_fulfilled_ifdef_define_allowed(self):
        input_list = ["#define FOO", "#ifdef FOO\n", "#define BAR 1\n", "#endif\n", "BAR\n"]
        expected_list = ["1\n"]
        self.run_case(input_list, expected_list)
                                
    def test_lines_normalized(self):
        input_list = ["foo\r\n", "bar\r\n"]
        expected_list = ["foo\n", "bar\n"]
        self.run_case(input_list, expected_list)
