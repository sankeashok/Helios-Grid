"""
Local CI/CD Pipeline Test Script
Simulates the GitHub Actions pipeline locally to debug issues
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"\nTesting: {description}")
    print(f"Command: {cmd}")
    print("-" * 50)

    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=Path.cwd()
        )

        if result.stdout:
            print("STDOUT:")
            print(result.stdout)

        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        if result.returncode == 0:
            print(f"PASSED: {description}")
            return True
        else:
            print(f"FAILED: {description} (exit code: {result.returncode})")
            return False

    except Exception as e:
        print(f"ERROR: {description} - {e}")
        return False


def test_code_quality():
    """Test Layer 1: Code Quality & Security"""
    print("\n" + "=" * 60)
    print("LAYER 1: CODE QUALITY & SECURITY FOUNDATION")
    print("=" * 60)

    # Install quality tools
    if not run_command(
        "pip install black flake8 bandit safety", "Installing Quality Tools"
    ):
        return False

    # Black formatting check
    if not run_command(
        'python -m black --check --diff . --exclude="helios-grid-env/|react-frontend/node_modules/"',
        "Black Formatting Check",
    ):
        print("Running Black auto-format...")
        run_command(
            'python -m black . --exclude="helios-grid-env/|react-frontend/node_modules/"',
            "Auto-formatting with Black",
        )

    # Flake8 linting
    if not run_command(
        "python -m flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude=helios-grid-env,react-frontend/node_modules",
        "Flake8 Linting",
    ):
        return False

    # Security scan (optional)
    run_command(
        "python -m bandit -r . -f json -o bandit-report.json --exclude ./helios-grid-env,./react-frontend/node_modules",
        "Security Scan (Bandit)",
    )

    return True


def test_backend():
    """Test Layer 2: Backend Testing"""
    print("\n" + "=" * 60)
    print("LAYER 2: BACKEND TESTING PIPELINE")
    print("=" * 60)

    # Core tests
    if not run_command("python tests/test_minimal.py", "Core Tests"):
        return False

    # Install pytest
    if not run_command("pip install pytest", "Installing pytest"):
        return False

    # Dependency tests
    if not run_command("python -m pytest tests/test_minimal.py -v", "Dependency Tests"):
        return False

    # Scientific packages
    if not run_command(
        "pip install numpy pandas scikit-learn joblib", "Installing Scientific Packages"
    ):
        return False

    # Test scientific imports
    test_imports = [
        "python -c \"import numpy; print(f'NumPy: {numpy.__version__}')\"",
        "python -c \"import pandas; print(f'Pandas: {pandas.__version__}')\"",
        "python -c \"import sklearn; print(f'Scikit-learn: {sklearn.__version__}')\"",
    ]

    for cmd in test_imports:
        if not run_command(
            cmd, f"Testing import: {cmd.split('import ')[1].split(';')[0]}"
        ):
            return False

    # Integration tests
    if not run_command(
        "python -m pytest tests/test_basic.py -v --tb=short", "Integration Tests"
    ):
        return False

    return True


def test_frontend():
    """Test Layer 3: Frontend Testing"""
    print("\n" + "=" * 60)
    print("LAYER 3: FRONTEND TESTING PIPELINE")
    print("=" * 60)

    frontend_dir = Path("react-frontend")
    if not frontend_dir.exists():
        print("Frontend directory not found, skipping frontend tests")
        return True

    # Change to frontend directory
    original_dir = os.getcwd()
    try:
        os.chdir(frontend_dir)

        # Install dependencies
        if not run_command("npm ci", "Installing Frontend Dependencies"):
            return False

        # Run tests
        if not run_command(
            "npm test -- --coverage --watchAll=false --passWithNoTests",
            "Frontend Tests",
        ):
            return False

        # Build production
        if not run_command("npm run build", "Frontend Build"):
            return False

        return True

    finally:
        os.chdir(original_dir)


def test_containerization():
    """Test Layer 4: Containerization"""
    print("\n" + "=" * 60)
    print("LAYER 4: CONTAINERIZATION PIPELINE")
    print("=" * 60)

    # Check if Docker is available
    if not run_command("docker --version", "Docker Version Check"):
        print("Docker not available, skipping containerization tests")
        return True

    # Check required files
    required_files = ["Dockerfile.production", "requirements-docker.txt"]
    for file in required_files:
        if not Path(file).exists():
            print(f"Missing {file}, skipping Docker build")
            return True

    # Build Docker image
    if not run_command(
        "docker build -f Dockerfile.production -t helios-grid:test .", "Docker Build"
    ):
        return False

    return True


def main():
    """Run complete local CI/CD test"""
    print("HELIOS-GRID LOCAL CI/CD PIPELINE TEST")
    print("=" * 60)
    print(f"Python Version: {sys.version}")
    print(f"Working Directory: {os.getcwd()}")
    print(f"Platform: {sys.platform}")

    results = {}

    # Layer 1: Code Quality
    results["code_quality"] = test_code_quality()

    # Layer 2: Backend Testing
    if results["code_quality"]:
        results["backend"] = test_backend()
    else:
        print("Skipping backend tests due to code quality failures")
        results["backend"] = False

    # Layer 3: Frontend Testing
    if results["code_quality"]:
        results["frontend"] = test_frontend()
    else:
        print("Skipping frontend tests due to code quality failures")
        results["frontend"] = False

    # Layer 4: Containerization
    if results["code_quality"] and results["backend"]:
        results["containerization"] = test_containerization()
    else:
        print("Skipping containerization due to previous failures")
        results["containerization"] = False

    # Summary
    print("\n" + "=" * 60)
    print("PIPELINE TEST SUMMARY")
    print("=" * 60)

    for layer, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"{layer.upper():20} | {status}")

    all_passed = all(results.values())

    if all_passed:
        print("\nALL TESTS PASSED! Pipeline should work in GitHub Actions.")
    else:
        print("\nSOME TESTS FAILED. Fix issues before pushing to GitHub.")
        failed_layers = [layer for layer, passed in results.items() if not passed]
        print(f"Failed layers: {', '.join(failed_layers)}")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
