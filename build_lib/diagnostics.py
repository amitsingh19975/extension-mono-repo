from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import IO, List, Optional, Union, cast
from .parse_module_dep import DependencyCmds, Module
from colorama import Fore, Back, Style

class DiagnosticKind(Enum):
    ERROR = auto()
    WARNING = auto()
    INFO = auto()
    SUCCESS = auto()

    def __str__(self) -> str:
        prefix = ''
        match self:
            case DiagnosticKind.ERROR: prefix = f'{Fore.RED}'
            case DiagnosticKind.WARNING: prefix = f'{Fore.YELLOW}'
            case DiagnosticKind.INFO: prefix = f'{Fore.BLUE}'
            case DiagnosticKind.SUCCESS: prefix = f'{Fore.GREEN}'
        max_len = max(len(kind.name) for kind in DiagnosticKind)
        return f'{prefix} {self.name:<{max_len}}:{Style.RESET_ALL}'

@dataclass
class DiagnosticLocation:
    path: Path
    prefix: Union[DependencyCmds, Module, None]
    resolved_base_path: Path

    def __str__(self) -> str:
        if self.prefix is None:
            return f'("{self.path}")'
        
        if type(self.prefix) == Module:
            return f'[{Style.BRIGHT}{Fore.MAGENTA}{self.prefix.name}{Style.RESET_ALL}]("{self.path}")'
        
        cmd = cast(DependencyCmds, self.prefix)
        cmd_name = cmd.name
        if cmd.is_builtin():
            cmd_name = cmd.get_builtin()
        return f'[{Style.BRIGHT}{Fore.CYAN}{cmd_name}{Style.RESET_ALL}]("{self.path}")'
    
    @staticmethod
    def from_module(module: Module) -> 'DiagnosticLocation':
        return DiagnosticLocation(path = module.path, prefix = module, resolved_base_path = module.resolve_base_path)

@dataclass
class DiagnosticMessage:
    location: DiagnosticLocation
    message: str
    kind: DiagnosticKind

    def __str__(self) -> str:
        return f'{self.kind} {self.location}: {self.message}'

class DiagnosticBase:
    def add_message(self, message: DiagnosticMessage) -> None:
        raise NotImplementedError
    
    def add(self, location: DiagnosticLocation, kind: DiagnosticKind, message: str) -> None:
        self.add_message(DiagnosticMessage(location = location, message = message, kind = kind))
    
    def has_errors(self) -> bool:
        raise NotImplementedError
    
    def has_warnings(self) -> bool:
        raise NotImplementedError
    
    def has_infos(self) -> bool:
        raise NotImplementedError

class StreamDiagnostics(DiagnosticBase):
    def __init__(self, writer: IO) -> None:
        self.writer = writer
    
    def add_message(self, message: DiagnosticMessage) -> None:
        self.writer.write(f'{message}\n')
    
    def add(self, location: DiagnosticLocation, kind: DiagnosticKind, message: str) -> None:
        self.add_message(DiagnosticMessage(location = location, message = message, kind = kind))

class ListDiagnostics(DiagnosticBase):
    def __init__(self) -> None:
        self.messages: List[DiagnosticMessage] = []
    
    def add_message(self, message: DiagnosticMessage) -> None:
        self.messages.append(message)
    
    def add(self, location: DiagnosticLocation, kind: DiagnosticKind, message: str) -> None:
        self.add_message(DiagnosticMessage(location = location, message = message, kind = kind))
    
    def has_errors(self) -> bool:
        return any(message.kind == DiagnosticKind.ERROR for message in self.messages)
    
    def has_warnings(self) -> bool:
        return any(message.kind == DiagnosticKind.WARNING for message in self.messages)
    
    def has_infos(self) -> bool:
        return any(message.kind == DiagnosticKind.INFO for message in self.messages)
    
    def __iter__(self):
        return iter(self.messages)
    
    def __len__(self):
        return len(self.messages)
    
    def __getitem__(self, index):
        return self.messages[index]
    
    def __str__(self) -> str:
        return '\n'.join(str(message) for message in self.messages)