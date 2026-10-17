"""Hermes Plugin for Google Ads API v22."""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional
from google_ads_client import GoogleAdsClient

_client = GoogleAdsClient()

def _check() -> bool:
    return _client.is_configured()

def gads_list_accounts(status_filter: str = "ENABLED") -> Dict[str, Any]:
    """List all accounts managed under the MCC."""
    mcc_id = _client._env.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").replace("-", "")
    query = """
    SELECT
        customer_client.client_customer,
        customer_client.level,
        customer_client.descriptive_name,
        customer_client.currency_code,
        customer_client.time_zone,
        customer_client.status
    FROM customer_client
    WHERE customer_client.level <= 1
    """
    rows = _client.search_stream(mcc_id, query)
    accounts = []
    status_filter_up = (status_filter or "ALL").upper()

    for r in rows:
        cc = r.get("customerClient", {})
        c_status = cc.get("status", "UNKNOWN")
        if status_filter_up != "ALL" and c_status != status_filter_up:
            continue
        cid_res = cc.get("clientCustomer", "")
        cid = cid_res.replace("customers/", "") if "customers/" in cid_res else cid_res
        accounts.append({
            "customer_id": cid,
            "name": cc.get("descriptiveName", "Unnamed"),
            "currency": cc.get("currencyCode", "USD"),
            "timezone": cc.get("timeZone", "America/New_York"),
            "status": c_status,
            "level": cc.get("level", 1)
        })
    return {"total": len(accounts), "accounts": accounts}

def gads_query(customer_id: str, query: str) -> Dict[str, Any]:
    """Execute arbitrary GAQL query."""
    if not customer_id:
        customer_id = _client._env.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "")
    rows = _client.search_stream(customer_id, query)
    return {"customer_id": customer_id, "row_count": len(rows), "results": rows}

def gads_campaign_performance(customer_id: str, date_range: str = "LAST_30_DAYS", status_filter: str = "ALL") -> Dict[str, Any]:
    """Summarize campaign metrics for an account."""
    clean_cid = customer_id.replace("-", "")
    valid_ranges = ["TODAY", "YESTERDAY", "LAST_7_DAYS", "LAST_14_DAYS", "LAST_30_DAYS", "THIS_MONTH", "LAST_MONTH"]
    date_clause = date_range if date_range in valid_ranges else "LAST_30_DAYS"

    query = f"""
    SELECT
        campaign.id,
        campaign.name,
        campaign.status,
        campaign.advertising_channel_type,
        campaign.bidding_strategy_type,
        metrics.cost_micros,
        metrics.impressions,
        metrics.clicks,
        metrics.ctr,
        metrics.average_cpc,
        metrics.conversions,
        metrics.conversions_value,
        metrics.cost_per_conversion
    FROM campaign
    WHERE segments.date DURING {date_clause}
    """
    rows = _client.search_stream(clean_cid, query)
    campaigns = []
    status_filter_up = (status_filter or "ALL").upper()

    total_spend = 0.0
    total_conv_value = 0.0
    total_conversions = 0.0

    for r in rows:
        c = r.get("campaign", {})
        m = r.get("metrics", {})
        c_status = c.get("status", "UNKNOWN")
        if status_filter_up != "ALL" and c_status != status_filter_up:
            continue

        spend = float(m.get("costMicros") or 0) / 1_000_000
        conv_val = float(m.get("conversionsValue") or 0)
        convs = float(m.get("conversions") or 0)
        roas = (conv_val / spend) if spend > 0 else 0.0
        cpa = float(m.get("costPerConversion") or 0) / 1_000_000 if convs > 0 else 0.0

        total_spend += spend
        total_conv_value += conv_val
        total_conversions += convs

        campaigns.append({
            "id": c.get("id"),
            "name": c.get("name"),
            "status": c_status,
            "type": c.get("advertisingChannelType"),
            "spend": round(spend, 2),
            "impressions": int(m.get("impressions") or 0),
            "clicks": int(m.get("clicks") or 0),
            "ctr": round(float(m.get("ctr") or 0) * 100, 2),
            "avg_cpc": round(float(m.get("averageCpc") or 0) / 1_000_000, 2),
            "conversions": round(convs, 1),
            "conversion_value": round(conv_val, 2),
            "roas": round(roas, 2),
            "cpa": round(cpa, 2)
        })

    overall_roas = (total_conv_value / total_spend) if total_spend > 0 else 0.0
    return {
        "customer_id": clean_cid,
        "date_range": date_clause,
        "summary": {
            "total_spend": round(total_spend, 2),
            "total_revenue": round(total_conv_value, 2),
            "total_conversions": round(total_conversions, 1),
            "blended_roas": round(overall_roas, 2)
        },
        "campaigns": campaigns
    }

