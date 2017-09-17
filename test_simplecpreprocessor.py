import unittest
import simplecpreprocessor
import os.path
import os
import tempfile


class FakeFile(object):

    def __init__(self, name, contents):
        self.name = name
        self.contents = contents

    def __iter__(self):
        for line in self.contents:
            yield line

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass


class FakeHandler(simplecpreprocessor.HeaderHandler):

    def __init__(self, header_mapping, include_paths=()):
        self.header_mapping = header_mapping
        super(FakeHandler, self).__init__(list(include_paths))

    def _open(self, header_path):
        contents = self.header_mapping.get(header_path)
        if contents is not None:
            return FakeFile(header_path, contents)
        else:
            return None

    def parent_open(self, header_path):
        return super(FakeHandler, self)._open(header_path)


class TestSimpleCPreprocessor(unittest.TestCase):

    def run_case(self, input_list, expected_list):
        output_list = list(simplecpreprocessor.preprocess(input_list))
        self.assertEqual(output_list, expected_list)

    def test_define(self):
        f_obj = FakeFile("header.h", ["#define FOO 1\n",
                                      "FOO"])
        expected_list = ["1\n"]
        self.run_case(f_obj, expected_list)

    def test_multiline_define(self):
        f_obj = FakeFile("header.h", ["#define FOO \\\n",
                                      "\t1\n",
                                      "FOO\n"])
        expected_list = ["1\n"]
        self.run_case(f_obj, expected_list)

    def test_define_simple_self_referential(self):
        f_obj = FakeFile("header.h", ["#define FOO FOO\n",
                                      "FOO\n"])
        expected_list = ["FOO\n"]
        self.run_case(f_obj, expected_list)

    def test_define_indirect_self_reference(self):
        f_obj = FakeFile("header.h", ["#define x (4 + y)\n",
                                      "#define y (2 * x)\n",
                                      "x\n", "y\n"])
        expected_list = ["(4 + (2 * x))\n", "(2 * (4 + y))\n"]
        self.run_case(f_obj, expected_list)

    def test_partial_match(self):
        f_obj = FakeFile("header.h", [
            "#define FOO\n",
            "FOOBAR\n"
        ])
        expected_list = ["FOOBAR\n"]
        self.run_case(f_obj, expected_list)

    def test_blank_define(self):
        f_obj = FakeFile("header.h", ["#define FOO\n",
                                      "FOO\n"])
        expected_list = ["\n"]
        self.run_case(f_obj, expected_list)

    def test_define_parens(self):
        f_obj = FakeFile("header.h", ["#define FOO (x)\n",
                                      "FOO\n"])
        expected_list = ["(x)\n"]
        self.run_case(f_obj, expected_list)

    def test_define_undefine(self):
        f_obj = FakeFile("header.h", ["#define FOO 1\n",
                                      "#undef FOO\n",
                                      "FOO"])
        expected_list = ["FOO\n"]
        self.run_case(f_obj, expected_list)

    def test_complex_ignore(self):
        f_obj = FakeFile("header.h",
                         [
                            "#ifdef X\n",
                            "#define X 1\n",
                            "#ifdef X\n",
                            "#define X 2\n",
                            "#else\n",
                            "#define X 3\n",
                            "#endif\n",
                            "#define X 4\n",
                            "#endif\n",
                            "X\n"])
        expected_list = ["X\n"]
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
        f_obj = FakeFile("header.h", ["#define FOO\n", "#ifndef FOO\n",
                                      "#define BAR 1\n",
                                      "#endif\n", "BAR\n"])
        expected_list = ["BAR\n"]
        self.run_case(f_obj, expected_list)

    def test_ifdef_unfulfilled_define_ignored(self):
        f_obj = FakeFile("header.h", ["#ifdef FOO\n", "#define BAR 1\n",
                                      "#endif\n", "BAR\n"])
        expected_list = ["BAR\n"]
        self.run_case(f_obj, expected_list)

    def test_ifndef_fulfilled_define_allowed(self):
        f_obj = FakeFile("header.h", ["#ifndef FOO\n", "#define BAR 1\n",
                                      "#endif\n", "BAR\n"])
        expected_list = ["1\n"]
        self.run_case(f_obj, expected_list)

    def test_fulfilled_ifdef_define_allowed(self):
        f_obj = FakeFile("header.h", ["#define FOO", "#ifdef FOO\n",
                                      "#define BAR 1\n",
                                      "#endif\n", "BAR\n"])
        expected_list = ["1\n"]
        self.run_case(f_obj, expected_list)

    def test_define_inside_ifndef(self):
        f_obj = FakeFile("header.h", ["#ifndef MODULE\n",
                                      "#define MODULE\n",
                                      "#ifdef BAR\n",
                                      "5\n",
                                      "#endif\n",
                                      "1\n",
                                      "#endif\n"])

        expected_list = ["1\n"]
        self.run_case(f_obj, expected_list)

    def test_ifdef_else_undefined(self):
        f_obj = FakeFile("header.h", [
            "#ifdef A\n",
            "#define X 1\n",
            "#else\n",
            "#define X 0\n",
            "#endif\n",
            "X\n"])
        expected_list = ["0\n"]
        self.run_case(f_obj, expected_list)

    def test_ifdef_else_defined(self):
        f_obj = FakeFile("header.h", [
            "#define A\n",
            "#ifdef A\n",
            "#define X 1\n",
            "#else\n",
            "#define X 0\n",
            "#endif\n",
            "X\n"])
        expected_list = ["1\n"]
        self.run_case(f_obj, expected_list)

    def test_ifndef_else_undefined(self):
        f_obj = FakeFile("header.h", [
            "#ifndef A\n",
            "#define X 1\n",
            "#else\n",
            "#define X 0\n",
            "#endif\n",
            "X\n"])
        expected_list = ["1\n"]
        self.run_case(f_obj, expected_list)

    def test_ifndef_else_defined(self):
        f_obj = FakeFile("header.h", [
            "#define A\n",
            "#ifndef A\n",
            "#define X 1\n",
            "#else\n",
            "#define X 0\n",
            "#endif\n",
            "X\n"])
        expected_list = ["0\n"]
        self.run_case(f_obj, expected_list)

    def test_lines_normalized(self):
        f_obj = FakeFile("header.h", ["foo\r\n", "bar\r\n"])
        expected_list = ["foo\n", "bar\n"]
        self.run_case(f_obj, expected_list)

    def test_lines_normalize_custom(self):
        f_obj = FakeFile("header.h", ["foo\n", "bar\n"])
        expected_list = ["foo\r\n", "bar\r\n"]
        ret = simplecpreprocessor.preprocess(f_obj,
                                             line_ending="\r\n")
        self.assertEqual(list(ret), expected_list)

    def test_include_local_file_with_subdirectory(self):
        other_header = "somedirectory/other.h"
        f_obj = FakeFile("header.h", ['#include "%s"\n' % other_header])
        handler = FakeHandler({other_header: ["1\n"]})
        ret = simplecpreprocessor.preprocess(f_obj,
                                             header_handler=handler)
        self.assertEqual(list(ret), ["1\n"])

    def test_define_with_comment(self):
        f_obj = FakeFile("header.h", [
            "#define FOO 1 // comment\n",
            "FOO\n"])
        expected_list = ["1\n"]
        self.run_case(f_obj, expected_list)

    def test_ifdef_with_comment(self):
        f_obj = FakeFile("header.h", [
            "#define FOO",
            "#ifdef FOO // comment\n",
            "1\n",
            "#endif"])
        expected_list = ["1\n"]
        self.run_case(f_obj, expected_list)

    def test_include_with_path_list(self):
        f_obj = FakeFile("header.h", ['#include <other.h>\n'])
        handler = FakeHandler({os.path.join("subdirectory",
                                            "other.h"): ["1\n"]})
        include_paths = ["subdirectory"]
        ret = simplecpreprocessor.preprocess(f_obj,
                                             include_paths=include_paths,
                                             header_handler=handler)
        self.assertEqual(list(ret), ["1\n"])

    def test_tab_macro_indentation(self):
        f_obj = FakeFile("header.h", [
            "\t#define FOO 1\n",
            "\tFOO\n"])
        expected_list = ["\t1\n"]
        self.run_case(f_obj, expected_list)

    def test_space_macro_indentation(self):
        f_obj = FakeFile("header.h", [
            "    #define FOO 1\n",
            "    FOO\n"])
        expected_list = ["    1\n"]
        self.run_case(f_obj, expected_list)

    def test_include_with_path_list_with_subdirectory(self):
        header_file = os.path.join("nested", "other.h")
        include_path = "somedir"
        f_obj = FakeFile("header.h", ['#include <%s>\n' % header_file])
        handler = FakeHandler({os.path.join(include_path,
                                            header_file): ["1\n"]})
        include_paths = [include_path]
        ret = simplecpreprocessor.preprocess(f_obj,
                                             include_paths=include_paths,
                                             header_handler=handler)
        self.assertEqual(list(ret), ["1\n"])

    def test_include_missing_local_file(self):
        other_header = os.path.join("somedirectory", "other.h")
        f_obj = FakeFile("header.h", ['#include "%s"\n' % other_header])
        handler = FakeHandler({})
        with self.assertRaises(simplecpreprocessor.ParseError):
            ret = simplecpreprocessor.preprocess(f_obj,
                                                 header_handler=handler)
            list(ret)

    def test_ignore_include_path(self):
        f_obj = FakeFile("header.h", ['#include <other.h>\n'])
        handler = FakeHandler({os.path.join("subdirectory",
                                            "other.h"): ["1\n"]})
        paths = ["subdirectory"]
        ignored = ["other.h"]
        ret = simplecpreprocessor.preprocess(f_obj,
                                             include_paths=paths,
                                             header_handler=handler,
                                             ignore_headers=ignored)
        self.assertEqual(list(ret), [])

    def test_pragma_once(self):
        f_obj = FakeFile("header.h", ["""#include "other.h"\n""",
                                      """#include "other.h"\n""",
                                      "X\n"])
        handler = FakeHandler({"other.h": [
            "#pragma once\n",
            "#ifdef X\n",
            "#define X 2\n",
            "#else\n",
            "#define X 1\n",
            "#endif\n"]})
        ret = simplecpreprocessor.preprocess(f_obj, header_handler=handler)
        self.assertEqual(list(ret), ["1\n"])

    def test_platform_constants(self):
        f_obj = FakeFile("header.h", ['#ifdef ODDPLATFORM\n',
                                      'ODDPLATFORM\n', '#endif'])
        const = {"ODDPLATFORM": "ODDPLATFORM"}
        ret = simplecpreprocessor.preprocess(f_obj,
                                             platform_constants=const)
        self.assertEqual(list(ret), ["ODDPLATFORM\n"])

    def test_handler_missing_file(self):
        handler = FakeHandler([])
        self.assertIs(handler.parent_open("does_not_exist"), None)

    def test_handler_existing_file(self):
        handler = FakeHandler([])
        file_info = os.stat(__file__)
        with handler.parent_open(__file__) as f_obj:
            self.assertEqual(os.fstat(f_obj.fileno()).st_ino,
                file_info.st_ino)
            self.assertEqual(f_obj.name, __file__)
