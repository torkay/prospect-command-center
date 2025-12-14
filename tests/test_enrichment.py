"""Tests for enrichment: email extraction and spam filtering."""

import pytest
from prospect.enrichment.contacts import (
    extract_emails,
    extract_phones,
    is_spam_email,
    normalize_phone,
)


class TestSpamEmailFiltering:
    """Test spam email detection."""

    def test_error_tracking_email_is_spam(self):
        """Error tracking emails should be detected as spam."""
        assert is_spam_email("abc123@error-tracking.reddit.com") is True
        assert is_spam_email("9f057df6115a4bb488c08ea12a835e6e@error-tracking.reddit.com") is True

    def test_sentry_email_is_spam(self):
        """Sentry.io emails should be detected as spam."""
        assert is_spam_email("alert@sentry.io") is True

    def test_noreply_email_is_spam(self):
        """No-reply emails should be detected as spam."""
        assert is_spam_email("noreply@example.com") is True
        assert is_spam_email("no-reply@company.com") is True
        assert is_spam_email("donotreply@business.com") is True

    def test_mailer_daemon_is_spam(self):
        """Mailer daemon emails should be detected as spam."""
        assert is_spam_email("mailer-daemon@server.com") is True
        assert is_spam_email("postmaster@domain.com") is True

    def test_automated_email_is_spam(self):
        """Automated/notification emails should be detected as spam."""
        assert is_spam_email("automated@company.com") is True
        assert is_spam_email("notifications@service.com") is True

    def test_platform_domains_are_spam(self):
        """Platform system domains should be detected as spam."""
        assert is_spam_email("user@wix.com") is True
        assert is_spam_email("site@squarespace.com") is True
        assert is_spam_email("bounce@sendgrid.net") is True
        assert is_spam_email("mail@mailchimp.com") is True

    def test_hash_based_email_is_spam(self):
        """Long hex-string emails should be detected as spam."""
        assert is_spam_email("abcdef1234567890abcdef@domain.com") is True

    def test_legitimate_email_not_spam(self):
        """Real business emails should not be detected as spam."""
        assert is_spam_email("info@mybusiness.com.au") is False
        assert is_spam_email("contact@acmeplumbing.com") is False
        assert is_spam_email("john.smith@company.net") is False
        assert is_spam_email("sales@example.org") is False

    def test_personal_style_email_not_spam(self):
        """Personal-style business emails should not be spam."""
        assert is_spam_email("john@plumber.com.au") is False
        assert is_spam_email("hello@mybiz.com") is False


class TestEmailExtraction:
    """Test email extraction from HTML."""

    def test_extracts_simple_email(self):
        """Basic email should be extracted."""
        html = "<p>Contact us at info@business.com</p>"
        emails = extract_emails(html)
        assert "info@business.com" in emails

    def test_extracts_multiple_emails(self):
        """Multiple emails should be extracted."""
        html = """
        <p>Email: john@company.com</p>
        <p>Sales: sales@company.com</p>
        """
        emails = extract_emails(html)
        assert "john@company.com" in emails
        assert "sales@company.com" in emails

    def test_deduplicates_emails(self):
        """Duplicate emails should be deduplicated."""
        html = """
        <p>info@business.com</p>
        <p>Contact: info@business.com</p>
        <footer>info@business.com</footer>
        """
        emails = extract_emails(html)
        assert emails.count("info@business.com") == 1

    def test_lowercases_emails(self):
        """Emails should be lowercased."""
        html = "<p>Email: John.Smith@COMPANY.COM</p>"
        emails = extract_emails(html)
        assert "john.smith@company.com" in emails

    def test_filters_spam_emails(self):
        """Spam emails should be filtered out."""
        html = """
        <p>info@business.com</p>
        <p>noreply@business.com</p>
        <p>abc123@error-tracking.reddit.com</p>
        """
        emails = extract_emails(html)
        assert "info@business.com" in emails
        assert "noreply@business.com" not in emails
        assert "abc123@error-tracking.reddit.com" not in emails

    def test_filters_example_domains(self):
        """Example/test domains should be filtered."""
        html = """
        <p>real@business.com</p>
        <p>test@example.com</p>
        <p>demo@test.com</p>
        """
        emails = extract_emails(html)
        assert "real@business.com" in emails
        assert len([e for e in emails if "example.com" in e]) == 0
        assert len([e for e in emails if "test.com" in e]) == 0

    def test_filters_asset_urls(self):
        """Asset file patterns should not be extracted as emails."""
        html = """
        <p>contact@business.com</p>
        <img src="logo@2x.png">
        <link href="style@1.5.css">
        <script src="app@bundle.js"></script>
        """
        emails = extract_emails(html)
        assert "contact@business.com" in emails
        assert len([e for e in emails if ".png" in e]) == 0
        assert len([e for e in emails if ".css" in e]) == 0
        assert len([e for e in emails if ".js" in e]) == 0

    def test_filters_webp_retina_images(self):
        """Retina image naming patterns should not be extracted."""
        html = """
        <p>hello@business.com</p>
        <img src="flags@2x.webp">
        <img src="globe@2x.webp">
        <img src="icon@3x.png">
        """
        emails = extract_emails(html)
        assert "hello@business.com" in emails
        assert len([e for e in emails if "@2x" in e]) == 0
        assert len([e for e in emails if "@3x" in e]) == 0

    def test_filters_very_long_emails(self):
        """Very long emails (>100 chars) should be filtered."""
        long_local = "a" * 100
        html = f"<p>info@business.com</p><p>{long_local}@domain.com</p>"
        emails = extract_emails(html)
        assert "info@business.com" in emails
        assert len([e for e in emails if len(e) > 100]) == 0

    def test_limits_email_count(self):
        """Should limit to 5 emails max."""
        html = "\n".join([f"<p>email{i}@business.com</p>" for i in range(10)])
        emails = extract_emails(html)
        assert len(emails) <= 5

    def test_empty_html_returns_empty(self):
        """Empty HTML should return empty list."""
        assert extract_emails("") == []
        assert extract_emails(None) == []


