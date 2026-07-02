#!/usr/bin/env python3
"""
Package OpenClaw Memory System for distribution
"""

import os
import shutil
import zipfile
from pathlib import Path

def create_package():
    """Create distributable package"""
    
    base_dir = Path(__file__).parent
    dist_dir = base_dir / "dist"
    dist_dir.mkdir(exist_ok=True)
    
    # Package name
    version = "1.0.0"
    package_name = f"openclaw-memory-system-{version}"
    package_dir = dist_dir / package_name
    
    # Clean existing
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir()
    
    # Files to include
    include_files = [
        "README.md",
        "requirements.txt",
        "setup.py",
        "check_install.py",
    ]
    
    include_dirs = [
        "core",
        "integration",
        "cli",
        "tests",
        "data",
    ]
    
    # Copy files
    for file in include_files:
        src = base_dir / file
        dst = package_dir / file
        if src.exists():
            shutil.copy2(src, dst)
            print(f"  Copied: {file}")
    
    # Copy directories
    for dir_name in include_dirs:
        src_dir = base_dir / dir_name
        dst_dir = package_dir / dir_name
        if src_dir.exists():
            shutil.copytree(src_dir, dst_dir)
            print(f"  Copied: {dir_name}/")
    
    # Create ZIP
    zip_path = dist_dir / f"{package_name}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in package_dir.rglob('*'):
            if file.is_file():
                arcname = file.relative_to(package_dir)
                zf.write(file, arcname)
    
    print(f"\nPackage created: {zip_path}")
    print(f"Size: {zip_path.stat().st_size / 1024:.1f} KB")
    
    return zip_path

if __name__ == "__main__":
    print("\n" + "="*60)
    print("OpenClaw Memory System - Package Builder")
    print("="*60)
    print()
    
    create_package()
