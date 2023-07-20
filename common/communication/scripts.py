import subprocess
import os

def static_checks():
    files = [f for f in os.listdir('src') if f.endswith('.py')]
    for f in files:
        p = subprocess.run(['python', '-m', 'pycodestyle', f'src/{f}'])
        p.check_returncode()
        p = subprocess.run(['python', '-m', 'mypy', f'src/{f}'])
        p.check_returncode()