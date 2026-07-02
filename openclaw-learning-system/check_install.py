#!/usr/bin/env python3
"""
Check if OpenClaw Learning System is properly installed
"""

import sys

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major >= 3 and version.minor >= 10:
        print("  ✓ Python version OK")
        return True
    else:
        print("  ✗ Python 3.10+ required")
        return False

def check_dependencies():
    """Check required dependencies"""
    print("\nChecking dependencies...")
    
    deps = [("numpy", "numpy>=1.21.0")]
    results = []
    
    for module, pip_name in deps:
        try:
            __import__(module)
            print(f"  ✓ {pip_name}")
            results.append(True)
        except ImportError:
            print(f"  ✗ {pip_name} - not installed")
            results.append(False)
    
    return all(results)

def check_core_modules():
    """Check core modules can be imported"""
    print("\nChecking core modules...")
    
    modules = [
        "core.q_learning_agent",
        "core.rl_decision_helper",
        "integration.decision_check",
    ]
    
    results = []
    
    for module in modules:
        try:
            __import__(module)
            print(f"  ✓ {module}")
            results.append(True)
        except ImportError as e:
            print(f"  ✗ {module} - {str(e)[:50]}")
            results.append(False)
    
    return all(results)

def check_data_files():
    """Check data files exist"""
    import os
    
    print("\nChecking data files...")
    
    files = [
        "data/q_table.json",
        "data/rl_decision_history.json",
    ]
    
    results = []
    
    for file in files:
        if os.path.exists(file):
            print(f"  ✓ {file}")
            results.append(True)
        else:
            print(f"  ⚠ {file} - will be created on first run")
            results.append(True)  # Not critical
    
    return True

def main():
    """Run all checks"""
    print("\n" + "="*60)
    print("OpenClaw Learning System - Installation Check")
    print("="*60)
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Core Modules", check_core_modules),
        ("Data Files", check_data_files),
    ]
    
    results = []
    
    for name, check_func in checks:
        print()
        success = check_func()
        results.append((name, success))
    
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {name}: {status}")
    
    passed = sum(1 for _, s in results if s)
    
    if passed == len(results):
        print("\n✓ All checks passed! System ready.")
        print("\nRun examples:")
        print("  python examples/basic_q_learning.py")
        print("  python examples/decision_helper.py")
    else:
        print(f"\n⚠ {len(results) - passed} check(s) failed.")
        print("\nTo install missing dependencies:")
        print("  pip install -r requirements.txt")

if __name__ == "__main__":
    main()
