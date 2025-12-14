"""Tests for SerpAPI integration."""

import os
import pytest
from prospect.scraper.serpapi import (
    SerpAPIClient,
    SerpAPIError,
    AuthenticationError,
    RateLimitError,
    normalize_au_location,
)
from prospect.models import SerpResults


class TestAustralianLocationNormalization:
    """Test Australian location string normalization."""

    @pytest.mark.parametrize("input_loc,expected", [
        ("Brisbane, QLD", "Brisbane, Queensland, Australia"),
        ("Sydney NSW", "Sydney, New South Wales, Australia"),
        ("Melbourne, VIC", "Melbourne, Victoria, Australia"),
        ("Perth WA", "Perth, Western Australia, Australia"),
        ("Adelaide, SA", "Adelaide, South Australia, Australia"),
        ("Hobart TAS", "Hobart, Tasmania, Australia"),
        ("Canberra ACT", "Canberra, Australian Capital Territory, Australia"),
        ("Darwin NT", "Darwin, Northern Territory, Australia"),
        ("Melbourne", "Melbourne, Australia"),  # No state
        ("Gold Coast, Queensland", "Gold Coast, Queensland, Australia"),  # Full state name
        ("Sydney, Australia", "Sydney, Australia"),  # Already has Australia
    ])
    def test_normalize_location(self, input_loc, expected):
        """Test various Australian location formats."""
        assert normalize_au_location(input_loc) == expected


class TestAuthenticationError:
    """Test API key validation."""

    def test_missing_key_raises_error(self, monkeypatch):
        """Should raise AuthenticationError without API key."""
        monkeypatch.delenv("SERPAPI_KEY", raising=False)
        monkeypatch.delenv("PROSPECT_SERPAPI_KEY", raising=False)

        with pytest.raises(AuthenticationError) as exc_info:
            SerpAPIClient()

        assert "SERPAPI_KEY" in str(exc_info.value)

    def test_explicit_key_works(self, monkeypatch):
        """Should accept explicit API key."""
        monkeypatch.delenv("SERPAPI_KEY", raising=False)
        monkeypatch.delenv("PROSPECT_SERPAPI_KEY", raising=False)

        # This will create the client but won't make API calls
        client = SerpAPIClient(api_key="test_key_123")
        assert client.api_key == "test_key_123"
        client.close()

    def test_env_var_key(self, monkeypatch):
        """Should pick up key from environment variable."""
        monkeypatch.setenv("SERPAPI_KEY", "env_test_key")

        client = SerpAPIClient()
        assert client.api_key == "env_test_key"
        client.close()


class TestClientConfiguration:
    """Test client configuration options."""

    def test_default_configuration(self, monkeypatch):
        """Test default client settings."""
        monkeypatch.setenv("SERPAPI_KEY", "test_key")

        client = SerpAPIClient()
        assert client.google_domain == "google.com.au"
        assert client.gl == "au"
        assert client.hl == "en"
        assert client.timeout == 30
        client.close()

    def test_custom_configuration(self, monkeypatch):
        """Test custom client settings."""
        monkeypatch.setenv("SERPAPI_KEY", "test_key")

        client = SerpAPIClient(
            google_domain="google.co.nz",
            gl="nz",
            hl="mi",
            timeout=60,
        )
        assert client.google_domain == "google.co.nz"
        assert client.gl == "nz"
        assert client.hl == "mi"
        assert client.timeout == 60
        client.close()

    def test_context_manager(self, monkeypatch):
        """Test client as context manager."""
        monkeypatch.setenv("SERPAPI_KEY", "test_key")

        with SerpAPIClient() as client:
            assert client.api_key == "test_key"


class TestExceptionTypes:
    """Test exception class hierarchy."""

    def test_authentication_error_is_serpapi_error(self):
        """AuthenticationError should be a SerpAPIError."""
        assert issubclass(AuthenticationError, SerpAPIError)

    def test_rate_limit_error_is_serpapi_error(self):
        """RateLimitError should be a SerpAPIError."""
        assert issubclass(RateLimitError, SerpAPIError)


@pytest.mark.integration
@pytest.mark.skipif(not os.environ.get("SERPAPI_KEY"), reason="SERPAPI_KEY required")
class TestSerpAPILive:
    """Live integration tests (require API key)."""

    def test_basic_search(self):
        """Test basic search returns results."""
        client = SerpAPIClient()
        results = client.search("plumber", "Sydney, NSW", num_results=10)

        assert isinstance(results, SerpResults)
        assert results.query == "plumber Sydney, NSW"

        # Should have some results
        total = len(results.ads) + len(results.maps) + len(results.organic)
        assert total > 0, "Should return at least some results"

        print(f"\nResults: {len(results.ads)} ads, {len(results.maps)} maps, {len(results.organic)} organic")

        client.close()

    def test_maps_results_have_data(self):
        """Verify maps results have expected fields."""
        client = SerpAPIClient()
        results = client.search("buyer's agent", "Brisbane, QLD", num_results=10)

        if results.maps:
            for m in results.maps:
                assert m.name, "Maps result should have name"
                assert m.position > 0, "Maps result should have position"

        client.close()

    def test_organic_results_have_domains(self):
        """Verify organic results have valid domains."""
        client = SerpAPIClient()
        results = client.search("accountant", "Melbourne, VIC", num_results=10)

        for r in results.organic:
            assert r.domain, f"Organic result should have domain: {r.title}"
            assert "." in r.domain, f"Domain should be valid: {r.domain}"

        client.close()

    def test_no_directories_in_organic(self):
        """Verify directories are filtered from organic results."""
        client = SerpAPIClient()
        results = client.search("electrician", "Perth, WA", num_results=20)

        directory_domains = {"reddit.com", "facebook.com", "yelp.com", "linkedin.com"}

        for result in results.organic:
            for d in directory_domains:
                assert d not in result.domain, f"Directory {d} should be filtered"

        client.close()

    def test_australian_localization(self):
        """Verify results are localized to Australia."""
        client = SerpAPIClient()
        results = client.search("plumber", "Adelaide, SA", num_results=5)

        # Maps results should have Australian addresses
        if results.maps:
            addresses = [m.address.lower() for m in results.maps if m.address]
            has_au_address = any(
                "sa" in a or "adelaide" in a or "australia" in a
                for a in addresses
            )
            assert has_au_address, "Should have Australian addresses in maps results"

        client.close()