def gads_search_terms(customer_id: str, campaign_id: Optional[str] = None, date_range: str = "LAST_30_DAYS", limit: int = 50) -> Dict[str, Any]:
    """Retrieve actual search query terms from shoppers."""
    clean_cid = customer_id.replace("-", "")
    valid_ranges = ["TODAY", "YESTERDAY", "LAST_7_DAYS", "LAST_14_DAYS", "LAST_30_DAYS", "THIS_MONTH", "LAST_MONTH"]
    date_clause = date_range if date_range in valid_ranges else "LAST_30_DAYS"

    where_clauses = [f"segments.date DURING {date_clause}"]
    if campaign_id:
        clean_camp = str(campaign_id).strip()
        where_clauses.append(f"campaign.id = {clean_camp}")

    where_str = " AND ".join(where_clauses)
    query = f"""
    SELECT
        search_term_view.search_term,
        search_term_view.status,
        campaign.name,
        metrics.impressions,
        metrics.clicks,
        metrics.cost_micros,
        metrics.conversions,
        metrics.conversions_value
    FROM search_term_view
    WHERE {where_str}
    ORDER BY metrics.cost_micros DESC
    LIMIT {min(int(limit or 50), 200)}
    """
    rows = _client.search_stream(clean_cid, query)
    terms = []
    for r in rows:
        st = r.get("searchTermView", {})
        m = r.get("metrics", {})
        spend = float(m.get("costMicros") or 0) / 1_000_000
        val = float(m.get("conversionsValue") or 0)
        terms.append({
            "term": st.get("searchTerm"),
            "status": st.get("status"),
            "campaign": r.get("campaign", {}).get("name"),
            "spend": round(spend, 2),
            "clicks": int(m.get("clicks") or 0),
            "conversions": float(m.get("conversions") or 0),
            "conv_value": round(val, 2),
            "roas": round((val / spend), 2) if spend > 0 else 0.0
        })
    return {"customer_id": clean_cid, "total_terms": len(terms), "search_terms": terms}

