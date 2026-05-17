#!/usr/bin/env python3
"""
Simple GitHub Actions Status Checker
Works without authentication for public repositories
"""

import json
import sys
from datetime import datetime

try:
    import requests
except ImportError:
    print("Installing requests library...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests


def check_workflow_status():
    """Check the status of recent workflow runs"""
    repo_owner = "sankeashok"
    repo_name = "Helios-Grid"
    branch = "feature/premium-mobile-ui-cicd"
    
    print("Checking GitHub Actions Status for Helios-Grid")
    print("=" * 60)
    
    # Get workflow runs
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/runs"
    params = {
        "branch": branch,
        "per_page": 5
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        runs = data.get("workflow_runs", [])
        if not runs:
            print("❌ No workflow runs found")
            return
        
        print(f"Found {len(runs)} recent workflow runs:\n")
        
        for i, run in enumerate(runs, 1):
            status = run["status"]
            conclusion = run.get("conclusion", "N/A")
            created_at = run["created_at"]
            title = run["display_title"]
            run_number = run["run_number"]
            
            # Status emoji
            if conclusion == "success":
                emoji = "[OK]"
            elif conclusion == "failure":
                emoji = "[FAIL]"
            elif conclusion == "cancelled":
                emoji = "[CANCEL]"
            elif status == "in_progress":
                emoji = "[RUNNING]"
            else:
                emoji = "[PENDING]"
            
            print(f"{emoji} Run #{run_number}: {title}")
            print(f"   Status: {status} | Conclusion: {conclusion}")
            print(f"   Created: {created_at}")
            print(f"   URL: {run['html_url']}")
            
            # Get jobs for this run
            jobs_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/runs/{run['id']}/jobs"
            try:
                jobs_response = requests.get(jobs_url)
                if jobs_response.status_code == 200:
                    jobs_data = jobs_response.json()
                    jobs = jobs_data.get("jobs", [])
                    
                    print(f"   Jobs ({len(jobs)}):")
                    for job in jobs:
                        job_status = job["status"]
                        job_conclusion = job.get("conclusion", "N/A")
                        job_name = job["name"]
                        
                        if job_conclusion == "success":
                            job_emoji = "[OK]"
                        elif job_conclusion == "failure":
                            job_emoji = "[FAIL]"
                        elif job_conclusion == "cancelled":
                            job_emoji = "[CANCEL]"
                        elif job_status == "in_progress":
                            job_emoji = "[RUNNING]"
                        else:
                            job_emoji = "[PENDING]"
                        
                        print(f"     {job_emoji} {job_name}: {job_status}/{job_conclusion}")
                        
                        # If job failed, try to get some error info
                        if job_conclusion == "failure":
                            print(f"       Job URL: {job['html_url']}")
            
            except Exception as e:
                print(f"   Could not fetch job details: {e}")
            
            print()  # Empty line between runs
        
        # Summary
        latest_run = runs[0]
        print("SUMMARY:")
        print(f"Latest run status: {latest_run['status']}")
        print(f"Latest run conclusion: {latest_run.get('conclusion', 'N/A')}")
        
        if latest_run.get("conclusion") == "failure":
            print("\nTROUBLESHOOTING STEPS:")
            print("1. Click on the failed job URLs above to see detailed logs")
            print("2. Look for error messages in the GitHub Actions interface")
            print("3. Check if dependencies are missing or incompatible")
            print("4. Verify Docker build issues or test failures")
            print("5. Check for permission or authentication issues")
        
        print(f"\nView all runs: https://github.com/{repo_owner}/{repo_name}/actions")
        
    except requests.RequestException as e:
        print(f"❌ Error fetching workflow data: {e}")
        print("This might be due to:")
        print("- Network connectivity issues")
        print("- GitHub API rate limiting")
        print("- Repository access restrictions")


def check_specific_run(run_id=None):
    """Check a specific workflow run by ID"""
    if not run_id:
        print("Please provide a run ID")
        return
    
    repo_owner = "sankeashok"
    repo_name = "Helios-Grid"
    
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/runs/{run_id}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        run_data = response.json()
        
        print(f"Workflow Run #{run_data['run_number']} Details:")
        print(f"Title: {run_data['display_title']}")
        print(f"Status: {run_data['status']}")
        print(f"Conclusion: {run_data.get('conclusion', 'N/A')}")
        print(f"URL: {run_data['html_url']}")
        
    except requests.RequestException as e:
        print(f"❌ Error fetching run {run_id}: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Check specific run ID if provided
        try:
            run_id = int(sys.argv[1])
            check_specific_run(run_id)
        except ValueError:
            print("❌ Invalid run ID. Please provide a numeric run ID.")
    else:
        # Check recent workflow status
        check_workflow_status()