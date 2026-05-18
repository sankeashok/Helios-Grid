#!/usr/bin/env python3
"""
Check GitHub repository settings and branch protection rules
"""

import requests
import json

def check_repo_settings():
    """Check repository settings that might affect auto-merge"""
    
    repo_owner = "sankeashok"
    repo_name = "Helios-Grid"
    
    print("🔍 CHECKING REPOSITORY SETTINGS")
    print("=" * 50)
    
    # Check repository general settings
    repo_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
    
    try:
        response = requests.get(repo_url)
        if response.status_code == 200:
            repo_data = response.json()
            
            print("📋 Repository Settings:")
            print(f"   - Allow merge commits: {repo_data.get('allow_merge_commit', 'Unknown')}")
            print(f"   - Allow squash merging: {repo_data.get('allow_squash_merge', 'Unknown')}")
            print(f"   - Allow rebase merging: {repo_data.get('allow_rebase_merge', 'Unknown')}")
            print(f"   - Delete head branches: {repo_data.get('delete_branch_on_merge', 'Unknown')}")
            print(f"   - Allow auto-merge: {repo_data.get('allow_auto_merge', 'Unknown')}")
            print()
            
        else:
            print(f"❌ Could not fetch repository settings: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error checking repository: {e}")
    
    # Check branch protection rules for main
    branch_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/branches/main/protection"
    
    try:
        response = requests.get(branch_url)
        if response.status_code == 200:
            protection_data = response.json()
            
            print("🛡️ Main Branch Protection Rules:")
            print(f"   - Required status checks: {protection_data.get('required_status_checks', {}).get('strict', 'None')}")
            print(f"   - Enforce admins: {protection_data.get('enforce_admins', {}).get('enabled', 'Unknown')}")
            print(f"   - Required pull request reviews: {protection_data.get('required_pull_request_reviews', 'None')}")
            print(f"   - Restrictions: {protection_data.get('restrictions', 'None')}")
            print()
            
            # Check required status checks
            if protection_data.get('required_status_checks'):
                contexts = protection_data['required_status_checks'].get('contexts', [])
                if contexts:
                    print("📋 Required Status Checks:")
                    for context in contexts:
                        print(f"   - {context}")
                    print()
                        
        elif response.status_code == 404:
            print("✅ Main Branch Protection: No protection rules found")
            print("   - This means auto-merge should work without restrictions")
            print()
        else:
            print(f"❌ Could not fetch branch protection: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error checking branch protection: {e}")
    
    # Check GitHub Actions permissions
    print("🔧 REQUIRED PERMISSIONS FOR AUTO-MERGE:")
    print("=" * 50)
    print("Repository Settings → Actions → General:")
    print("   ✅ Workflow permissions: Read and write permissions")
    print("   ✅ Allow GitHub Actions to create and approve pull requests: ENABLED")
    print()
    print("Repository Settings → General:")
    print("   ✅ Allow auto-merge: ENABLED")
    print("   ✅ Automatically delete head branches: ENABLED (optional)")
    print()
    print("Branch Protection (if any):")
    print("   ✅ Allow force pushes: ENABLED (for auto-merge)")
    print("   ✅ Allow deletions: ENABLED (optional)")
    print()
    
    print("🔗 CHECK THESE URLS:")
    print("=" * 50)
    print(f"Repository Settings: https://github.com/{repo_owner}/{repo_name}/settings")
    print(f"Actions Permissions: https://github.com/{repo_owner}/{repo_name}/settings/actions")
    print(f"Branch Protection: https://github.com/{repo_owner}/{repo_name}/settings/branches")
    print(f"Auto-merge Setting: https://github.com/{repo_owner}/{repo_name}/settings (scroll to Pull Requests)")

if __name__ == "__main__":
    check_repo_settings()