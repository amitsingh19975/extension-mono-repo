from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union
import json

BASE_PATH = Path(__file__).parent.parent

def try_read_json(path: Path) -> Optional[dict]:
    try:
        with path.open() as f:
            return json.load(f)
    except:
        return None

@dataclass
class DependencyFiles:
    uuid: str
    buildPath: Path
    srcPath: Path

    @staticmethod
    def from_json(base_path: Path, json_data: dict) -> 'DependencyFiles':
        module_path = base_path / 'module.json'
        if 'uuid' not in json_data:
            raise ValueError(f'No uuid in dependency file: "{module_path}"\n{json_data}')
        
        uuid = json_data['uuid']

        if type(uuid) != str:
            raise ValueError(f'type of "uuid" must be a "str", but found "{type(uuid)}": {module_path}\n{json_data}')
        
        if 'path' not in json_data:
            raise ValueError(f'No "path" in dependency file: "{module_path}"\n{json_data}')

        if type(json_data['path']) != str:
            raise ValueError(f'type of "path" must be a "str", but found "{type(json_data["path"])}": {module_path}\n{json_data}')
        
        buildPath = base_path / json_data['path']

        if 'srcPath' not in json_data:
            raise ValueError(f'No "srcPath" in dependency file: "{module_path}"\n{json_data}')
        
        if type(json_data['srcPath']) != str:
            raise ValueError(f'type of "srcPath" must be a "str", but found "{type(json_data["srcPath"])}": {module_path}\n{json_data}')
        
        srcPath = base_path / json_data['srcPath']

        if not srcPath.exists():
            raise FileNotFoundError(f'File not found: {srcPath}')
        
        if not srcPath.is_file():
            raise ValueError(f'Not a file: {srcPath}')

        return DependencyFiles(uuid = uuid, buildPath = buildPath, srcPath = srcPath)

@dataclass
class DependencyCmds:
    name: str
    cmd: str

    @staticmethod
    def builtin(cmd: str) -> 'DependencyCmds':
        match cmd:
            case 'deploy': return DependencyCmds(name = 'Deploy', cmd = '__builtin__:deploy')
            case _: raise ValueError(f'Unknown builtin command: {cmd}')

    @staticmethod
    def from_step(cmds: Union[dict, str]) -> 'DependencyCmds':
        if isinstance(cmds, str):
            return DependencyCmds.builtin(cmds)
        
        if 'name' not in cmds:
            raise ValueError(f'No "name" in command: {cmds}')
        
        if 'cmd' not in cmds:
            raise ValueError(f'No "cmd" in command: {cmds}')

        name = cmds['name']
        if type(name) != str:
            raise ValueError(f'type of "name" must be a "str", but found "{type(name)}": {cmds}')
        
        cmd = cmds['cmd']
        if type(cmd) != str:
            raise ValueError(f'type of "cmd" must be a "str", but found "{type(cmd)}": {cmds}')
        
        return DependencyCmds(name = name, cmd = cmd)
    
    def is_builtin(self) -> bool:
        return self.cmd.startswith('__builtin__:')
    
    def get_builtin(self) -> str:
        if not self.is_builtin():
            raise ValueError(f'Command is not builtin: {self.cmd}')
        return self.cmd[len('__builtin__:'):]

    def is_deploy(self) -> bool:
        try:
            return self.get_builtin() == 'deploy'
        except:
            return False

def validate_commands(path: Path, steps: List[DependencyCmds]) -> None:
    has_deploy = False
    for step in steps:
        has_deploy = step.is_deploy() or has_deploy

    if has_deploy and not steps[-1].is_deploy():
        raise ValueError(f'Last step must be deploy: {path}')

@dataclass
class Module:
    name: str
    path: Path
    resolve_base_path: Path
    includes: List['Module']
    steps: List[DependencyCmds]
    files: List[DependencyFiles]

    @staticmethod
    def from_path(base_path: Path, module_path: Path) -> 'Module':
        resolved_base_path = base_path.resolve()
        path = module_path

        if not path.exists():
            raise FileNotFoundError(f'File not found: {path}')
        
        if not path.is_file():
            raise ValueError(f'Not a file: {path}')
        
        json_data = try_read_json(path)
        if json_data is None:
            raise ValueError(f'Not a valid JSON file: {path}')
        
        name: str = '<Unknown Module>'

        if 'name' in json_data:
            name = json_data['name']
            if type(name) != str:
                raise ValueError(f'type of "name" must be a "str", but found "{type(name)}": {path}')

        includes: List['Module'] = []

        if 'includes' in json_data:
            if type(json_data['includes']) != list:
                raise ValueError(f'type of "includes" must be a "list", but found "{type(json_data["includes"])}": {path}')
            
            for include in json_data['includes']:
                if type(include) != str:
                    raise ValueError(f'type of "include" must be a "str", but found "{type(include)}": {path}')
                
                include_path = base_path / include
                include_module = Module.from_path(include_path, include_path / 'module.json')
                includes.append(include_module)
        
        steps: List[DependencyCmds] = []

        if 'steps' in json_data:
            if type(json_data['steps']) != list:
                raise ValueError(f'type of "steps" must be a "list", but found "{type(json_data["steps"])}": {path}')
            
            steps = [DependencyCmds.from_step(step) for step in json_data['steps']]
            validate_commands(path, steps)
            

        files: List[DependencyFiles] = []

        if 'files' in json_data:
            if type(json_data['files']) != list:
                raise ValueError(f'type of "files" must be a "list", but found "{type(json_data["files"])}": {path}')
            
            files = [DependencyFiles.from_json(base_path, file) for file in json_data['files']] 
        
        module = Module(name = name, path = path, resolve_base_path = resolved_base_path, includes = includes, steps = steps, files = files)
        return module
    
    def __hash__(self) -> int:
        return hash(id(self))
 
def parse_module(base_path: Union[Path, str] = './') -> Module:
    module_path = Path(base_path) / 'module.json'
    module = Module.from_path(Path(base_path), module_path)
    if module.name == '<Unknown Module>':
        module.name = "Root Module"
    return module
