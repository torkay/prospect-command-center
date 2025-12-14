"""Tests for data accuracy: domain normalization and directory filtering."""

import pytest
from prospect.dedup import normalize_domain, is_directory_url, is_directory_domain


class TestNormalizeDomain:
    """Test domain normalization from URLs."""

    def test_basic_url(self):
        """Standard URL should return domain without www."""
        assert normalize_domain("https://www.example.com/page") == "example.com"

    def test_subdomain_preserved(self):
        """Subdomains (other than www) should be preserved."""
        assert normalize_domain("https://sub.example.com.au/") == "sub.example.com.au"

    def test_bare_domain(self):
        """Domain without protocol should work."""
        assert normalize_domain("example.com") == "example.com"

    def test_https_only_returns_none(self):
        """Just 'https:' should return None, not 'https:'."""
        assert normalize_domain("https:") is None
        assert normalize_domain("http:") is None
        assert normalize_domain("https://") is None
        assert normalize_domain("http://") is None

    def test_empty_string_returns_none(self):
        """Empty string should return None."""
        assert normalize_domain("") is None
        assert normalize_domain("   ") is None

    def test_none_input_returns_none(self):
        """None input should return None."""
        assert normalize_domain(None) is None

    def test_removes_port_number(self):
        """Port numbers should be stripped."""
        assert normalize_domain("https://example.com:8080/page") == "example.com"

    def test_removes_www_prefix(self):
        """www prefix should be removed."""
        assert normalize_domain("https://www.example.com") == "example.com"
        assert normalize_domain("www.example.com") == "example.com"

    def test_lowercases_domain(self):
        """Domain should be lowercased."""
        assert normalize_domain("https://EXAMPLE.COM") == "example.com"
        assert normalize_domain("https://Example.Com.Au") == "example.com.au"

    def test_invalid_domain_returns_none(self):
        """Invalid domain-like strings should return None."""
        assert normalize_domain("not a url") is None
        assert normalize_domain("20+ comments") is None
        assert normalize_domain("abc") is None  # Too short, no dot

    def test_domain_with_invalid_chars_returns_none(self):
        """Domains with invalid characters should return None."""
        assert normalize_domain("https://exam<ple>.com") is None
        assert normalize_domain("https://exam'ple.com") is None

    def test_australian_domains(self):
        """Australian domains should work correctly."""
        assert normalize_domain("https://www.business.com.au") == "business.com.au"
        assert normalize_domain("business.net.au") == "business.net.au"

    def test_complex_path_ignored(self):
        """URL path should not affect domain extraction."""
        url = "https://www.example.com.au/some/long/path?query=value#hash"
        assert normalize_domain(url) == "example.com.au"


class TestDirectoryFiltering:
    """Test directory/social media filtering."""

    def test_reddit_domain_filtered(self):
        """Reddit domain should be detected as directory."""
        assert is_directory_domain("reddit.com") is True
        assert is_directory_domain("www.reddit.com") is True  # Substring match catches www prefix too

    def test_reddit_url_pattern_filtered(self):
        """Reddit URLs with /r/ should be filtered."""
        assert is_directory_url("https://www.reddit.com/r/brisbane/comments/123", "reddit.com") is True

    def test_facebook_filtered(self):
        """Facebook should be detected as directory."""
        assert is_directory_domain("facebook.com") is True

    def test_linkedin_company_pages_filtered(self):
        """LinkedIn company pages should be filtered by URL pattern."""
        assert is_directory_url("https://linkedin.com/company/acme-corp", "linkedin.com") is True

    def test_yelp_filtered(self):
        """Yelp should be detected as directory."""
        assert is_directory_domain("yelp.com") is True
        assert is_directory_domain("yelp.com.au") is True

    def test_yellowpages_filtered(self):
        """Yellow Pages should be detected as directory."""
        assert is_directory_domain("yellowpages.com.au") is True

    def test_legitimate_business_not_filtered(self):
        """Legitimate business domains should not be filtered."""
        assert is_directory_domain("acmeplumbing.com.au") is False
        assert is_directory_domain("mybusiness.com") is False

    def test_job_boards_filtered(self):
        """Job boards should be filtered."""
        assert is_directory_domain("seek.com.au") is True
        assert is_directory_domain("indeed.com.au") is True

    def test_social_media_filtered(self):
        """Social media platforms should be filtered."""
        assert is_directory_domain("instagram.com") is True
        assert is_directory_domain("twitter.com") is True
        assert is_directory_domain("x.com") is True
        assert is_directory_domain("tiktok.com") is True

    def test_url_patterns_work(self):
        """URL-based patterns should detect directory content."""
        # /biz/ pattern (Yelp business pages)
        assert is_directory_url("https://yelp.com/biz/some-business", "yelp.com") is True

        # /company/ pattern (LinkedIn)
        assert is_directory_url("https://linkedin.com/company/test", "linkedin.com") is True

        # /profile/ pattern
        assert is_directory_url("https://somesite.com/profile/user123", "somesite.com") is True

    def test_directory_check_with_empty_domain(self):
        """Empty domain should return False."""
        assert is_directory_domain("") is False
        assert is_directory_domain(None) is False


class TestIntegrationScenarios:
    """Integration tests combining normalization and filtering."""

    def test_reddit_url_normalization_and_filter(self):
        """Reddit URL should normalize then filter."""
        url = "https://www.reddit.com/r/brisbane/comments/abc123/title"
        domain = normalize_domain(url)
        assert domain == "reddit.com"
        assert is_directory_url(url, domain) is True

    def test_business_url_passes_through(self):
        """Legitimate business URL should pass through."""
        url = "https://www.mybusiness.com.au/contact"
        domain = normalize_domain(url)
        assert domain == "mybusiness.com.au"
        assert is_directory_domain(domain) is False
        assert is_directory_url(url, domain) is False
