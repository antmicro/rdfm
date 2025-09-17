import argparse
import pathlib
import subprocess
import glob
import os
import sys
import pathlib
from typing import Optional


def parse_common_arguments() -> argparse.Namespace:
    prog = os.path.basename(sys.argv[0])
    parser = argparse.ArgumentParser(
            prog=prog,
            description=(f"{'MyPy' if 'mypy' in prog else 'Pycodestyle'}"
                         " checks for the RDFM's CI flow"))

    parser.add_argument("-d", "--directory", type=str, default=".")
    parser.add_argument("-e", "--exclude", type=str)

    default_config = "mypy.ini" if "mypy" in prog else "pycodestyle"
    default_path_to_config = (pathlib.Path(__file__).parent / default_config).resolve()
    parser.add_argument("-c", "--config-file", type=str, default=str(default_path_to_config))

    return parser.parse_args()


def try_get_env_executable(cwd: str) -> Optional[str]:
    """
    Try getting the executable path using Poetry's CLI.
    """
    result = subprocess.run(
            "poetry env info --executable",
            shell=True,
            capture_output=True,
            encoding="utf-8",
            cwd=cwd)

    if 0 != result.returncode:
        return None

    return result.stdout.strip()


def collect_paths(dir: str) -> set[str]:
    """
    Collect all python files in the src directory and its subdirectories.
    """
    return {f for f in glob.glob(f'{dir}/src/**/*.py', recursive=True)}


def pycodestyle_checks() -> None:
    """
    Execute Pycodesyle checks on the provided python files.

    If any of the checks fail, an exception is raised.
    """
    args = parse_common_arguments()
    files = collect_paths(args.directory)
    cmd = [sys.executable, '-m', 'pycodestyle', f'--config={args.config_file}']
    if args.exclude:
        cmd.append(f"--exclude={args.exclude}")

    return_codes = list()
    for f in sorted(files):
        return_codes.append(subprocess.run(cmd + [f]).returncode)
    if any([code != 0 for code in return_codes]):
        raise Exception('Pycodestyle static checks failed')


def mypy_checks() -> None:
    """
    Execute MyPy checks on the provided python files.

    If any of the checks fail, an exception is raised.
    """
    args = parse_common_arguments()
    files = collect_paths(args.directory)
    exclude = ["--exclude", args.exclude] if args.exclude else []
    config_file = ["--config-file", args.config_file]

    # Access the PYTHON_EXEC variable which can hold the path to
    # the python executable in the subproject's virtualenv.
    # MyPy needs it to be able to find packages associated
    # with that virutalenv for type checking.
    python_executable = (["--python-executable", os.environ["PYTHON_EXEC"]]
                         if "PYTHON_EXEC" in os.environ.keys() else [])
    # In the case the above environment variable wasn't supplied,
    # try getting it via Poetry's CLI.
    if not python_executable:
        exec = try_get_env_executable(args.directory)
        if exec:
            python_executable = ["--python-executable", exec]

    return_codes = list()
    for f in sorted(files):
        return_codes.append(subprocess.run(
            [sys.executable, '-m', 'mypy',
             *config_file,
             *python_executable,
             *exclude,
             f]
            ).returncode)
    if any([code != 0 for code in return_codes]):
        raise Exception('MyPy static checks failed')
