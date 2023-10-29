from typing import MutableMapping
from .diagnostics import DiagnosticBase, DiagnosticKind, DiagnosticLocation
from .parse_module_dep import Module
import asyncio
from .run_shell_cmds import run_shell

async def build_steps_async(diagnostic: DiagnosticBase, module: Module) -> bool:
    for step in module.steps:
        location = DiagnosticLocation(path = module.path, prefix = step, resolved_base_path = module.resolve_base_path)
        if not run_shell(diagnostic, location, step):
            return False
    return True
    

def build_module_helper(diagnostic: DiagnosticBase, module: Module, tasks: MutableMapping[Module, asyncio.Task]) -> None:
    location = DiagnosticLocation.from_module(module)
    diagnostic.add(location, DiagnosticKind.INFO, f'Building module: "{module.name}"')

    if (len(module.steps) > 0):
        task = asyncio.create_task(build_steps_async(diagnostic, module), name=f'{module.name}_steps')
        tasks[module] = task
    else:
        diagnostic.add(location, DiagnosticKind.INFO, f'No steps for module: "{module.name}"')

    for dep in module.includes:    
        build_module_helper(diagnostic, dep, tasks)
    
    diagnostic.add(location, DiagnosticKind.INFO, f'Finished building module: "{module.name}"')


async def build_module_async(diagnostic: DiagnosticBase, module: Module) -> None:
    tasks: MutableMapping[Module, asyncio.Task] = {}
    build_module_helper(diagnostic, module, tasks)
    for module, task in tasks.items():
        if await task == False:
            diagnostic.add(DiagnosticLocation.from_module(module), DiagnosticKind.ERROR, f'Failed to build module: "{module.name}"')

def build_module(diagnostic: DiagnosticBase, module: Module) -> Module:
    asyncio.run(build_module_async(diagnostic, module))
    return module