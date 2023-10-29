import sys
from build_lib import parse_module, StreamDiagnostics, build_module, parse_changed_files, get_changed_files_from_module
from pprint import pprint

def main() -> None:
    module = parse_module()
    pprint(module)
    diagnostic = StreamDiagnostics(sys.stdout)
    build_module(diagnostic, module)
    files = parse_changed_files(diagnostic)
    print(get_changed_files_from_module(diagnostic, module, files))

if __name__ == '__main__':
    main()