#!/usr/bin/env python3
"""
GitHub Actions Log Reader for Helios-Grid CI/CD Pipeline
Fetches and analyzes workflow run logs from GitHub API
"""

import json
import os
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional

import requests


class GitHubActionsLogReader:
    """GitHub Actions log reader and analyzer"""

    def __init__(self, repo_owner: str, repo_name: str, token: Optional[str] = None):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Helios-Grid-Log-Reader/1.0"
        }
        
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
        else:
            print("⚠️  No GitHub token provided. API rate limits will be lower.")
            print("   Set GITHUB_TOKEN environment variable for better access.")

    def get_workflow_runs(self, branch: str = "feature/premium-mobile-ui-cicd", limit: int = 5) -> List[Dict]:
        """Get recent workflow runs for the specified branch"""
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/actions/runs"
        params = {
            "branch": branch,
            "per_page": limit,
            "status": "completed"  # Get completed runs first
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json().get("workflow_runs", [])
        except requests.RequestException as e:
            print(f"❌ Error fetching workflow runs: {e}")
            return []

    def get_workflow_jobs(self, run_id: int) -> List[Dict]:
        """Get jobs for a specific workflow run"""
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/actions/runs/{run_id}/jobs"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json().get("jobs", [])
        except requests.RequestException as e:
            print(f"❌ Error fetching jobs for run {run_id}: {e}")
            return []

    def get_job_logs(self, job_id: int) -> str:
        """Get logs for a specific job"""
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/actions/jobs/{job_id}/logs"
        
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.text
            else:
                return f"❌ Could not fetch logs (Status: {response.status_code})"
        except requests.RequestException as e:
            return f"❌ Error fetching logs: {e}"

    def analyze_logs(self, logs: str) -> Dict:
        """Analyze logs for errors, warnings, and key information"""
        analysis = {
            "errors": [],
            "warnings": [],
            "test_results": [],
            "build_info": [],
            "security_issues": [],
            "performance_info": []
        }
        
        lines = logs.split('\n')
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # Extract errors
            if any(keyword in line_lower for keyword in ['error:', 'failed:', 'exception:', 'traceback']):
                analysis["errors"].append({
                    "line": i + 1,
                    "content": line.strip(),
                    "context": self._get_context(lines, i)
                })
            
            # Extract warnings
            elif any(keyword in line_lower for keyword in ['warning:', 'warn:', 'deprecated']):
                analysis["warnings"].append({
                    "line": i + 1,
                    "content": line.strip()
                })
            
            # Extract test results
            elif any(keyword in line_lower for keyword in ['passed', 'failed', 'skipped', 'test']):
                if re.search(r'\d+\s+(passed|failed|skipped)', line_lower):
                    analysis["test_results"].append({
                        "line": i + 1,
                        "content": line.strip()
                    })
            
            # Extract build information
            elif any(keyword in line_lower for keyword in ['installing', 'building', 'compiling']):
                analysis["build_info"].append({
                    "line": i + 1,
                    "content": line.strip()
                })
            
            # Extract security issues
            elif any(keyword in line_lower for keyword in ['vulnerability', 'cve-', 'security']):
                analysis["security_issues"].append({
                    "line": i + 1,
                    "content": line.strip()
                })
        
        return analysis

    def _get_context(self, lines: List[str], index: int, context_size: int = 2) -> List[str]:
        """Get context lines around an error"""
        start = max(0, index - context_size)
        end = min(len(lines), index + context_size + 1)
        return [f"{i+1}: {lines[i].strip()}" for i in range(start, end)]

    def format_analysis(self, analysis: Dict, job_name: str) -> str:
        """Format analysis results for display"""
        output = [f"\n🔍 ANALYSIS FOR JOB: {job_name}"]
        output.append("=" * 60)
        
        if analysis["errors"]:
            output.append(f"\n❌ ERRORS ({len(analysis['errors'])}):")
            for error in analysis["errors"][:5]:  # Show first 5 errors
                output.append(f"  Line {error['line']}: {error['content']}")
                if error.get("context"):
                    output.append("    Context:")
                    for ctx_line in error["context"]:
                        output.append(f"      {ctx_line}")
                output.append("")
        
        if analysis["warnings"]:
            output.append(f"\n⚠️  WARNINGS ({len(analysis['warnings'])}):")
            for warning in analysis["warnings"][:3]:  # Show first 3 warnings
                output.append(f"  Line {warning['line']}: {warning['content']}")
        
        if analysis["test_results"]:
            output.append(f"\n🧪 TEST RESULTS:")
            for test in analysis["test_results"]:
                output.append(f"  {test['content']}")
        
        if analysis["security_issues"]:
            output.append(f"\n🔒 SECURITY ISSUES ({len(analysis['security_issues'])}):")
            for issue in analysis["security_issues"]:
                output.append(f"  Line {issue['line']}: {issue['content']}")
        
        return "\n".join(output)

    def get_latest_run_analysis(self, branch: str = "feature/premium-mobile-ui-cicd") -> str:
        """Get comprehensive analysis of the latest workflow run"""
        print(f"🔍 Fetching latest workflow runs for branch: {branch}")
        
        runs = self.get_workflow_runs(branch)
        if not runs:
            return "❌ No workflow runs found for the specified branch."
        
        latest_run = runs[0]
        run_id = latest_run["id"]
        
        print(f"📊 Analyzing run #{run_id} - {latest_run['display_title']}")
        print(f"   Status: {latest_run['status']} | Conclusion: {latest_run.get('conclusion', 'N/A')}")
        print(f"   Created: {latest_run['created_at']}")
        print(f"   URL: {latest_run['html_url']}")
        
        jobs = self.get_workflow_jobs(run_id)
        if not jobs:
            return f"❌ No jobs found for run {run_id}"
        
        full_analysis = [f"📋 WORKFLOW RUN ANALYSIS"]
        full_analysis.append(f"Run ID: {run_id}")
        full_analysis.append(f"Branch: {branch}")
        full_analysis.append(f"Status: {latest_run['status']} | Conclusion: {latest_run.get('conclusion', 'N/A')}")
        full_analysis.append(f"URL: {latest_run['html_url']}")
        full_analysis.append("=" * 80)
        
        for job in jobs:
            job_name = job["name"]
            job_status = job["status"]
            job_conclusion = job.get("conclusion", "N/A")
            
            print(f"   📝 Analyzing job: {job_name} ({job_status}/{job_conclusion})")
            
            full_analysis.append(f"\n🔧 JOB: {job_name}")
            full_analysis.append(f"Status: {job_status} | Conclusion: {job_conclusion}")
            
            if job_conclusion in ["failure", "cancelled"]:
                logs = self.get_job_logs(job["id"])
                if logs and not logs.startswith("❌"):
                    analysis = self.analyze_logs(logs)
                    formatted = self.format_analysis(analysis, job_name)
                    full_analysis.append(formatted)
                else:
                    full_analysis.append(f"❌ Could not fetch logs for {job_name}")
            else:
                full_analysis.append(f"✅ Job completed successfully")
        
        return "\n".join(full_analysis)

    def save_analysis(self, analysis: str, filename: str = None) -> str:
        """Save analysis to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"github_actions_analysis_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(analysis)
            return filename
        except Exception as e:
            print(f"❌ Error saving analysis: {e}")
            return None


def main():
    """Main function to run the log analysis"""
    print("🚀 GitHub Actions Log Reader for Helios-Grid")
    print("=" * 50)
    
    # Repository configuration
    repo_owner = "sankeashok"
    repo_name = "Helios-Grid"
    branch = "feature/premium-mobile-ui-cicd"
    
    # Initialize log reader
    log_reader = GitHubActionsLogReader(repo_owner, repo_name)
    
    # Get and analyze latest run
    analysis = log_reader.get_latest_run_analysis(branch)
    
    # Display analysis
    print(analysis)
    
    # Save to file
    filename = log_reader.save_analysis(analysis)
    if filename:
        print(f"\n💾 Analysis saved to: {filename}")
    
    # Provide recommendations
    print("\n🎯 RECOMMENDATIONS:")
    print("1. Check the detailed error messages above")
    print("2. Focus on jobs with 'failure' conclusion")
    print("3. Look for patterns in error messages")
    print("4. Check if dependencies are missing or incompatible")
    print("5. Verify file paths and permissions")


if __name__ == "__main__":
    # Check if requests is available
    try:
        import requests
    except ImportError:
        print("❌ 'requests' library not found. Installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
        import requests
    
    main()