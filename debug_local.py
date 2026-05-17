#!/usr/bin/env python3
"""
Local environment diagnostic script
Run this to see what your local environment looks like vs CI
"""

import sys
import os
import platform
import subprocess


def run_command(cmd):
    """Run a command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"


def main():
    print("LOCAL ENVIRONMENT DIAGNOSTIC")
    print("=" * 50)
    
    print(f"Platform: {platform.platform()}")
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Current directory: {os.getcwd()}")
    
    print("\nPACKAGE VERSIONS:")
    packages = ['pytest', 'numpy', 'pandas', 'scikit-learn', 'joblib']
    for pkg in packages:
        try:
            module = __import__(pkg.replace('-', '_'))
            version = getattr(module, '__version__', 'Unknown')
            print(f"  {pkg}: {version}")
        except ImportError:
            print(f"  {pkg}: NOT INSTALLED")
    
    print(f"\nPIP LIST:")
    pip_list = run_command("pip list")
    print(pip_list[:500] + "..." if len(pip_list) > 500 else pip_list)
    
    print(f"\nPROJECT STRUCTURE:")
    for root, dirs, files in os.walk('.'):
        # Skip deep nested directories
        level = root.replace('.', '').count(os.sep)
        if level < 3:
            indent = ' ' * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in files[:10]:  # Limit files shown
                print(f"{subindent}{file}")
    
    print(f"\nRUNNING MINIMAL TEST:")
    try:
        # Test basic imports
        import numpy as np
        import pandas as pd
        print("OK: NumPy and Pandas import successfully")
        
        # Test basic operations
        arr = np.array([1, 2, 3])
        df = pd.DataFrame({'A': [1, 2, 3]})
        print("OK: Basic operations work")
        
        # Test sklearn
        from sklearn.linear_model import LinearRegression
        model = LinearRegression()
        print("OK: Scikit-learn imports successfully")
        
    except Exception as e:
        print(f"ERROR in basic test: {e}")
    
    print("\nRECOMMENDATIONS:")
    print("1. Compare this output with CI logs")
    print("2. Check for version mismatches")
    print("3. Look for missing dependencies")
    print("4. Verify file structure matches CI expectations")


if __name__ == "__main__":
    main()