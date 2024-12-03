import subprocess
import glob


def pycodestyle_checks():
    """
    Execute Pycodesyle checks on all python files in the src directory
    and its subdirectories.

    If any of the checks fail, an exception is raised.
    """
    files = [f for f in glob.glob('src/**/*.py', recursive=True)]
    return_codes = list()
    for f in files:
        return_codes.append(subprocess.run(
            ['python', '-m', 'pycodestyle', '--max-line-length=100', f]).returncode)
    if any([code != 0 for code in return_codes]):
        raise Exception('Pycodestyle static checks failed')


def mypy_checks():
    """
    Execute MyPy checks on all python files in the src directory
    and its subdirectories.

    If any of the checks fail, an exception is raised.
    """
    files = [f for f in glob.glob('src/**/*.py', recursive=True)]
    return_codes = list()
    for f in files:
        return_codes.append(subprocess.run(
            ['python', '-m', 'mypy', f]).returncode)
    if any([code != 0 for code in return_codes]):
        raise Exception('MyPy static checks failed')
