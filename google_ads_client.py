"""Google Ads API v22 REST client for Hermes."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

API_VERSION = "v22"
BASE_URL = f"https://googleads.googleapis.com/{API_VERSION}"
TOKEN_URL = "https://oauth2.googleapis.com/token"

class GoogleAdsClient:
    def __init__(self, env_path: Optional[str] = None):
        self.env_path = env_path or "/root/.hermes/profiles/gogo/.env"
        self._env = self._load_env()
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0.0

    def _load_env(self) -> Dict[str, str]:
        env_vars = {}
        if os.path.exists(self.env_path):
            with open(self.env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        env_vars[k.strip()] = v.strip().strip("'\"")
        # Allow environment variables to override
        for key in ["GOOGLE_ADS_CLIENT_ID", "GOOGLE_ADS_CLIENT_SECRET", "GOOGLE_ADS_REFRESH_TOKEN", "GOOGLE_ADS_LOGIN_CUSTOMER_ID", "GOOGLE_ADS_DEVELOPER_TOKEN"]:
            if key in os.environ:
                env_vars[key] = os.environ[key]
        return env_vars

    def is_configured(self) -> bool:
        self._env = self._load_env()
        return bool(
            self._env.get("GOOGLE_ADS_CLIENT_ID")
            and self._env.get("GOOGLE_ADS_CLIENT_SECRET")
            and self._env.get("GOOGLE_ADS_REFRESH_TOKEN")
            and self._env.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID")
        )

    def get_access_token(self) -> str:
        now = time.time()
        if self._access_token and now < self._token_expiry - 60:
            return self._access_token

        self._env = self._load_env()
        client_id = self._env.get("GOOGLE_ADS_CLIENT_ID")
        client_secret = self._env.get("GOOGLE_ADS_CLIENT_SECRET")
        refresh_token = self._env.get("GOOGLE_ADS_REFRESH_TOKEN")

        if not (client_id and client_secret and refresh_token):
            raise ValueError("Google Ads credentials incomplete in .env (missing client_id, secret, or refresh_token).")

        token_data = urllib.parse.urlencode({
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token"
        }).encode("utf-8")

        req = urllib.request.Request(TOKEN_URL, data=token_data, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                self._access_token = data["access_token"]
                expires_in = data.get("expires_in", 3600)
                self._token_expiry = now + expires_in
                return self._access_token
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8")
            raise RuntimeError(f"Failed to refresh Google OAuth token (HTTP {e.code}): {err_msg}")
        except Exception as e:
            raise RuntimeError(f"Error refreshing Google OAuth token: {e}")

    def _get_headers(self, customer_id: Optional[str] = None) -> Dict[str, str]:
        token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        dev_token = self._env.get("GOOGLE_ADS_DEVELOPER_TOKEN")
        if dev_token:
            headers["developer-token"] = dev_token
        
        mcc_id = (self._env.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID") or "").replace("-", "")
        if mcc_id:
            headers["login-customer-id"] = mcc_id
        return headers

    def search_stream(self, customer_id: str, query: str) -> List[Dict[str, Any]]:
        clean_cid = str(customer_id).replace("-", "").strip()
        url = f"{BASE_URL}/customers/{clean_cid}/googleAds:searchStream"
        headers = self._get_headers(clean_cid)
        payload = json.dumps({"query": query}).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                rows = []
                for batch in data:
                    rows.extend(batch.get("results", []))
                return rows
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8")
            try:
                err_json = json.loads(err_msg)
                details = err_json.get("error", {}).get("message", err_msg)
            except Exception:
                details = err_msg
            raise RuntimeError(f"Google Ads GAQL query error (HTTP {e.code}): {details}")
        except Exception as e:
            raise RuntimeError(f"Google Ads API request failed: {e}")

    def mutate(self, customer_id: str, endpoint: str, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        clean_cid = str(customer_id).replace("-", "").strip()
        url = f"{BASE_URL}/customers/{clean_cid}/{endpoint}:mutate"
        headers = self._get_headers(clean_cid)
        payload = json.dumps({"operations": operations}).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8")
            try:
                err_json = json.loads(err_msg)
                details = err_json.get("error", {}).get("message", err_msg)
            except Exception:
                details = err_msg
            raise RuntimeError(f"Google Ads mutate error (HTTP {e.code}): {details}")
        except Exception as e:
            raise RuntimeError(f"Google Ads mutate failed: {e}")
