#!/usr/bin/env python3
"""
Create GraphDB repositories via REST API
GraphDB Free doesn't support Turtle config, so we use a simpler approach
"""

import requests
import time
import sys

GRAPHDB_URL = "http://localhost:7200"

# Repository configurations
REPOS = [
    {"id": "demo", "title": "Demo Medical KG"},
    {"id": "hearing", "title": "Hearing & Tinnitus KG"},
    {"id": "psychiatry", "title": "Psychiatry & Depression KG"},
    {"id": "unified", "title": "Unified Medical KG (All graphs + alignment)"}
]

def wait_for_graphdb():
    """Wait for GraphDB to be ready"""
    print("⏳ Waiting for GraphDB to be ready...")
    for i in range(30):
        try:
            response = requests.get(f"{GRAPHDB_URL}/rest/repositories", timeout=2)
            if response.status_code == 200:
                print("✅ GraphDB is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        print(f"   Attempt {i+1}/30...")
        time.sleep(2)
    print("❌ GraphDB failed to start")
    return False

def create_repository(repo_id, title):
    """Create a repository using GraphDB REST API"""
    print(f"\n📦 Creating repository: {repo_id}")

    # Check if exists
    try:
        response = requests.get(f"{GRAPHDB_URL}/rest/repositories/{repo_id}")
        if response.status_code == 200:
            print(f"   ⚠️  Repository {repo_id} already exists, skipping")
            return True
    except:
        pass

    # GraphDB Free repository config (simplified)
    config = {
        "id": repo_id,
        "params": {
            "ruleset": {
                "label": "Ruleset",
                "name": "ruleset",
                "value": "owl2-rl-optimized"
            },
            "title": {
                "label": "Repository title",
                "name": "title",
                "value": title
            },
            "checkForInconsistencies": {
                "label": "Check for inconsistencies",
                "name": "checkForInconsistencies",
                "value": "false"
            },
            "disableSameAs": {
                "label": "Disable owl:sameAs",
                "name": "disableSameAs",
                "value": "false"
            },
            "baseURL": {
                "label": "Base URL",
                "name": "baseURL",
                "value": "http://example.org/grape#"
            },
            "repositoryType": {
                "label": "Repository type",
                "name": "repositoryType",
                "value": "file-repository"
            },
            "id": {
                "label": "Repository ID",
                "name": "id",
                "value": repo_id
            },
            "title": {
                "label": "Repository title",
                "name": "title",
                "value": title
            }
        },
        "title": title,
        "type": "free"
    }

    try:
        response = requests.post(
            f"{GRAPHDB_URL}/rest/repositories",
            json=config,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code in [200, 201]:
            print(f"   ✅ Repository {repo_id} created successfully")
            return True
        else:
            print(f"   ⚠️  Response: {response.status_code}")
            print(f"   {response.text}")
            # Try alternative method with form data
            return create_repository_form(repo_id, title)
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def create_repository_form(repo_id, title):
    """Alternative method using form data"""
    print(f"   Trying alternative method for {repo_id}...")

    form_data = {
        "type": "free",
        "title": title,
        "id": repo_id,
        "ruleset": "owl2-rl-optimized",
        "baseURL": "http://example.org/grape#",
        "checkForInconsistencies": "false",
        "disableSameAs": "false"
    }

    try:
        response = requests.post(
            f"{GRAPHDB_URL}/rest/repositories",
            data=form_data
        )

        if response.status_code in [200, 201]:
            print(f"   ✅ Repository {repo_id} created with form method")
            return True
        else:
            print(f"   ⚠️  Form method also failed: {response.status_code}")
            print(f"   {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Form method error: {e}")
        return False

def main():
    print("🍇 Grape GraphDB - Repository Creator")
    print("=" * 60)

    if not wait_for_graphdb():
        sys.exit(1)

    print("\n📦 Creating repositories...")
    success_count = 0

    for repo in REPOS:
        if create_repository(repo["id"], repo["title"]):
            success_count += 1
        time.sleep(1)

    print("\n" + "=" * 60)
    print(f"✅ Created {success_count}/{len(REPOS)} repositories")

    if success_count == 0:
        print("\n⚠️  Could not create repositories via API.")
        print("   Please create them manually via GraphDB Workbench:")
        print(f"   1. Open {GRAPHDB_URL}")
        print("   2. Go to Setup → Repositories → Create new repository")
        print("   3. Select 'GraphDB Free' and create these repos:")
        for repo in REPOS:
            print(f"      - ID: {repo['id']}, Title: {repo['title']}")
        sys.exit(1)

    print(f"\n🌐 GraphDB Workbench: {GRAPHDB_URL}")
    print("\n🔍 Test with:")
    print(f"   curl {GRAPHDB_URL}/rest/repositories")

if __name__ == "__main__":
    main()
