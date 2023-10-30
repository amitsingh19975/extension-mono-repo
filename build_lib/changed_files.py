from dataclasses import dataclass
import json
from pathlib import Path
from typing import List, MutableMapping, MutableSet, Optional, Set, cast
from .parse_module_dep import DependencyFiles, Module
from .diagnostics import DiagnosticBase, DiagnosticKind, DiagnosticLocation
from hashlib import md5
from os import environ
import asyncio

REPO_PATH = Path(__file__).parent.parent
CHECKSUM_FILE_NAME = 'checksums.json'
FILE_CHANGED_PATH = REPO_PATH / CHECKSUM_FILE_NAME

@dataclass
class FileChecksum:
    path: Path
    checksum: str

    @staticmethod
    def from_tuple(diagnostic: DiagnosticBase, location: DiagnosticLocation, element: tuple) -> Optional['FileChecksum']:
        (path_str, checksum) = element
        if type(path_str) != str:
            diagnostic.add(location, DiagnosticKind.ERROR, f'Invalid path type: "{path_str}"')
            return None
        
        if type(checksum) != str:
            diagnostic.add(location, DiagnosticKind.ERROR, f'Invalid checksum type: "{checksum}"')
            return None
        
        path = Path(path_str)

        if not path.exists():
            diagnostic.add(location, DiagnosticKind.ERROR, f'File not found: "{path}"')
            return None
        
        checksum.strip()

        if checksum == '':
            diagnostic.add(location, DiagnosticKind.INFO, f'Empty checksum for "{path}"')

        return FileChecksum(Path(path), checksum)

def parse_cached_file_checksum_from_file(diagnostic: DiagnosticBase) -> Optional[List[FileChecksum]]:
    res: List[FileChecksum] = []

    location = DiagnosticLocation(path=Path(FILE_CHANGED_PATH.name), prefix=None, resolved_base_path=REPO_PATH)
    if not FILE_CHANGED_PATH.exists():
        diagnostic.add(location, DiagnosticKind.INFO, f'Failed to find "{CHECKSUM_FILE_NAME}"')
        return None
    
    with FILE_CHANGED_PATH.open('r') as f:
        data = f.read().strip()
        if data == '':
            diagnostic.add(location, DiagnosticKind.INFO, f'Empty "{CHECKSUM_FILE_NAME}"')
            return res
        try:
            json_data = json.loads(data)
            if type(json_data) != dict:
                diagnostic.add(location, DiagnosticKind.ERROR, f'Failed to parse "{CHECKSUM_FILE_NAME}"')
                return res
            for json_file in json_data.items():
                file_checksum = FileChecksum.from_tuple(diagnostic, location, json_file)
                if file_checksum is not None:
                    res.append(file_checksum)
        except json.JSONDecodeError as e:
            diagnostic.add(location, DiagnosticKind.ERROR, f'Failed to parse "{CHECKSUM_FILE_NAME}"\n\t{e}')
            return res
        
    return res

async def generate_changed_files(diagnostic: DiagnosticBase, path: Path) -> Optional[FileChecksum]:
    location = DiagnosticLocation(path=path, prefix=None, resolved_base_path=REPO_PATH)
    if not path.exists():
        diagnostic.add(location, DiagnosticKind.ERROR, f'Failed to find "{path}"')
        return None
    
    if not path.is_file():
        diagnostic.add(location, DiagnosticKind.ERROR, f'"{path}" is not a file')
        return None
    
    with path.open('r') as f:
        data = f.read()
        checksum = md5(data.encode()).hexdigest()
        return FileChecksum(path, checksum)
    
async def write_changed_files_to_file_helper(diagnostic: DiagnosticBase, paths: List[Path]) -> List[FileChecksum]:
    res = await asyncio.gather(*[generate_changed_files(diagnostic, path) for path in paths])
    return [file for file in res if file is not None]

