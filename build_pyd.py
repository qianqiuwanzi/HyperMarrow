#!/usr/bin/env python3
"""Cython compile .py → .pyd → output to dist/pyd/. Source NEVER modified."""

import os, sys, subprocess, shutil, py_compile
from pathlib import Path

_HERE = Path(__file__).parent
_TARGETS = ['openclaw-memory-system', 'openclaw-learning-system']
_SKIP_DIRS = {'examples', '__pycache__', 'openclaw_memory_system', 'data', 'memory_api', 'memory_cli'}
_SKIP_FILES = {'setup.py', 'build_package.py', 'build_pyd.py'}

OUTPUT = _HERE / 'dist' / 'pyd'
# Clean output dir
if OUTPUT.exists():
    shutil.rmtree(OUTPUT)
os.makedirs(OUTPUT, exist_ok=True)

# Copy start.py, stop.py, config.yaml as-is
for f in ['start.py', 'stop.py', 'config.yaml']:
    src = _HERE / f
    if src.exists():
        shutil.copy2(src, OUTPUT / f)

# Collect .py files to compile
py_files = []
for target in _TARGETS:
    for py_file in (_HERE / target).rglob('*.py'):
        if any(s in py_file.parts for s in _SKIP_DIRS): continue
        if py_file.name in _SKIP_FILES: continue
        py_files.append(py_file)

total = len(py_files)
print(f'Compiling {total} modules → {OUTPUT}')

for i, py_file in enumerate(py_files):
    rel = py_file.relative_to(_HERE)
    out_dir = OUTPUT / py_file.parent.relative_to(_HERE)
    out_dir.mkdir(parents=True, exist_ok=True)

    mod_name = py_file.stem
    print(f'  [{i+1}/{total}] {rel}', end='', flush=True)

    # Step 1: Cythonize
    build_dir = out_dir / 'build_tmp'
    build_dir.mkdir(exist_ok=True)
    result = subprocess.run(
        [sys.executable, '-m', 'cython', '-3', str(py_file.name)],
        capture_output=True, text=True, cwd=str(py_file.parent), timeout=60
    )
    if result.returncode != 0:
        print(f'  CYTHON FAILED → .pyc fallback')
        py_compile.compile(str(py_file), cfile=str(out_dir / f'{mod_name}.pyc'), doraise=False, optimize=2)
        shutil.rmtree(build_dir, ignore_errors=True)
        continue

    c_file = py_file.with_suffix('.c')
    if not c_file.exists():
        print(f'  NO .c FILE → .pyc fallback')
        py_compile.compile(str(py_file), cfile=str(out_dir / f'{mod_name}.pyc'), doraise=False, optimize=2)
        shutil.rmtree(build_dir, ignore_errors=True)
        continue

    # Step 2: Compile .c → .pyd using MSVC
    setup_content = f'''
from distutils.core import setup, Extension
setup(
    ext_modules=[Extension("{mod_name}", ["{c_file.name}"])],
    script_args=['build_ext', '--build-lib', '.', '--build-temp', '{build_dir.name}'],
)
'''
    setup_py = py_file.parent / '_setup_temp.py'
    setup_py.write_text(setup_content)

    result = subprocess.run(
        [sys.executable, '_setup_temp.py', '--quiet'],
        capture_output=True, text=True, cwd=str(py_file.parent), timeout=120
    )
    setup_py.unlink()

    # Move compiled .pyd to output dir
    pyd_files = list(py_file.parent.glob(f'{mod_name}*.pyd'))
    if pyd_files:
        target_pyd = out_dir / f'{mod_name}.pyd'
        shutil.move(str(pyd_files[0]), str(target_pyd))
        for extra in pyd_files[1:]:
            extra.unlink()
        print('  OK')
    else:
        print(f'  COMPILE FAILED → .pyc fallback')
        py_compile.compile(str(py_file), cfile=str(out_dir / f'{mod_name}.pyc'), doraise=False, optimize=2)

    # Clean up intermediates in source dir
    c_file.unlink()
    shutil.rmtree(build_dir, ignore_errors=True)

# ── Compile skipped files (memory_api, memory_cli) to .pyc ──
print('\nCompiling API layer → .pyc...')
for target in _TARGETS:
    for py_file in (_HERE / target).rglob('*.py'):
        if not any(s in py_file.parts for s in _SKIP_DIRS): continue
        out_dir = OUTPUT / py_file.parent.relative_to(_HERE)
        out_dir.mkdir(parents=True, exist_ok=True)
        py_compile.compile(str(py_file), cfile=str(out_dir / f'{py_file.stem}.pyc'), doraise=False, optimize=2)
        print(f'  {py_file.relative_to(_HERE)} → .pyc')

# ── Clean all intermediates in output ──
for target in _TARGETS:
    out_target = OUTPUT / target
    if not out_target.exists(): continue
    for ext in ['*.c', '*.cpp', '*.html']:
        for f in out_target.rglob(ext):
            f.unlink()
    for d in out_target.rglob('build_tmp'):
        shutil.rmtree(d, ignore_errors=True)
    for d in out_target.rglob('build'):
        shutil.rmtree(d, ignore_errors=True)

print(f'\nDone → {OUTPUT}')
