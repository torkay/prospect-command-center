"""Search orchestrator for tiered deep searches."""

import logging
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, AsyncGenerator, Any

from prospect.scraper.serpapi import SerpAPIClient
from prospect.scraper.locations import get_nearby_suburbs, expand_query_variations
from prospect.dedup import deduplicate_serp_results
from prospect.models import Prospect, SerpResults, MapsResult
from prospect import _native

logger = logging.getLogger(__name__)


@dataclass
class SearchPlan:
    """Plan for a search with all queries and locations."""
    queries: List[str]
    locations: List[str]
    organic_pages: int
    maps_pages: int
    search_types: List[str]
    max_api_calls: int
    estimated_cost_cents: int

    @property
    def total_api_calls(self) -> int:
        """Calculate total API calls needed (capped by max)."""
        calls = 0
        for query in self.queries:
            for location in self.locations:
                if "organic" in self.search_types:
                    calls += self.organic_pages
                if "maps" in self.search_types:
                    calls += self.maps_pages
                if "local_services" in self.search_types:
                    calls += 1
        return min(calls, self.max_api_calls)


@dataclass
class SearchProgress:
    """Real-time search progress."""
    phase: str  # planning, searching, deduplicating, enriching, scoring, complete
    total_api_calls: int = 0
    completed_api_calls: int = 0
    total_prospects: int = 0
    unique_prospects: int = 0
    current_query: str = ""
    current_location: str = ""
    current_page: int = 0
    errors: List[str] = field(default_factory=list)
    results: List[Any] = field(default_factory=list)