def gads_draft_proposal(customer_id: str, action_type: str, title: str, details: Dict[str, Any]) -> Dict[str, Any]:
    """Draft a campaign action to outputs directory for Sếp approval."""
    clean_cid = customer_id.replace("-", "")
    ts = time.strftime("%Y%m%d_%H%M%S")
    proposal_id = f"gads_prop_{ts}"
    out_dir = "/root/.hermes/profiles/gogo/workspace/outputs"
    os.makedirs(out_dir, exist_ok=True)
    file_path = os.path.join(out_dir, f"{proposal_id}.json")

    proposal_data = {
        "proposal_id": proposal_id,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "customer_id": clean_cid,
        "action_type": action_type,
        "title": title,
        "status": "PENDING_APPROVAL",
        "details": details
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(proposal_data, f, indent=2, ensure_ascii=False)

    return {
        "status": "DRAFTED_SUCCESSFULLY",
        "proposal_id": proposal_id,
        "file_path": file_path,
        "message": f"Dự thảo '{title}' đã được tạo và lưu tại outputs. Cần Sếp duyệt trước khi gọi gads_mutate để thực thi."
    }

def gads_mutate(customer_id: str, operation: str, params: Dict[str, Any], approved: bool, approval_note: str) -> Dict[str, Any]:
    """Execute an approved Google Ads mutation. Strictly blocked if not approved."""
    clean_cid = customer_id.replace("-", "")
    if not approved:
        return {
            "status": "BLOCKED",
            "error": "HUMAN_APPROVAL_REQUIRED",
            "message": "Hành động này bị chặn vì chưa có phê duyệt chính thức từ Sếp. Hãy tạo dự thảo (gads_draft_proposal) và xin phép Sếp trước khi thực thi."
        }
    if not approval_note or len(approval_note.strip()) < 5:
        return {
            "status": "BLOCKED",
            "error": "INVALID_APPROVAL_NOTE",
            "message": "Phải cung cấp ghi chú xác nhận phê duyệt cụ thể từ Sếp (approval_note)."
        }

    # Dispatch supported operations
    if operation == "update_campaign_status":
        camp_id = str(params.get("campaign_id", "")).strip()
        new_status = str(params.get("status", "PAUSED")).upper()
        if new_status not in ["ENABLED", "PAUSED"]:
            return {"error": "Invalid status. Must be ENABLED or PAUSED."}
        
        resource_name = f"customers/{clean_cid}/campaigns/{camp_id}"
        op = {
            "update": {
                "resourceName": resource_name,
                "status": new_status
            },
            "updateMask": "status"
        }
        res = _client.mutate(clean_cid, "campaigns", [op])
        return {"status": "SUCCESS", "operation": operation, "result": res}

    elif operation == "add_campaign_negative_keywords":
        camp_id = str(params.get("campaign_id", "")).strip()
        keywords = params.get("keywords", [])
        if not keywords:
            return {"error": "No keywords provided."}
        
        ops = []
        for kw in keywords:
            text = kw.get("text") if isinstance(kw, dict) else str(kw)
            match_type = kw.get("match_type", "EXACT") if isinstance(kw, dict) else "EXACT"
            ops.append({
                "create": {
                    "campaign": f"customers/{clean_cid}/campaigns/{camp_id}",
                    "criterion": {
                        "keyword": {
                            "text": text,
                            "matchType": match_type.upper()
                        }
                    },
                    "negative": True
                }
            })
        res = _client.mutate(clean_cid, "campaignCriteria", ops)
        return {"status": "SUCCESS", "operation": operation, "added_count": len(ops), "result": res}

    else:
        return {
            "status": "UNSUPPORTED_OPERATION",
            "message": f"Operation '{operation}' chưa được hỗ trợ hoặc cần bổ sung logic."
        }

SCHEMAS = {
    "gads_list_accounts": {
        "name": "gads_list_accounts",
        "description": "List all accessible Google Ads accounts under the MCC with ID, descriptive name, currency, timezone, and status.",
        "parameters": {
            "type": "object",
            "properties": {
                "status_filter": {
                    "type": "string",
                    "enum": ["ENABLED", "CANCELED", "ALL"],
                    "description": "Filter by account status (default: ENABLED)"
                }
            }
        }
    },
    "gads_query": {
        "name": "gads_query",
        "description": "Execute a raw Google Ads Query Language (GAQL) query on a specific customer ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "10-digit customer account ID (no dashes). Defaults to MCC if omitted."
                },
                "query": {
                    "type": "string",
                    "description": "GAQL query string (e.g. SELECT campaign.name, metrics.cost_micros FROM campaign WHERE segments.date DURING LAST_7_DAYS)"
                }
            },
            "required": ["customer_id", "query"]
        }
    },
    "gads_campaign_performance": {
        "name": "gads_campaign_performance",
        "description": "Retrieve campaign performance summary (spend, conversions, revenue, ROAS, CPA, CTR) for a customer account.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "10-digit Google Ads customer ID."
                },
                "date_range": {
                    "type": "string",
                    "enum": ["TODAY", "YESTERDAY", "LAST_7_DAYS", "LAST_14_DAYS", "LAST_30_DAYS", "THIS_MONTH", "LAST_MONTH"],
                    "description": "Reporting date window (default: LAST_30_DAYS)"
                },
                "status_filter": {
                    "type": "string",
                    "enum": ["ENABLED", "PAUSED", "ALL"],
                    "description": "Filter by campaign status (default: ALL)"
                }
            },
            "required": ["customer_id"]
        }
    },
    "gads_search_terms": {
        "name": "gads_search_terms",
        "description": "Analyze actual search queries entered by shoppers for an account or specific campaign.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "10-digit Google Ads customer ID."
                },
                "campaign_id": {
                    "type": "string",
                    "description": "Optional campaign ID to filter queries for."
                },
                "date_range": {
                    "type": "string",
                    "enum": ["TODAY", "YESTERDAY", "LAST_7_DAYS", "LAST_14_DAYS", "LAST_30_DAYS", "THIS_MONTH", "LAST_MONTH"],
                    "description": "Date window (default: LAST_30_DAYS)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum search queries to return (default: 50, max: 200)"
                }
            },
            "required": ["customer_id"]
        }
    },
    "gads_draft_proposal": {
        "name": "gads_draft_proposal",
        "description": "Draft a proposed campaign action (new camp, budget change, tROAS, negative list) to outputs directory for Sếp approval.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Target Google Ads customer ID."
                },
                "action_type": {
                    "type": "string",
                    "description": "Type of action (e.g. create_campaign, update_budget, add_negative_keywords)"
                },
                "title": {
                    "type": "string",
                    "description": "Short title describing the proposed optimization."
                },
                "details": {
                    "type": "object",
                    "description": "Structured parameters, keywords, ad copy, and rationale."
                }
            },
            "required": ["customer_id", "action_type", "title", "details"]
        }
    },
    "gads_mutate": {
        "name": "gads_mutate",
        "description": "Execute a live change on Google Ads. STRICT REQUIREMENT: Must have explicit approval from Sếp (approved=True and approval_note).",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "10-digit Google Ads customer ID."
                },
                "operation": {
                    "type": "string",
                    "enum": ["update_campaign_status", "add_campaign_negative_keywords"],
                    "description": "Mutation operation to perform."
                },
                "params": {
                    "type": "object",
                    "description": "Operation arguments (e.g. campaign_id, status, keywords)."
                },
                "approved": {
                    "type": "boolean",
                    "description": "MUST be True. Blocks execution if False."
                },
                "approval_note": {
                    "type": "string",
                    "description": "Explicit confirmation note that Sếp approved this change."
                }
            },
            "required": ["customer_id", "operation", "params", "approved", "approval_note"]
        }
    }
}

