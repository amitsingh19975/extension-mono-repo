from pathlib import Path
from typing import Any, List, MutableSet, Set, cast
from .parse_module_dep import DependencyFiles, Module
from .diagnostics import DiagnosticBase, DiagnosticKind, DiagnosticLocation
from git import Repo
from sys import argv

REPO_PATH = Path(__file__).parent.parent
git_repo = Repo(REPO_PATH)

def get_git_changed_files_between_hashes(diagnostic: DiagnosticBase, last_hash: str) -> List[str]:

    print(f'get_git_changed_files_between_hashes => Last Hash: {last_hash} | {argv[1] if len(argv) > 1 else None}')
    current_hash = argv[1] if len(argv) > 1 else git_repo.head.commit.hexsha
    res: Any = git_repo.git.execute(['git', 'diff', '--name-only', last_hash, current_hash])
    if bytes == type(res):
        try:
            res = res.decode('utf-8')
        except UnicodeDecodeError:
            diagnostic.add(None, DiagnosticKind.ERROR, f'Failed to decode git diff')
            return []
    
    if type(res) == str:
        return res.strip().splitlines()
        
    diagnostic.add(None, DiagnosticKind.ERROR, f'Failed to get git diff')
    return []
    # return pipe.stdout.decode('utf-8').splitlines()
    

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

def get_git_prev_commit_hash(prev: int) -> str:
    try:
        res: Any = git_repo.git.execute(['git', 'rev-parse', f'HEAD~{prev}'])
        if bytes == type(res):
            try:
                res = res.decode('utf-8')
            except UnicodeDecodeError:
                return 'HEAD'
        
        if type(res) == str:
            return res.strip()
    except:
        pass
    return 'HEAD'

def parse_changed_files(diagnostic: DiagnosticBase, base_path: Path = Path(".")) -> List[Path]:    
    resolved_base_path = base_path.resolve()
    paths: List[Path] = []
    cache_path = resolved_base_path / 'cache'
    
    if not cache_path.exists():
        cache_path.mkdir(parents = True)

    last_hash_path = cache_path / 'last_hash.txt'
    last_hash = get_git_prev_commit_hash(3)
    print(f'First Hash: {last_hash}')

    if last_hash_path.exists():
        with last_hash_path.open('r') as f:
            last_hash = f.read().strip()
        print(f'Last Hash: {last_hash}')

    files = get_git_changed_files_between_hashes(diagnostic, last_hash)
    for file in files:
        parse_space_separated_paths_escape(file, paths, resolved_base_path)

    with last_hash_path.open('w') as f:
        f.write(git_repo.head.commit.hexsha)

    print(f'Found {len(paths)} changed files')
    print(f'Changed Files: {paths}')

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
    get_changed_files_from_module_helper(diagnostic, module, changed_source_files, changed_files)
    diagnostic.add(DiagnosticLocation.from_module(module), DiagnosticKind.INFO, f'Found {len(changed_files)} changed files')
    return cast(Set, changed_files)