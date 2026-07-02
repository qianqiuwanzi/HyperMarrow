import os
from setuptools import find_packages

# 列出所有 __init__.py 文件
init_files = []
for root, dirs, files in os.walk('.'):
    if '__init__.py' in files:
        init_files.append(root)

print("Directories with __init__.py:")
for f in init_files:
    print(f"  {f}")

# 尝试用明确的路径
packages = find_packages(include=['core', 'integration'])
print(f"\nPackages (with include): {packages}")

packages2 = find_packages(exclude=['tests', 'examples'])
print(f"Packages (excluding tests/examples): {packages2}")
