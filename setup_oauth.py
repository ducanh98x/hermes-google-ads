#!/usr/bin/env python3
"""Interactive OAuth & Environment Setup for Hermes Google Ads Plugin.

Allows any user/organization to configure their own Google Cloud Console
project and obtain credentials for any Hermes profile.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, Optional


def print_banner():
    print("=" * 72)
    print("   HERMES GOOGLE ADS PLUGIN - OAUTH & CREDENTIALS SETUP WIZARD")
    print("=" * 72)
    print("This wizard helps you connect your OWN Google Cloud Project and")
    print("Google Ads MCC to any Hermes profile with zero hardcoded dependencies.\n")


def print_gcp_guide():
    print("-" * 72)
    print("📋 PREREQUISITE: Create Your Own Google Cloud Project (takes ~2 mins)")
    print("-" * 72)
    print("1. Go to Google Cloud Console: https://console.cloud.google.com")
    print("   -> Create a NEW Project (e.g. 'MyStore Google Ads API')")
    print("2. Enable Google Ads API:")
    print("   -> Go to 'APIs & Services' > 'Library'")
    print("   -> Search 'Google Ads API' and click 'ENABLE'")
    print("3. Configure OAuth Consent Screen:")
    print("   -> Go to 'APIs & Services' > 'OAuth consent screen'")
    print("   -> Choose 'External' > Create")
    print("   -> Set App Name (e.g. 'Hermes Ads Agent') and your email")
    print("   -> In 'Test users', click '+ ADD USERS' and add your Google Ads email")
    print("   -> Save and Continue")
    print("4. Create OAuth Client Credentials:")
    print("   -> Go to 'APIs & Services' > 'Credentials' > '+ CREATE CREDENTIALS'")
    print("   -> Choose 'OAuth client ID'")
    print("   -> Application type: 'Web application' (or 'Desktop app')")
    print("   -> If Web application: add Authorized redirect URI:")
    print("         http://127.0.0.1:8089")
    print("   -> Copy your Client ID and Client Secret")
    print("-" * 72 + "\n")


def resolve_target_env() -> str:
    default_profile = os.environ.get("HERMES_PROFILE") or os.environ.get("HERMES_SESSION_PROFILE") or "gogo"
    default_path = os.path.expanduser(f"~/.hermes/profiles/{default_profile}/.env")
    if not os.path.exists(os.path.dirname(default_path)):
        default_path = os.path.expanduser("~/.hermes/.env")

    print(f"Target Hermes profile or .env file:")
    print(f"Default: {default_path}")
    choice = input("Enter path to .env or profile name [Press Enter for default]: ").strip()
    if not choice:
        return default_path
    if "/" in choice or choice.endswith(".env"):
        return os.path.abspath(os.path.expanduser(choice))
    # It's a profile name
    p_path = os.path.expanduser(f"~/.hermes/profiles/{choice}/.env")
    os.makedirs(os.path.dirname(p_path), exist_ok=True)
    return p_path


def load_env(path: str) -> Dict[str, str]:
    env_vars = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip().strip("'\"")
    return env_vars


def save_env_values(path: str, values: Dict[str, str]):
    existing_lines = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            existing_lines = f.readlines()

    keys_written = set()
    new_lines = []
    for line in existing_lines:
        matched = False
        for k, v in values.items():
            if line.strip().startswith(f"{k}="):
                new_lines.append(f"{k}=\"{v}\"\n")
                keys_written.add(k)
                matched = True
                break
        if not matched:
            new_lines.append(line)

    for k, v in values.items():
        if k not in keys_written:
            new_lines.append(f"{k}=\"{v}\"\n")

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    os.chmod(path, 0o600)
    print(f"✓ Saved credentials securely to {path} (chmod 600)")


def exchange_code(client_id: str, client_secret: str, redirect_uri: str, code: str) -> str:
    token_url = "https://oauth2.googleapis.com/token"
    token_data = urllib.parse.urlencode({
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }).encode("utf-8")

    req = urllib.request.Request(token_url, data=token_data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            refresh_token = data.get("refresh_token")
            if not refresh_token:
                raise RuntimeError(f"No refresh_token returned by Google: {data}")
            return refresh_token
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8")
        raise RuntimeError(f"OAuth HTTP {e.code}: {err}")


def main():
    print_banner()
    print_gcp_guide()

    target_env = resolve_target_env()
    current_env = load_env(target_env)

    # Prompt Client ID
    curr_cid = current_env.get("GOOGLE_ADS_CLIENT_ID", "")
    prompt_cid = f"Enter GOOGLE_ADS_CLIENT_ID [{curr_cid[:15]}...]: " if curr_cid else "Enter GOOGLE_ADS_CLIENT_ID: "
    client_id = input(prompt_cid).strip() or curr_cid

    # Prompt Client Secret
    curr_sec = current_env.get("GOOGLE_ADS_CLIENT_SECRET", "")
    prompt_sec = "Enter GOOGLE_ADS_CLIENT_SECRET [hidden]: " if curr_sec else "Enter GOOGLE_ADS_CLIENT_SECRET: "
    client_secret = input(prompt_sec).strip() or curr_sec

    # Prompt MCC ID
    curr_mcc = current_env.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "")
    prompt_mcc = f"Enter GOOGLE_ADS_LOGIN_CUSTOMER_ID (10 digits) [{curr_mcc}]: " if curr_mcc else "Enter GOOGLE_ADS_LOGIN_CUSTOMER_ID (10 digits): "
    mcc_id = input(prompt_mcc).strip().replace("-", "") or curr_mcc.replace("-", "")

    # Optional Developer Token
    curr_dev = current_env.get("GOOGLE_ADS_DEVELOPER_TOKEN", "")
    prompt_dev = f"Enter GOOGLE_ADS_DEVELOPER_TOKEN (optional) [{curr_dev}]: " if curr_dev else "Enter GOOGLE_ADS_DEVELOPER_TOKEN (optional, press Enter to skip): "
    dev_token = input(prompt_dev).strip() or curr_dev

    if not client_id or not client_secret:
        print("❌ Error: Client ID and Client Secret are mandatory.")
        sys.exit(1)

    port = 8089
    redirect_uri = f"http://127.0.0.1:{port}"

    scope = "https://www.googleapis.com/auth/adwords"
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "access_type": "offline",
        "prompt": "consent"
    }
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)

    print("\n" + "=" * 72)
    print("🔗 STEP 1: Open this link in your browser to authorize access:")
    print("=" * 72)
    print(auth_url)
    print("=" * 72 + "\n")

    auth_code: Optional[str] = None

    class OAuthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal auth_code
            query = urllib.parse.urlparse(self.path).query
            qs = urllib.parse.parse_qs(query)
            if "code" in qs:
                auth_code = qs["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"<h1>Authentication successful! You can close this window.</h1>")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"<h1>No code found in redirect.</h1>")

        def log_message(self, format, *args):
            pass

    server = None
    try:
        server = HTTPServer(("0.0.0.0", port), OAuthHandler)
        server_thread = threading.Thread(target=server.handle_request)
        server_thread.daemon = True
        server_thread.start()
    except Exception:
        pass

    print("👉 STEP 2: After logging in & allowing access:")
    print("   - If running locally, browser will redirect to 127.0.0.1:8089 automatically.")
    print("   - If running on a remote VPS, browser may say 'Unable to connect',")
    print("     simply COPY the full URL from the address bar and PASTE it below.\n")

    user_input = input("Paste redirect URL or code here [or wait for auto-capture]: ").strip()
    if user_input:
        if "code=" in user_input:
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(user_input).query)
            if "code" in qs:
                auth_code = qs["code"][0]
        else:
            auth_code = user_input

    if not auth_code:
        print("❌ Error: No authorization code received.")
        sys.exit(1)

    print("\n⏳ Exchanging authorization code for Refresh Token...")
    try:
        refresh_token = exchange_code(client_id, client_secret, redirect_uri, auth_code)
        print(f"🎉 Success! Refresh token obtained.")
        
        save_env_values(target_env, {
            "GOOGLE_ADS_CLIENT_ID": client_id,
            "GOOGLE_ADS_CLIENT_SECRET": client_secret,
            "GOOGLE_ADS_REFRESH_TOKEN": refresh_token,
            "GOOGLE_ADS_LOGIN_CUSTOMER_ID": mcc_id,
            "GOOGLE_ADS_DEVELOPER_TOKEN": dev_token
        })

        print("\n🔍 Verifying live connection to Google Ads API...")
        try:
            from google_ads_client import GoogleAdsClient
            client = GoogleAdsClient(env_path=target_env)
            query = "SELECT customer_client.descriptive_name, customer_client.client_customer FROM customer_client WHERE customer_client.level <= 1"
            rows = client.search_stream(mcc_id, query)
            print(f"✓ Connected successfully! Found {len(rows)} account(s) under MCC {mcc_id}:")
            for r in rows[:5]:
                cc = r.get("customerClient", {})
                cid = cc.get("clientCustomer", "").replace("customers/", "")
                name = cc.get("descriptiveName", "Unnamed")
                print(f"   - [{cid}] {name}")
            if len(rows) > 5:
                print(f"   ... and {len(rows) - 5} more.")
            print("\n🚀 SETUP COMPLETE! Plugin is ready to use in profile.")
        except Exception as e:
            print(f"⚠️ Token saved, but API test returned: {e}")
            print("Please check if MCC ID is correct and Google Ads API is enabled in your Google Cloud Project.")

    except Exception as e:
        print(f"❌ Failed to exchange code: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
