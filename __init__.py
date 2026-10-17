"""Hermes Google Ads Plugin."""

from .google_ads_plugin import (
    gads_campaign_performance,
    gads_draft_proposal,
    gads_feed_diagnostics,
    gads_list_accounts,
    gads_mutate,
    gads_product_performance,
    gads_query,
    gads_search_terms,
    register,
)

__all__ = [
    "gads_campaign_performance",
    "gads_draft_proposal",
    "gads_feed_diagnostics",
    "gads_list_accounts",
    "gads_mutate",
    "gads_product_performance",
    "gads_query",
    "gads_search_terms",
    "register",
]
