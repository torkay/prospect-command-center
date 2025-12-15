"""
Prospect Command Center - Marketing prospect discovery tool.

Find businesses that need marketing help, score them for fit and opportunity,
and manage your outreach pipeline.

CLI Usage:
    prospect search "buyer's agent" "Brisbane" --limit 20
    prospect search "plumber" "Sydney" -f json -q | jq '.'
    prospect web  # Start web interface

Library Usage:
    from prospect import search_prospects

    results = search_prospects(
        business_type="buyer's agent",
        location="Brisbane, QLD",
        limit=20,
        skip_enrichment=False
    )

    for r in results:
        print(f"{r.name}: {r.priority_score}")
"""

__version__ = "1.0.1"
__author__ = "SortedSystems"

# Semantic versioning
# MAJOR.MINOR.PATCH
# - MAJOR: Breaking changes
# - MINOR: New features (backward compatible)
# - PATCH: Bug fixes (backward compatible)
VERSION_INFO = {
    "major": 1,
    "minor": 0,
    "patch": 1,
    "release": "stable",  # stable, beta, alpha
}


def get_version() -> str:
    """Get full version string."""
    version = f"{VERSION_INFO['major']}.{VERSION_INFO['minor']}.{VERSION_INFO['patch']}"
    if VERSION_INFO["release"] != "stable":
        version += f"-{VERSION_INFO['release']}"
    return version


from prospect.api import search_prospects, ProspectResult

__all__ = ["search_prospects", "ProspectResult", "__version__", "get_version", "VERSION_INFO"]
