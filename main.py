import sys
from build_lib import parse_module, StreamDiagnostics, build_module, parse_cached_file_checksums, get_changed_files_from_module, upsert_checksum
from pprint import pprint

def main() -> None:
    module = parse_module()
    pprint(module)
    diagnostic = StreamDiagnostics(sys.stdout)
    build_module(diagnostic, module)
    files = parse_cached_file_checksums(diagnostic)
    changed_files = get_changed_files_from_module(diagnostic, module, files)
    print(changed_files)
    upsert_checksum(diagnostic, changed_files)

if __name__ == '__main__':
    main()