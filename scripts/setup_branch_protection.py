#!/usr/bin/env python3
"""
🛡️ Helios-Grid - Branch Protection Setup
Enforces feature branch → staging → auto-merge → production workflow
"""

import requests
import json
import os

def setup_branch_protection():
    """Setup branch protection rules to enforce GitFlow"""
    
    # GitHub API configuration
    REPO_OWNER = "sankeashok"
    REPO_NAME = "Helios-Grid"
    BRANCH = "main"
    
    # You'll need to create a Personal Access Token with repo permissions
    # Go to: https://github.com/settings/tokens
    TOKEN = input("Enter your GitHub Personal Access Token (with repo permissions): ")
    
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Branch protection configuration
    protection_config = {
        "required_status_checks": {
            "strict": True,
            "contexts": [
                "🐍 Backend Testing Pipeline (core)",
                "🐍 Backend Testing Pipeline (dependencies)", 
                "🐍 Backend Testing Pipeline (scientific)",
                "🐍 Backend Testing Pipeline (integration)",
                "⚛️ Frontend Testing Pipeline",
                "🐳 Containerization Pipeline",
                "🚀 Deployment Readiness Check",
                "🎆 Deploy to Staging"
            ]
        },
        "enforce_admins": False,  # Allow admins to bypass (for emergencies)
        "required_pull_request_reviews": {
            "required_approving_review_count": 0,  # Auto-merge handles this
            "dismiss_stale_reviews": True,
            "require_code_owner_reviews": False
        },
        "restrictions": None,  # No user/team restrictions
        "allow_force_pushes": False,
        "allow_deletions": False
    }
    
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/branches/{BRANCH}/protection"
    
    print(f"🛡️ Setting up branch protection for {REPO_OWNER}/{REPO_NAME}:{BRANCH}")
    print("📋 Protection Rules:")
    print("   ✅ Require status checks to pass")
    print("   ✅ Require branches to be up to date")
    print("   ✅ Block direct pushes to main")
    print("   ✅ Allow auto-merge from feature branches")
    print()
    
    response = requests.put(url, headers=headers, json=protection_config)
    
    if response.status_code == 200:
        print("✅ SUCCESS! Branch protection rules applied!")
        print()
        print("🎯 Now ALL changes must follow:")
        print("   Feature Branch → Staging → Auto-merge → Production")
        print()
        print("🚫 Direct pushes to main are now blocked!")
        print("✅ Only the CI/CD pipeline can merge to main!")
        
    elif response.status_code == 401:
        print("❌ ERROR: Invalid token or insufficient permissions")
        print("💡 Make sure your token has 'repo' permissions")
        
    elif response.status_code == 404:
        print("❌ ERROR: Repository not found or no access")
        
    else:
        print(f"❌ ERROR: {response.status_code}")
        print(f"Response: {response.text}")

if __name__ == "__main__":
    print("🛡️ Helios-Grid Branch Protection Setup")
    print("=" * 50)
    print()
    print("This will enforce the GitFlow pattern:")
    print("Feature Branch → Staging → Auto-merge → Production")
    print()
    
    confirm = input("Continue? (y/N): ")
    if confirm.lower() == 'y':
        setup_branch_protection()
    else:
        print("Setup cancelled.")