def register(ctx: Any) -> None:
    """Hermes plugin entrypoint."""
    handlers = {
        "gads_list_accounts": lambda args, **_: json.dumps(gads_list_accounts(args.get("status_filter", "ENABLED")), default=str),
        "gads_query": lambda args, **_: json.dumps(gads_query(args["customer_id"], args["query"]), default=str),
        "gads_campaign_performance": lambda args, **_: json.dumps(gads_campaign_performance(args["customer_id"], args.get("date_range", "LAST_30_DAYS"), args.get("status_filter", "ALL")), default=str),
        "gads_search_terms": lambda args, **_: json.dumps(gads_search_terms(args["customer_id"], args.get("campaign_id"), args.get("date_range", "LAST_30_DAYS"), args.get("limit", 50)), default=str),
        "gads_draft_proposal": lambda args, **_: json.dumps(gads_draft_proposal(args["customer_id"], args["action_type"], args["title"], args["details"]), default=str),
        "gads_mutate": lambda args, **_: json.dumps(gads_mutate(args["customer_id"], args["operation"], args["params"], args.get("approved", False), args.get("approval_note", "")), default=str),
    }
    emojis = {
        "gads_list_accounts": "🏢",
        "gads_query": "🔍",
        "gads_campaign_performance": "📊",
        "gads_search_terms": "🎯",
        "gads_draft_proposal": "📝",
        "gads_mutate": "⚡",
    }
    for name, schema in SCHEMAS.items():
        ctx.register_tool(
            name=name,
            toolset="google_ads",
            schema=schema,
            handler=handlers[name],
            check_fn=_check,
            description=schema["description"],
            emoji=emojis.get(name, "📈"),
        )