def write_changed_files_to_file(diagnostic: DiagnosticBase, files: List[Path]) -> None:

    location = DiagnosticLocation(path=Path(CHECKSUM_FILE_NAME), prefix=None, resolved_base_path=REPO_PATH)
    
    changed_files = asyncio.run(write_changed_files_to_file_helper(diagnostic, files))
    
    if len(changed_files) == 0:
        diagnostic.add(location, DiagnosticKind.INFO, f'No files changed')
        return

    try:
        with FILE_CHANGED_PATH.open('w') as f:
            json.dump({ (file.path, file.checksum) for file in changed_files}, f, indent=4)
    except Exception as e:
        diagnostic.add(location, DiagnosticKind.ERROR, f'Failed to write "{CHECKSUM_FILE_NAME}"\n\t{e}')
        return

def parse_space_separated_paths_escape(line: str, paths: List[Path], resolved_base_path: Path) -> None:
    path = ''
    pieces: List[str] = []
    escape = False
    for c in line:
        if escape:
            path += c
            escape = False
        elif c == '\\':
            escape = True
        elif c == ' ':
            pieces.append(path)
            path = ''
        else:
            path += c
    
    if path != '':
        pieces.append(path)
    
    for piece in pieces:
        path_buf = Path(piece.strip())
        if not path_buf.is_absolute():
            path_buf = resolved_base_path / piece
        
        if path_buf.exists() and path_buf.is_file():
            paths.append(path_buf)

def parse_cached_file_checksums(diagnostic: DiagnosticBase) -> Optional[List[FileChecksum]]:    
    return parse_cached_file_checksum_from_file(diagnostic)

def get_changed_files_from_module_helper(diagnostic: DiagnosticBase, module: Module, changed_source_files: Optional[List[FileChecksum]], changed_files: MutableSet[DependencyFiles]) -> None:
    for file in module.files:
        if changed_source_files is None:
            changed_files.add(file)
            continue

        has_path = False
        for changed_file in changed_source_files:
            if file.src_path == changed_file.path and file.checksum != changed_file.checksum:
                has_path = True
                break

        if has_path:
            if not file.build_path.exists():
                diagnostic.add(DiagnosticLocation.from_module(module), DiagnosticKind.ERROR, f'Dependency Found but build file "{file.build_path}" does not exist')
                continue
            changed_files.add(file)
    
    for include in module.includes:
        get_changed_files_from_module_helper(diagnostic, include, changed_source_files, changed_files)


def get_changed_files_from_module(diagnostic: DiagnosticBase, module: Module, changed_source_files: Optional[List[FileChecksum]]) -> Set[DependencyFiles]:
    changed_files: MutableSet[DependencyFiles] = set()
    get_changed_files_from_module_helper(diagnostic, module, changed_source_files, changed_files)
    diagnostic.add(DiagnosticLocation.from_module(module), DiagnosticKind.INFO, f'Found {len(changed_files)} changed files')
    return cast(Set, changed_files)

def upsert_checksum(diagnostic: DiagnosticBase, changed_files: Set[DependencyFiles], only_for_actions = True) -> None:
    if only_for_actions and environ.get('GITHUB_ACTIONS') != 'true':
        return
    
    location = DiagnosticLocation(path=Path(CHECKSUM_FILE_NAME), prefix=None, resolved_base_path=REPO_PATH)
    
    if len(changed_files) == 0:
        diagnostic.add(location, DiagnosticKind.INFO, f'No files changed')
        return

    old_json: MutableMapping[str, str] = {}
    if FILE_CHANGED_PATH.exists():
        try:
            old_json = json.loads(FILE_CHANGED_PATH.read_text())
        except Exception as e:
            old_json = {}
    
    if type(old_json) != dict:
        diagnostic.add(location, DiagnosticKind.ERROR, f'Failed to parse "{CHECKSUM_FILE_NAME}"')
        return
    
    for file in changed_files:
        old_json[str(file.src_path)] = file.checksum

    try:
        json.dump(old_json, FILE_CHANGED_PATH.open('w'), indent=4)
    except Exception as e:
        diagnostic.add(location, DiagnosticKind.ERROR, f'Failed to write "{CHECKSUM_FILE_NAME}"\n\t{e}')
        return