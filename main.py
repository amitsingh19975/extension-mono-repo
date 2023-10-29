import sys
from build_lib import parse_module, StreamDiagnostics, build_module
from pprint import pprint

def main() -> None:
    module = parse_module()
    pprint(module)
    diagnostic = StreamDiagnostics(sys.stdout)
    build_module(diagnostic, module)

if __name__ == '__main__':
    main()