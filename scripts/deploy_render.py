#!/usr/bin/env python3
"""Deploy Binance Claw Quiz to Render.com via API"""

import requests
import json
import sys
import time
import os

RENDER_API_KEY = os.environ.get("RENDER_API_KEY", "rnd_YxBytB8BPGumAaSnNjetwPwt76Mk")
OWNER_ID = "tea-d6k6oontskes73bfdkrg"
BASE_URL = "https://api.render.com/v1"

HEADERS = {
    "Authorization": f"Bearer {RENDER_API_KEY}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def create_service(payload):
    resp = requests.post(f"{BASE_URL}/services", headers=HEADERS, json=payload)
    if resp.status_code in (200, 201):
        data = resp.json()
        service = data.get("service", data)
        print(f"  Created: {service.get('name')} -> {service.get('serviceDetails', {}).get('url', 'pending')}")
        return service
    else:
        print(f"  ERROR {resp.status_code}: {resp.text}")
        return None

def set_env_vars(service_id, env_vars):
    for item in env_vars:
        resp = requests.put(
            f"{BASE_URL}/services/{service_id}/env-vars/{item['key']}",
            headers=HEADERS,
            json={"value": item["value"]}
        )
        if resp.status_code in (200, 201):
            print(f"  Set {item['key']}")
        else:
            # Try POST instead
            resp2 = requests.post(
                f"{BASE_URL}/services/{service_id}/env-vars",
                headers=HEADERS,
                json=[item]
            )
            if resp2.status_code in (200, 201):
                print(f"  Set {item['key']}")
            else:
                print(f"  Failed to set {item['key']}: {resp2.status_code}")

def trigger_deploy(service_id):
    resp = requests.post(f"{BASE_URL}/services/{service_id}/deploys", headers=HEADERS, json={})
    if resp.status_code in (200, 201):
        print("  Deploy triggered!")
    else:
        print(f"  Deploy trigger: {resp.status_code} {resp.text}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 deploy_render.py <github_repo_url>")
        print("Example: python3 deploy_render.py https://github.com/user/binance-claw-quiz")
        sys.exit(1)

    repo_url = sys.argv[1]
    print(f"\nDeploying Binance Claw Quiz from: {repo_url}")
    print("=" * 60)

    # Step 1: Create Backend Service
    print("\n[1/4] Creating Backend API service...")
    backend = create_service({
        "autoDeploy": "yes",
        "branch": "main",
        "name": "binance-claw-quiz-api",
        "ownerId": OWNER_ID,
        "repo": repo_url,
        "rootDir": "backend",
        "serviceDetails": {
            "envSpecificDetails": {
                "buildCommand": "pip install -r requirements.txt",
                "startCommand": "uvicorn server:app --host 0.0.0.0 --port $PORT"
            },
            "plan": "free",
            "region": "oregon",
            "runtime": "python"
        },
        "type": "web_service"
    })

    if not backend:
        print("Backend creation failed!")
        sys.exit(1)

    backend_id = backend["id"]
    backend_url = backend.get("serviceDetails", {}).get("url", "")
    print(f"  Backend ID: {backend_id}")
    print(f"  Backend URL: {backend_url}")

    # Step 2: Set Backend Env Vars
    print("\n[2/4] Setting backend environment variables...")

    mongo_url = input("\nEnter your MongoDB Atlas connection string (or press Enter to skip): ").strip()
    if not mongo_url:
        mongo_url = "mongodb+srv://user:pass@cluster.mongodb.net/binance_claw_quiz"
        print("  WARNING: Using placeholder MongoDB URL. Update later in Render dashboard!")

    set_env_vars(backend_id, [
        {"key": "MONGO_URL", "value": mongo_url},
        {"key": "DB_NAME", "value": "binance_claw_quiz"},
        {"key": "EMERGENT_LLM_KEY", "value": "sk-emergent-5EbB694792770A98c5"},
        {"key": "TELEGRAM_BOT_TOKEN", "value": "8734566460:AAF2SggqHU1gXMLVnzU7e_UNp4HBoCwS5lg"},
        {"key": "CORS_ORIGINS", "value": "*"},
        {"key": "PYTHON_VERSION", "value": "3.11.0"},
    ])

    # Wait for backend URL
    print("\n  Waiting for backend URL...")
    for _ in range(10):
        time.sleep(3)
        resp = requests.get(f"{BASE_URL}/services/{backend_id}", headers=HEADERS)
        if resp.status_code == 200:
            svc = resp.json()
            url = svc.get("serviceDetails", {}).get("url", "")
            if url:
                backend_url = url
                break

    print(f"  Backend URL: {backend_url}")

    # Step 3: Create Frontend Static Site
    print("\n[3/4] Creating Frontend static site...")
    frontend = create_service({
        "autoDeploy": "yes",
        "branch": "main",
        "name": "binance-claw-quiz-app",
        "ownerId": OWNER_ID,
        "repo": repo_url,
        "rootDir": "frontend",
        "serviceDetails": {
            "envSpecificDetails": {
                "buildCommand": "yarn install && yarn build",
                "publishPath": "build"
            },
            "plan": "free",
            "region": "oregon",
            "pullRequestPreviewsEnabled": "no"
        },
        "type": "static_site"
    })

    if not frontend:
        print("Frontend creation failed!")
        sys.exit(1)

    frontend_id = frontend["id"]
    frontend_url = frontend.get("serviceDetails", {}).get("url", "")
    print(f"  Frontend ID: {frontend_id}")
    print(f"  Frontend URL: {frontend_url}")

    # Step 4: Set Frontend + Backend FRONTEND_URL env vars
    print("\n[4/4] Setting frontend environment variables...")
    set_env_vars(frontend_id, [
        {"key": "REACT_APP_BACKEND_URL", "value": backend_url},
    ])

    # Update backend FRONTEND_URL
    if frontend_url:
        set_env_vars(backend_id, [
            {"key": "FRONTEND_URL", "value": frontend_url},
        ])

    print("\n" + "=" * 60)
    print("DEPLOYMENT INITIATED!")
    print(f"  Backend:  {backend_url}")
    print(f"  Frontend: {frontend_url}")
    print("\nNOTE: First deploy takes 5-10 minutes. Check Render dashboard for status.")
    print("You'll need to update FRONTEND_URL on the backend once the frontend URL is confirmed.")
    print("Also update the Telegram bot's web app URL to the frontend URL.")


if __name__ == "__main__":
    main()
