from pathlib import Path
from typing import List, MutableSet, Set, cast

from .parse_module_dep import DependencyFiles, Module
from .diagnostics import DiagnosticBase, DiagnosticKind, DiagnosticLocation

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



def parse_changed_files(diagnostic: DiagnosticBase, base_path: Path = Path(".")) -> List[Path]:
    file_path = base_path / 'changed_files.txt'
    location = DiagnosticLocation(path=file_path, prefix=None, resolved_base_path=base_path.resolve())
    if not file_path.exists():
        diagnostic.add(location, DiagnosticKind.ERROR, f'File {file_path} does not exist')
        return []
    
    if not file_path.is_file():
        diagnostic.add(location, DiagnosticKind.ERROR, f'File {file_path} is not a file')
        return []
    
    resolved_base_path = base_path.resolve()
    paths: List[Path] = []

    with file_path.open('r') as f:
        lines = f.readlines()
        for line in lines:
            parse_space_separated_paths_escape(line, paths, resolved_base_path)

    print(f'Changed files: {paths}')
    return paths

def get_changed_files_from_module_helper(diagnostic: DiagnosticBase, module: Module, changed_source_files: List[Path], changed_files: MutableSet[DependencyFiles]) -> None:
    for file in module.files:
        if file.srcPath in changed_source_files:
            if not file.buildPath.exists():
                diagnostic.add(DiagnosticLocation.from_module(module), DiagnosticKind.ERROR, f'Dependency Found but build file "{file.buildPath}" does not exist')
                continue

            changed_files.add(file)
    
    for include in module.includes:
        get_changed_files_from_module_helper(diagnostic, include, changed_source_files, changed_files)


def get_changed_files_from_module(diagnostic: DiagnosticBase, module: Module, changed_source_files: List[Path]) -> Set[DependencyFiles]:
    changed_files: MutableSet[DependencyFiles] = set()
    print(f'Changed source files: {changed_source_files}')
    get_changed_files_from_module_helper(diagnostic, module, changed_source_files, changed_files)
    diagnostic.add(DiagnosticLocation.from_module(module), DiagnosticKind.INFO, f'Found {len(changed_files)} changed files')
    return cast(Set, changed_files)