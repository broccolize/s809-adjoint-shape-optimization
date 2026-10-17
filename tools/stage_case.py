#!/usr/bin/env python3
"""Copy one case into a new disposable runs/ directory; never run the solver."""
from pathlib import Path
import argparse
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
CHOICES = ['case-a-ffd','case-b-cst','mesh-check-20k','mesh-check-40k','mesh-check-80k','aoa-sweep']

def stage(case, name):
    if case not in CHOICES or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', name):
        raise ValueError('Invalid case or run name')
    target = ROOT/'runs'/name
    if target.exists():
        raise FileExistsError('Choose another --name to preserve an existing run')
    target.parent.mkdir(exist_ok=True)
    shutil.copytree(ROOT/'cases'/case, target)
    (target/'.s809-run-dir').write_text(f'Staged from cases/{case}\n', encoding='utf-8')
    return target

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', choices=CHOICES)
    parser.add_argument('--name', help='Optional new name under runs/; existing paths are never overwritten')
    args = parser.parse_args()
    target = stage(args.case, args.name or args.case)
    print(f'Staged {target.relative_to(ROOT)}; no CFD process was started.')
    print('Use docs/reproduction.md for the commands in a compatible Linux solver environment.')

if __name__ == '__main__':
    main()
