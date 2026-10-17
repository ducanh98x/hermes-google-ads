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
        self.env_path = env_path
        self._env = self._load_env()
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0.0

    @property
    def env(self) -> Dict[str, str]:
        if not hasattr(self, "_env") or not self._env:
            self._env = self._load_env()
        return self._env

    def reload_env(self) -> Dict[str, str]:
        self._env = self._load_env()
        return self._env

    def get_login_customer_id(self) -> str:
        val = (self.env.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID") or "").replace("-", "").strip()
        if not val:
            self.reload_env()
            val = (self.env.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID") or "").replace("-", "").strip()
        return val

    def _find_env_candidates(self) -> List[str]:
        candidates = []
        if self.env_path:
            candidates.append(self.env_path)

        # 1. Active profile from environment
        profile = (
            os.environ.get("HERMES_PROFILE")
            or os.environ.get("HERMES_SESSION_PROFILE")
        )
        if profile:
            candidates.append(os.path.expanduser(f"~/.hermes/profiles/{profile}/.env"))

        # 2. Check current working directory if inside ~/.hermes/profiles/<name>/...
        cwd = os.path.abspath(os.getcwd())
        profiles_marker = "/.hermes/profiles/"
        if profiles_marker in cwd:
            parts = cwd.split(profiles_marker)[1].split("/")
            if parts and parts[0]:
                p_name = parts[0]
                candidates.append(os.path.expanduser(f"~/.hermes/profiles/{p_name}/.env"))

        # 3. Check CWD and parent directory .env
        candidates.append(os.path.join(cwd, ".env"))
        candidates.append(os.path.join(os.path.dirname(cwd), ".env"))

        # 4. Global Hermes env
        candidates.append(os.path.expanduser("~/.hermes/.env"))

        # Deduplicate preserving order
        seen = set()
        existing = []
        for c in candidates:
            c_norm = os.path.normpath(c)
            if c_norm not in seen and os.path.isfile(c_norm):
                seen.add(c_norm)
                existing.append(c_norm)
        return existing

    def _load_env(self) -> Dict[str, str]:
        env_vars = {}
        for path in reversed(self._find_env_candidates()):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            env_vars[k.strip()] = v.strip().strip("'\"")
            except Exception:
                pass

        # Environment variables take highest precedence
        for key in [
            "GOOGLE_ADS_CLIENT_ID",
            "GOOGLE_ADS_CLIENT_SECRET",
            "GOOGLE_ADS_REFRESH_TOKEN",
            "GOOGLE_ADS_LOGIN_CUSTOMER_ID",
            "GOOGLE_ADS_DEVELOPER_TOKEN",
        ]:
            if os.environ.get(key):
                env_vars[key] = os.environ[key]
        return env_vars

    def is_configured(self) -> bool:
        return bool(
            self.env.get("GOOGLE_ADS_CLIENT_ID")
            and self.env.get("GOOGLE_ADS_CLIENT_SECRET")
            and self.env.get("GOOGLE_ADS_REFRESH_TOKEN")
            and self.env.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID")
        )

    def get_access_token(self) -> str:
        now = time.time()
        if self._access_token and now < self._token_expiry - 60:
            return self._access_token

        client_id = self.env.get("GOOGLE_ADS_CLIENT_ID")
        client_secret = self.env.get("GOOGLE_ADS_CLIENT_SECRET")
        refresh_token = self.env.get("GOOGLE_ADS_REFRESH_TOKEN")

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
        dev_token = self.env.get("GOOGLE_ADS_DEVELOPER_TOKEN")
        if dev_token:
            headers["developer-token"] = dev_token

        mcc_id = self.get_login_customer_id()
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
