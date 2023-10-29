from os import chdir, getcwd
import subprocess
from typing import Optional

from .diagnostics import DiagnosticBase, DiagnosticKind, DiagnosticLocation
from .parse_module_dep import DependencyCmds
from colorama import Fore, Style

TAB_SPACE = '    '

def convert_output_to_str(output: Optional[bytes]) -> str:
    if output is None:
        return ''
    try:
        return output.decode('utf-8').strip().replace('\r\n', '\n').replace('\n', f'\n{TAB_SPACE}')
    except:
        return ''

def run_shell(diagnostic: DiagnosticBase, location: DiagnosticLocation, cmd: DependencyCmds):
    diagnostic.add(location, DiagnosticKind.INFO, f'Running shell command: "{cmd.cmd}"')
    current_dir = getcwd()
    try:
        cmd_base_path = location.resolved_base_path
        diagnostic.add(location, DiagnosticKind.INFO, f'Changing directory to: "{cmd_base_path}"')
        chdir(cmd_base_path)
    except:
        diagnostic.add(location, DiagnosticKind.ERROR, f'Unable to change directory: from "{current_dir}" to "{cmd_base_path}"')
        return False
    
    try:
        result = subprocess.run(cmd.cmd, shell=True, start_new_session=True, capture_output=True)
        if result.returncode != 0:
            diagnostic.add(location, DiagnosticKind.ERROR, f'Shell command failed: {result.returncode}')
            stdout = convert_output_to_str(result.stdout)
            stderr = convert_output_to_str(result.stderr)
            if len(stdout) > 0:
                diagnostic.add(location, DiagnosticKind.INFO, f'{Fore.GREEN}{Style.BRIGHT}Stdout: {Style.RESET_ALL} \n{TAB_SPACE}{stdout}')

            if len(stderr) > 0:
                diagnostic.add(location, DiagnosticKind.ERROR, f'{Fore.RED}{Style.BRIGHT}Stderr: {Style.RESET_ALL} \n{TAB_SPACE}{stderr}')
            return False
        else:
            diagnostic.add(location, DiagnosticKind.SUCCESS, f'Shell command succeeded')
            stdout = convert_output_to_str(result.stdout)
            stderr = convert_output_to_str(result.stderr)
            if len(stdout) > 0:
                diagnostic.add(location, DiagnosticKind.INFO, f'{Fore.GREEN}{Style.BRIGHT}Stdout: {Style.RESET_ALL} \n{TAB_SPACE}{stdout}')

            if len(stderr) > 0:
                diagnostic.add(location, DiagnosticKind.ERROR, f'{Fore.RED}{Style.BRIGHT}Stderr: {Style.RESET_ALL} \n{TAB_SPACE}{stderr}')
        return True
    except Exception as e:
        diagnostic.add(location, DiagnosticKind.ERROR, f'Unable to run shell command: {e}')
        return False
    finally:
        chdir(current_dir)