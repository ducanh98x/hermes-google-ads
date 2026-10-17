# Hermes Google Ads Plugin (v1.1.0)

Production-grade Hermes Agent plugin integrating Google Ads API v22 REST. Designed for e-commerce multi-store dropshipping/print-on-demand portfolios operating on US market via MCC (Manager Account).

Zero hardcoded dependencies: Works across any Hermes profile, any user workspace, and connects to **any custom Google Cloud Console project**.

---

## 🌟 Key Features

1. **Independent Google Cloud Project Setup:**
   - Any team or user can create their own Google Cloud Project.
   - Built-in interactive CLI setup wizard (`setup_oauth.py`) guides the OAuth authorization process and saves credentials directly into the target profile's `.env`.
2. **Product & Listing Centric (Shopping & PMax):**
   - Deep visibility into product-level SKU metrics (`shopping_performance_view`).
   - Identifies high-ROAS winners, zero-conversion budget burners, and bleeders (ROAS < 1.6).
   - Category breakdowns, budget hog detection (SKUs eating >= 10% spend), and 70-character title audit.
3. **Pure REST API v22 (Stdlib Only):**
   - Pure Python standard library (`urllib.request`, `json`). Zero heavy external dependencies (`google-ads` python library / gRPC not required).
   - Fully resilient against Google's Developer Token sunset policy (enforced Sept 2026).
4. **Safety First Architecture:**
   - **Read & Analyze:** Full access to metrics, campaigns, products, and search terms.
   - **Draft Proposals:** Generates structured proposals dynamically to `workspace/outputs/`.
   - **Human-in-the-Loop Gate:** Mutations strictly require `approved=True` and explicit `approval_note`. New campaigns default to `PAUSED`.

---

## 🛠️ Tool Catalog (8 Tools)

| Tool Name | Emoji | Purpose |
|---|---|---|
| `gads_list_accounts` | 🏢 | List all client accounts under MCC with ID, descriptive name, currency, timezone, and status. |
| `gads_query` | 🔍 | Run arbitrary GAQL queries for ad-hoc analysis. |
| `gads_campaign_performance` | 📊 | Aggregated campaign metrics (Spend, Revenue, Blended ROAS, CPA, CVR, CTR). |
| `gads_product_performance` | 🏷️ | Deep product SKU performance from Shopping Ads & PMax (`shopping_performance_view`). Filter by SKU, campaign, min spend, or status (`WINNER`, `PROFITABLE`, `BLEEDING`, `ZERO_CONVERSION`). |
| `gads_feed_diagnostics` | 🩺 | Product feed diagnostics: category spend breakdown, budget hogs (SKUs taking >= 10% spend), and title length audit. |
| `gads_search_terms` | 🎯 | Search query analysis from shoppers to find converting intent and negative keywords. |
| `gads_draft_proposal` | 📝 | Create structured optimization proposal in `outputs/` for owner review. |
| `gads_mutate` | ⚡ | Execute mutations (pause/enable camp, add negative keywords). Strictly requires human approval. |

---

## 🚀 Setup Guide: Connecting Your Own Google Cloud Project

You do NOT need to share or use any centralized Google Cloud project. You can create your own isolated project in 2 minutes:

### Step 1: Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com).
2. Click the project dropdown at the top > **New Project**.
3. Name it anything (e.g. `MyStore - Google Ads API`) and click **Create**.

### Step 2: Enable Google Ads API
1. Navigate to **APIs & Services** > **Library**.
2. Search for `Google Ads API`.
3. Click on it and click **ENABLE**.

### Step 3: Configure OAuth Consent Screen
1. Go to **APIs & Services** > **OAuth consent screen**.
2. Choose **External** > Click **Create**.
3. Fill in:
   - **App name**: (e.g. `Hermes Ads Agent`)
   - **User support email**: your email
   - **Developer contact**: your email
4. Click **Save and Continue** until you reach **Test users**.
5. Click **+ ADD USERS** and enter the Google account email that manages your Google Ads MCC.
6. Click **Save and Continue** > **Back to Dashboard**.

### Step 4: Create OAuth Client Credentials
1. Go to **APIs & Services** > **Credentials**.
2. Click **+ CREATE CREDENTIALS** > **OAuth client ID**.
3. Application type: Select **Web application** (or **Desktop app**).
4. If Web application:
   - Under **Authorized redirect URIs**, click **+ ADD URI**.
   - Enter: `http://127.0.0.1:8089`
5. Click **Create** and copy your **Client ID** and **Client Secret**.

---

### Step 5: Run Setup Wizard (Interactive CLI)

Inside the plugin directory, run:

```bash
python3 setup_oauth.py
```

The wizard will:
1. Ask for your target Hermes profile or `.env` path.
2. Prompt for your **Client ID**, **Client Secret**, and 10-digit **MCC ID**.
3. Open an authorization link for you to log into Google and grant access.
4. Automatically capture the authorization code and exchange it for a **Refresh Token**.
5. Save everything securely to your profile's `.env` with `chmod 600`.
6. Test live connectivity and list your MCC accounts.

---

## ⚙️ Manual Configuration (.env)

If configuring manually without the wizard, add these variables to your profile's `.env` (e.g., `~/.hermes/profiles/<profile>/.env`):

```bash
GOOGLE_ADS_CLIENT_ID="<your-oauth-client-id>.apps.googleusercontent.com"
GOOGLE_ADS_CLIENT_SECRET="<your-oauth-client-secret>"
GOOGLE_ADS_REFRESH_TOKEN="<your-oauth-refresh-token>"
GOOGLE_ADS_LOGIN_CUSTOMER_ID="<10-digit-mcc-id>"
GOOGLE_ADS_DEVELOPER_TOKEN="<optional-developer-token>"
```

Permissions should be restricted: `chmod 600 ~/.hermes/profiles/<profile>/.env`

---

## 📦 Activation in Hermes

1. Enable the plugin globally or per-profile:
   ```bash
   hermes plugins enable google-ads
   ```
2. Verify with Plugin Doctor:
   ```bash
   hermes plugins doctor google-ads
   ```
3. Add `google_ads` to your profile's `platform_toolsets` in `config.yaml`.

---

## 📄 License
MIT © 2026 David (ducanh98x)
