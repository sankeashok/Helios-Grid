#!/usr/bin/env python3
"""
GitHub Actions Status Checker - Clean Version
No emojis to avoid Windows encoding issues
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
    
    print("GitHub Actions Status for Helios-Grid")
    print("=" * 60)
    
    # Get workflow runs
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/runs"
    params = {
        "branch": branch,
        "per_page": 10
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        runs = data.get("workflow_runs", [])
        if not runs:
            print("ERROR: No workflow runs found")
            return
        
        print(f"Found {len(runs)} recent workflow runs:")
        print()
        
        for i, run in enumerate(runs, 1):
            status = run["status"]
            conclusion = run.get("conclusion", "N/A")
            created_at = run["created_at"]
            title = run["display_title"]
            run_number = run["run_number"]
            
            # Status indicator
            if conclusion == "success":
                status_text = "[SUCCESS]"
            elif conclusion == "failure":
                status_text = "[FAILED]"
            elif conclusion == "cancelled":
                status_text = "[CANCELLED]"
            elif status == "in_progress":
                status_text = "[RUNNING]"
            else:
                status_text = "[PENDING]"
            
            # Clean title to avoid encoding issues
            clean_title = title.encode('ascii', 'ignore').decode('ascii')
            
            print(f"{status_text} Run #{run_number}: {clean_title}")
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
                            job_status_text = "[OK]"
                        elif job_conclusion == "failure":
                            job_status_text = "[FAIL]"
                        elif job_conclusion == "cancelled":
                            job_status_text = "[CANCEL]"
                        elif job_status == "in_progress":
                            job_status_text = "[RUNNING]"
                        else:
                            job_status_text = "[PENDING]"
                        
                        print(f"     {job_status_text} {job_name}: {job_status}/{job_conclusion}")
                        
                        # If job failed, show URL for detailed logs
                        if job_conclusion == "failure":
                            print(f"       Failed Job URL: {job['html_url']}")
                            
                            # Try to get some basic error info from job steps
                            steps = job.get("steps", [])
                            failed_steps = [step for step in steps if step.get("conclusion") == "failure"]
                            if failed_steps:
                                print(f"       Failed Steps:")
                                for step in failed_steps[:3]:  # Show first 3 failed steps
                                    print(f"         - {step['name']}")
            
            except Exception as e:
                print(f"   WARNING: Could not fetch job details: {e}")
            
            print()  # Empty line between runs
            
            # Only show first 3 runs in detail to avoid clutter
            if i >= 3:
                break
        
        # Summary of latest run
        latest_run = runs[0]
        print("LATEST RUN SUMMARY:")
        print("=" * 30)
        print(f"Status: {latest_run['status']}")
        print(f"Conclusion: {latest_run.get('conclusion', 'N/A')}")
        print(f"Branch: {latest_run['head_branch']}")
        print(f"Commit: {latest_run['head_sha'][:8]}")
        
        if latest_run.get("conclusion") == "failure":
            print()
            print("TROUBLESHOOTING STEPS:")
            print("1. Click on the failed job URLs above to see detailed logs")
            print("2. Look for error messages in the GitHub Actions interface")
            print("3. Check for dependency installation issues")
            print("4. Verify Docker build problems")
            print("5. Look for test failures or code quality issues")
            print("6. Check for permission or authentication problems")
        
        print()
        print(f"View all runs: https://github.com/{repo_owner}/{repo_name}/actions")
        
        # Show rate limit info
        rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
        if rate_limit_remaining:
            print(f"API Rate Limit Remaining: {rate_limit_remaining}")
        
    except requests.RequestException as e:
        print(f"ERROR: Could not fetch workflow data: {e}")
        print("This might be due to:")
        print("- Network connectivity issues")
        print("- GitHub API rate limiting")
        print("- Repository access restrictions")


def get_latest_failed_jobs():
    """Get details about the latest failed jobs"""
    repo_owner = "sankeashok"
    repo_name = "Helios-Grid"
    branch = "feature/premium-mobile-ui-cicd"
    
    print("LATEST FAILED JOBS ANALYSIS:")
    print("=" * 40)
    
    # Get latest failed run
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/runs"
    params = {
        "branch": branch,
        "status": "completed",
        "conclusion": "failure",
        "per_page": 1
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        runs = data.get("workflow_runs", [])
        if not runs:
            print("No failed runs found recently")
            return
        
        failed_run = runs[0]
        print(f"Analyzing failed run #{failed_run['run_number']}")
        clean_title = failed_run['display_title'].encode('ascii', 'ignore').decode('ascii')
        print(f"Title: {clean_title}")
        print(f"URL: {failed_run['html_url']}")
        print()
        
        # Get jobs for the failed run
        jobs_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/runs/{failed_run['id']}/jobs"
        jobs_response = requests.get(jobs_url)
        
        if jobs_response.status_code == 200:
            jobs_data = jobs_response.json()
            failed_jobs = [job for job in jobs_data.get("jobs", []) if job.get("conclusion") == "failure"]
            
            print(f"Found {len(failed_jobs)} failed jobs:")
            for job in failed_jobs:
                print(f"\nFAILED JOB: {job['name']}")
                print(f"Started: {job['started_at']}")
                print(f"Completed: {job.get('completed_at', 'N/A')}")
                print(f"URL: {job['html_url']}")
                
                # Show failed steps
                steps = job.get("steps", [])
                failed_steps = [step for step in steps if step.get("conclusion") == "failure"]
                
                if failed_steps:
                    print("Failed Steps:")
                    for step in failed_steps:
                        print(f"  - {step['name']} (started: {step.get('started_at', 'N/A')})")
                        if step.get("number"):
                            print(f"    Step #{step['number']}")
        
    except Exception as e:
        print(f"ERROR: Could not analyze failed jobs: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--failed":
        get_latest_failed_jobs()
    else:
        check_workflow_status()
        print()
        print("Run with --failed flag to get detailed analysis of failed jobs")
        print("Example: python check_github_status.py --failed")