# Hermes Google Ads Plugin (v1.1.0)

Production-grade Hermes Agent plugin integrating Google Ads API v22 REST. Designed for e-commerce multi-store dropshipping/print-on-demand portfolios operating on US market via MCC (Manager Account).

## 🌟 Key Features

1. **Product & Listing Centric (Shopping & PMax):**
   - Deep visibility into product-level SKU metrics (`shopping_performance_view`).
   - Identifies high-ROAS winners, zero-conversion budget burners, and bleeders (ROAS < 1.6).
   - Category breakdowns, budget hog detection (SKUs eating >= 10% spend), and 70-character title audit.
2. **REST API v22 (Stdlib Only):**
   - Pure Python standard library (`urllib.request`, `json`). Zero heavy external dependencies (`google-ads` python library / gRPC not required).
   - Resilient against Google's Developer Token sunset policy (enforced Sept 2026).
3. **Safety First Architecture:**
   - **Read & Analyze:** Full access to metrics, campaigns, products, and search terms.
   - **Draft Proposals:** Generates structured proposals to `workspace/outputs/`.
   - **Human-in-the-Loop Gate:** Mutations strictly require `approved=True` and explicit `approval_note`. New campaigns default to `PAUSED`.

---

## 🛠️ Tool Catalog (8 Tools)

| Tool Name | Emoji | Purpose |
|---|---|---|
| `gads_list_accounts` | 🏢 | List all client accounts under MCC with ID, descriptive name, currency, timezone, and status. |
| `gads_query` | 🔍 | Run arbitrary GAQL queries for ad-hoc analysis. |
| `gads_campaign_performance` | 📊 | Aggregated campaign metrics (Spend, Revenue, Blended ROAS, CPA, CVR, CTR). |
| `gads_product_performance` | 🏷️ | **[NEW]** Deep product SKU performance from Shopping Ads & PMax (`shopping_performance_view`). Filter by SKU, campaign, min spend, or status (`WINNER`, `PROFITABLE`, `BLEEDING`, `ZERO_CONVERSION`). |
| `gads_feed_diagnostics` | 🩺 | **[NEW]** Product feed diagnostics: category spend breakdown, budget hogs (SKUs taking >= 10% spend), and title length audit. |
| `gads_search_terms` | 🎯 | Search query analysis from shoppers to find converting intent and negative keywords. |
| `gads_draft_proposal` | 📝 | Create structured optimization proposal in `outputs/` for owner review. |
| `gads_mutate` | ⚡ | Execute mutations (pause/enable camp, add negative keywords). Requires approval. |

---

## ⚙️ Configuration (.env)

Add the following to `/root/.hermes/profiles/<profile>/.env`:

```bash
GOOGLE_ADS_CLIENT_ID="<your-oauth-client-id>.apps.googleusercontent.com"
GOOGLE_ADS_CLIENT_SECRET="<your-oauth-client-secret>"
GOOGLE_ADS_REFRESH_TOKEN="<your-oauth-refresh-token>"
GOOGLE_ADS_LOGIN_CUSTOMER_ID="<10-digit-mcc-id>"
GOOGLE_ADS_DEVELOPER_TOKEN="<token-if-applicable>"
```

Ensure permissions: `chmod 600 /root/.hermes/profiles/<profile>/.env`

---

## 🚀 Installation in Hermes

1. Clone or place this directory under `/root/.hermes/plugins/google-ads`.
2. Enable globally or per-profile:
   ```bash
   hermes plugins enable google-ads
   ```
3. Add `google_ads` to `platform_toolsets.cli` and `platform_toolsets.telegram` in `config.yaml`.

---

## 📄 License
MIT © 2026 David (ducanh98x)