class TestPhoneNormalization:
    """Test phone number normalization."""

    def test_mobile_format(self):
        """Mobile numbers should be formatted correctly."""
        assert normalize_phone("0412345678") == "0412 345 678"
        assert normalize_phone("0412 345 678") == "0412 345 678"

    def test_landline_format(self):
        """Landline numbers should be formatted correctly."""
        assert normalize_phone("0298765432") == "02 9876 5432"

    def test_international_format(self):
        """International format should be normalized."""
        assert normalize_phone("+61412345678") == "0412 345 678"
        assert normalize_phone("+610412345678") == "0412 345 678"

    def test_1300_format(self):
        """1300 numbers should be formatted correctly."""
        assert normalize_phone("1300123456") == "1300 123 456"

    def test_1800_format(self):
        """1800 numbers should be formatted correctly."""
        assert normalize_phone("1800123456") == "1800 123 456"

    def test_13_short_format(self):
        """13 XX XX short numbers - note: filtered as too short (<8 digits) to avoid false positives."""
        # Implementation requires minimum 8 digits to avoid false positives
        # 13 XX XX numbers (6 digits) are filtered out
        assert normalize_phone("131234") == ""

    def test_too_short_returns_empty(self):
        """Too short numbers should return empty."""
        assert normalize_phone("12345") == ""
        assert normalize_phone("") == ""

    def test_none_returns_empty(self):
        """None input should return empty string."""
        assert normalize_phone(None) == ""


class TestPhoneExtraction:
    """Test phone extraction from HTML."""

    def test_extracts_mobile(self):
        """Mobile numbers should be extracted."""
        html = "<p>Call us: 0412 345 678</p>"
        phones = extract_phones(html)
        assert len(phones) > 0
        assert any("0412" in p for p in phones)

    def test_extracts_landline(self):
        """Landline numbers should be extracted."""
        html = "<p>Office: (02) 9876 5432</p>"
        phones = extract_phones(html)
        assert len(phones) > 0

    def test_extracts_1300(self):
        """1300 numbers should be extracted."""
        html = "<p>Call: 1300 123 456</p>"
        phones = extract_phones(html)
        assert len(phones) > 0
        assert any("1300" in p for p in phones)

    def test_deduplicates_phones(self):
        """Duplicate phone numbers should be deduplicated."""
        html = """
        <p>0412 345 678</p>
        <footer>0412 345 678</footer>
        <div>0412345678</div>
        """
        phones = extract_phones(html)
        # After normalization, these should all be the same
        unique_normalized = set(phones)
        assert len(unique_normalized) == 1

    def test_empty_html_returns_empty(self):
        """Empty HTML should return empty list."""
        assert extract_phones("") == []
        assert extract_phones(None) == []