class SearchOrchestrator:
    """
    Orchestrates multi-query, multi-location searches.

    Features:
    - Query expansion (plumber → plumber services, emergency plumber)
    - Location expansion (Brisbane → Brisbane CBD, Fortitude Valley)
    - Pagination (organic pages 1, 2, 3)
    - Result caching (avoid duplicate API calls)
    - Real-time progress updates
    - Cost tracking
    """

    def __init__(
        self,
        serpapi_key: Optional[str] = None,
        cache_ttl_hours: int = 24,
    ):
        self.serpapi_key = serpapi_key
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self._cache: Dict[str, Dict] = {}
        self._client: Optional[SerpAPIClient] = None

    def _get_client(self) -> SerpAPIClient:
        """Get or create SerpAPI client."""
        if self._client is None:
            self._client = SerpAPIClient(api_key=self.serpapi_key)
        return self._client

    def plan_search(
        self,
        business_type: str,
        location: str,
        config: Dict,
    ) -> SearchPlan:
        """
        Create a search plan based on configuration.

        Args:
            business_type: Type of business to search
            location: Base location
            config: SearchConfig dict with depth settings

        Returns:
            SearchPlan with estimated API calls and cost
        """
        # Expand queries
        if config.get("use_query_variations") and config.get("query_variations"):
            queries = expand_query_variations(business_type, config["query_variations"])
        else:
            queries = [business_type]

        # Expand locations
        if config.get("use_location_expansion"):
            locations = get_nearby_suburbs(
                location,
                radius_km=config.get("expansion_radius_km", 10),
                max_results=config.get("max_locations", 5),
            )
        else:
            locations = [location]

        # Determine search types
        search_types = []
        if config.get("search_organic", True):
            search_types.append("organic")
        if config.get("search_maps", True):
            search_types.append("maps")
        if config.get("search_local_services", False):
            search_types.append("local_services")

        return SearchPlan(
            queries=queries,
            locations=locations,
            organic_pages=config.get("organic_pages", 1),
            maps_pages=config.get("maps_pages", 1),
            search_types=search_types,
            max_api_calls=config.get("max_api_calls", 5),
            estimated_cost_cents=config.get("estimated_cost_cents", 5),
        )

    async def execute_search(
        self,
        business_type: str,
        location: str,
        config: Dict,
    ) -> AsyncGenerator[SearchProgress, None]:
        """
        Execute a search with real-time progress updates.

        Yields SearchProgress objects as the search progresses.
        """
        # Create plan
        plan = self.plan_search(business_type, location, config)

        progress = SearchProgress(
            phase="planning",
            total_api_calls=plan.total_api_calls,
        )
        yield progress

        # Track all results
        all_serp_results: List[SerpResults] = []
        all_maps_results: List[MapsResult] = []
        api_calls_made = 0

        progress.phase = "searching"
        client = self._get_client()

        # Execute searches
        for query in plan.queries:
            for loc in plan.locations:
                if api_calls_made >= plan.max_api_calls:
                    break

                progress.current_query = query
                progress.current_location = loc

                # Check cache first
                cache_key = self._cache_key(query, loc)
                cached = self._get_cached(cache_key)

                if cached:
                    all_serp_results.extend(cached.get("serp", []))
                    all_maps_results.extend(cached.get("maps", []))
                    progress.total_prospects = sum(
                        len(sr.ads) + len(sr.maps) + len(sr.organic)
                        for sr in all_serp_results
                    ) + len(all_maps_results)
                    yield progress
                    continue

                cached_serp: List[SerpResults] = []
                cached_maps: List[MapsResult] = []

                # Search organic (includes local pack)
                if "organic" in plan.search_types:
                    for page in range(1, plan.organic_pages + 1):
                        if api_calls_made >= plan.max_api_calls:
                            break

                        progress.current_page = page

                        try:
                            results = client.search_paginated(
                                business_type=query,
                                location=loc,
                                page=page,
                                num_results=10,
                            )
                            all_serp_results.append(results)
                            cached_serp.append(results)
                            api_calls_made += 1
                            progress.completed_api_calls = api_calls_made
                            progress.total_prospects = sum(
                                len(sr.ads) + len(sr.maps) + len(sr.organic)
                                for sr in all_serp_results
                            ) + len(all_maps_results)
                            yield progress

                        except Exception as e:
                            error_msg = f"Organic search error (p{page}): {str(e)}"
                            logger.warning(error_msg)
                            progress.errors.append(error_msg)

                # Search maps
                if "maps" in plan.search_types:
                    for page in range(plan.maps_pages):
                        if api_calls_made >= plan.max_api_calls:
                            break

                        progress.current_page = page + 1

                        try:
                            maps_results = client.search_maps(
                                business_type=query,
                                location=loc,
                                start=page * 20,
                            )
                            all_maps_results.extend(maps_results)
                            cached_maps.extend(maps_results)
                            api_calls_made += 1
                            progress.completed_api_calls = api_calls_made
                            progress.total_prospects = sum(
                                len(sr.ads) + len(sr.maps) + len(sr.organic)
                                for sr in all_serp_results
                            ) + len(all_maps_results)
                            yield progress

                        except Exception as e:
                            error_msg = f"Maps search error: {str(e)}"
                            logger.warning(error_msg)
                            progress.errors.append(error_msg)

                # Search local services
                if "local_services" in plan.search_types:
                    if api_calls_made < plan.max_api_calls:
                        try:
                            local_results = client.search_local_services(
                                business_type=query,
                                location=loc,
                            )
                            # Convert to MapsResult format for consistency
                            for lr in local_results:
                                all_maps_results.append(MapsResult(
                                    position=0,
                                    name=lr.get("name", "Unknown"),
                                    rating=lr.get("rating"),
                                    review_count=lr.get("reviews"),
                                    phone=lr.get("phone"),
                                    website=lr.get("website"),
                                ))
                            api_calls_made += 1
                            progress.completed_api_calls = api_calls_made
                            progress.total_prospects = sum(
                                len(sr.ads) + len(sr.maps) + len(sr.organic)
                                for sr in all_serp_results
                            ) + len(all_maps_results)
                            yield progress

                        except Exception as e:
                            error_msg = f"Local services error: {str(e)}"
                            logger.debug(error_msg)
                            progress.errors.append(error_msg)

                # Cache results for this query/location
                self._set_cached(cache_key, {
                    "serp": cached_serp,
                    "maps": cached_maps,
                })

        # Combine all SERP results
        combined = SerpResults(
            query=business_type,
            location=location,
        )
        for sr in all_serp_results:
            combined.ads.extend(sr.ads)
            combined.maps.extend(sr.maps)
            combined.organic.extend(sr.organic)

        # Add maps results
        combined.maps.extend(all_maps_results)

        # Deduplicate
        progress.phase = "deduplicating"
        yield progress

        unique_results = deduplicate_serp_results(combined, location=location)
        progress.unique_prospects = len(unique_results)
        progress.results = unique_results
        yield progress

        # Complete
        progress.phase = "complete"
        yield progress

    def estimate_cost(self, plan: SearchPlan) -> Dict:
        """
        Estimate cost for a search plan.

        Returns breakdown of API calls and estimated cost.
        """
        # SerpAPI pricing: ~$0.01 per search (varies by plan)
        cost_per_call = 0.01

        return {
            "queries": len(plan.queries),
            "query_list": plan.queries,
            "locations": len(plan.locations),
            "location_list": plan.locations,
            "search_types": plan.search_types,
            "organic_pages": plan.organic_pages,
            "maps_pages": plan.maps_pages,
            "total_api_calls": plan.total_api_calls,
            "max_api_calls": plan.max_api_calls,
            "estimated_cost_usd": round(plan.total_api_calls * cost_per_call, 2),
            "estimated_cost_cents": plan.estimated_cost_cents,
        }

    def _cache_key(self, query: str, location: str) -> str:
        """Generate cache key for query/location combo."""
        if _native.fast_cache_key is not None:
            return _native.fast_cache_key(query, location)
        raw = f"{query.lower()}|{location.lower()}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _get_cached(self, key: str) -> Optional[Dict]:
        """Get cached results if still valid."""
        if key in self._cache:
            cached = self._cache[key]
            if datetime.utcnow() - cached["timestamp"] < self.cache_ttl:
                return cached["data"]
        return None

    def _set_cached(self, key: str, data: Dict):
        """Cache results."""
        self._cache[key] = {
            "timestamp": datetime.utcnow(),
            "data": data,
        }

    def close(self):
        """Close resources."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
