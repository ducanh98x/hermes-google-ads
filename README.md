# Hermes Google Ads Plugin

A lightweight, zero-heavy-dependency Google Ads API plugin for Hermes Agent. Built entirely on standard Python libraries (`urllib`, `json`), communicating directly with **Google Ads API v22** via REST transcoding.

Designed specifically for autonomous e-commerce marketing agents and specialists operating within a multi-agent matrix organization.

---

## Key Features

1. **Native REST API v22 Integration:**
   - Communicates with Google Ads REST endpoints directly without bulky gRPC client libraries (`google-ads` pip package).
   - Fully resilient to the **September 9, 2026 Developer Token sunset**: supports access levels mapped directly to Google Cloud Projects while optionally maintaining developer token headers.
2. **Multi-Account MCC Discovery:**
   - Easily manages multiple client stores under a single Manager Account (MCC).
   - Auto-discovers child customer IDs, currencies, timezones, and operational statuses.
3. **High-Performance GAQL Analytics:**
   - Runs arbitrary Google Ads Query Language (`GAQL`) queries over HTTP streaming (`searchStream`).
   - Built-in performance reporting for Campaigns (Shopping, Performance Max, Search, Demand Gen) and Search Term Views.
4. **Human-in-the-Loop Safe Mutation (Approval Gate):**
   - **Lớp an toàn 1 (Draft Mode):** Campaigns and structural changes are first drafted as structured proposals in `workspace/outputs/`.
   - **Lớp an toàn 2 (Approval Enforcement):** Live mutations via `gads_mutate` strictly require explicit authorization parameters (`approved=True` and `approval_note`).
   - **Lớp an toàn 3 (Safety Default):** New campaigns are always instantiated with status `PAUSED`.

---

## Tool Catalog

| Tool | Emojis | Description | Parameters |
|---|---|---|---|
| `gads_list_accounts` | 🏢 | Lists all accessible customer accounts under the MCC. | `status_filter` (`ENABLED`, `CANCELED`, `ALL`) |
| `gads_query` | 🔍 | Executes raw GAQL queries against any customer account. | `customer_id`, `query` |
| `gads_campaign_performance` | 📊 | Pulls aggregated metrics (Spend, Revenue, ROAS, CPA, CVR, CTR). | `customer_id`, `date_range`, `status_filter` |
| `gads_search_terms` | 🎯 | Analyzes search queries entered by shoppers for intent or negative filtering. | `customer_id`, `campaign_id`, `date_range`, `limit` |
| `gads_draft_proposal` | 📝 | Creates structured JSON/Markdown action proposals in outputs directory. | `customer_id`, `action_type`, `title`, `details` |
| `gads_mutate` | ⚡ | Executes approved mutations (status change, negative keywords). Enforces approval. | `customer_id`, `operation`, `params`, `approved`, `approval_note` |

---

## Configuration

Credentials can be provided via environment variables or profile-scoped `.env`:

```bash
# 1. Google Cloud OAuth 2.0 Credentials (console.cloud.google.com -> Credentials)
GOOGLE_ADS_CLIENT_ID="your_client_id.apps.googleusercontent.com"
GOOGLE_ADS_CLIENT_SECRET="your_client_secret"

# 2. OAuth Refresh Token (long-lived token with scope https://www.googleapis.com/auth/adwords)
GOOGLE_ADS_REFRESH_TOKEN="your_refresh_token"

# 3. Manager Account / MCC ID (10 digits without dashes)
GOOGLE_ADS_LOGIN_CUSTOMER_ID="1234567890"

# 4. Optional Developer Token (supported for legacy/transition compatibility)
GOOGLE_ADS_DEVELOPER_TOKEN="your_dev_token"
```

---

## Integration with Hermes Agent

Enable the plugin in your profile's `config.yaml`:

```yaml
plugins:
  enabled:
    - google-ads

platform_toolsets:
  cli:
    - google_ads
  telegram:
    - google_ads
```

---

## Security & Privacy

- All secret tokens (`refresh_token`, `client_secret`) are resolved strictly server-side and never leaked in LLM conversational outputs.
- Read-only queries can run autonomously; any state-changing operations require explicit human confirmation.

## License

MIT License. Copyright (c) 2026 DU COMMERCE LLC / Hermes Agent.
