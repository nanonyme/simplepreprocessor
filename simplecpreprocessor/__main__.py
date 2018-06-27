from simplecpreprocessor import preprocess
import argparse

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


main()
