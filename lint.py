#!/usr/bin/env python3
import subprocess
import sys

args = [
    'pylint',
    'game',
    'setup.py',
]
retcode = subprocess.call(args, stdout=sys.stdout, stderr=sys.stderr)

args = [
    'pycodestyle',
]
retcode += subprocess.call(args, stdout=sys.stdout, stderr=sys.stderr)
