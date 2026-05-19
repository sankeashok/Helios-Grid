#!/usr/bin/env python3
"""
🚀 Helios-Grid MLOps - Production Deployment Script
Merges feature branch to main and triggers production deployment
"""

import subprocess
import sys
import time

def run_command(cmd, description):
    """Execute command and handle errors"""
    print(f"Running: {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        print(f"Success: {description} completed")
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error: {description} failed: {e.stderr}")
        return None

def main():
    """Deploy feature branch to production"""
    print("Helios-Grid MLOps - Production Deployment")
    print("=" * 50)
    
    # Get current branch
    current_branch = run_command("git branch --show-current", "Getting current branch")
    if not current_branch:
        sys.exit(1)
    
    print(f"Current branch: {current_branch}")
    
    if current_branch == "main":
        print("Already on main branch. Pushing to trigger production deployment...")
        run_command("git push origin main", "Pushing to main")
        return
    
    # Ensure we're up to date
    run_command("git fetch origin", "Fetching latest changes")
    
    # Switch to main and merge
    if not run_command("git checkout main", "Switching to main branch"):
        sys.exit(1)
    
    if not run_command("git pull origin main", "Pulling latest main"):
        sys.exit(1)
    
    if not run_command(f"git merge {current_branch}", f"Merging {current_branch} to main"):
        print("Merge failed. Please resolve conflicts manually.")
        sys.exit(1)
    
    # Push to trigger production deployment
    if not run_command("git push origin main", "Pushing to main (triggers production)"):
        sys.exit(1)
    
    print("\nSUCCESS! Production deployment triggered!")
    print("Check GitHub Actions for deployment status")
    print("Production will be live shortly at your Azure endpoint")

if __name__ == "__main__":
    main()