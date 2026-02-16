"""
Native Rust acceleration layer for LeadSwarm.

Attempts to import the compiled _leadswarm_native module (built with maturin).
Falls back gracefully when not available — all functions remain None and callers
should check before use.

Build with: cd rust && maturin develop --release
"""

import logging

_logger = logging.getLogger(__name__)

# Text processing (dedup.py / validation.py)
normalize_domain = None
normalize_name = None
clean_business_name = None
normalize_phone = None
is_directory_domain = None
is_directory_url = None
validate_email_domain = None
filter_emails_for_domain = None

# HTML extraction (contacts.py / technology.py)
extract_emails = None
extract_phones = None
detect_cms = None
detect_tracking = None
detect_booking_system = None
detect_frameworks = None
detect_responsive = None
analyze_tech_stack = None

# Scoring (scoring/fit.py / scoring/opportunity.py)
calculate_fit_score = None
calculate_opportunity_score = None
score_prospects_batch = None

# Geo / cache (orchestrator.py / locations.py)
fast_cache_key = None
haversine_distance = None
batch_haversine = None

# Export serialization (export.py)
serialize_prospects_csv = None
serialize_prospects_json = None

# HTML metadata extraction (crawler.py)
extract_html_metadata = None

AVAILABLE = False

try:
    import _leadswarm_native as _n

    normalize_domain = _n.normalize_domain
    normalize_name = _n.normalize_name
    clean_business_name = _n.clean_business_name
    normalize_phone = _n.normalize_phone
    is_directory_domain = _n.is_directory_domain
    is_directory_url = _n.is_directory_url
    validate_email_domain = _n.validate_email_domain
    filter_emails_for_domain = _n.filter_emails_for_domain

    extract_emails = _n.extract_emails
    extract_phones = _n.extract_phones
    detect_cms = _n.detect_cms
    detect_tracking = _n.detect_tracking
    detect_booking_system = _n.detect_booking_system
    detect_frameworks = _n.detect_frameworks
    detect_responsive = _n.detect_responsive
    analyze_tech_stack = _n.analyze_tech_stack

    calculate_fit_score = _n.calculate_fit_score
    calculate_opportunity_score = _n.calculate_opportunity_score
    score_prospects_batch = _n.score_prospects_batch

    fast_cache_key = _n.fast_cache_key
    haversine_distance = _n.haversine_distance
    batch_haversine = _n.batch_haversine

    serialize_prospects_csv = _n.serialize_prospects_csv
    serialize_prospects_json = _n.serialize_prospects_json

    extract_html_metadata = _n.extract_html_metadata

    AVAILABLE = True
    _logger.info("Rust native acceleration loaded successfully")
except ImportError:
    _logger.info("Rust native module not available, using pure Python")
