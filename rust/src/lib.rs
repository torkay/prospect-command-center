use pyo3::prelude::*;

mod export;
mod geo;
mod html;
mod metadata;
mod scoring;
mod text;

/// Native performance extensions for LeadSwarm.
#[pymodule]
fn _leadswarm_native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(text::normalize_domain, m)?)?;
    m.add_function(wrap_pyfunction!(text::normalize_name, m)?)?;
    m.add_function(wrap_pyfunction!(text::clean_business_name, m)?)?;
    m.add_function(wrap_pyfunction!(text::normalize_phone, m)?)?;
    m.add_function(wrap_pyfunction!(text::is_directory_domain, m)?)?;
    m.add_function(wrap_pyfunction!(text::is_directory_url, m)?)?;
    m.add_function(wrap_pyfunction!(text::validate_email_domain, m)?)?;
    m.add_function(wrap_pyfunction!(text::filter_emails_for_domain, m)?)?;

    m.add_function(wrap_pyfunction!(html::extract_emails, m)?)?;
    m.add_function(wrap_pyfunction!(html::extract_phones, m)?)?;
    m.add_function(wrap_pyfunction!(html::detect_cms, m)?)?;
    m.add_function(wrap_pyfunction!(html::detect_tracking, m)?)?;
    m.add_function(wrap_pyfunction!(html::detect_booking_system, m)?)?;
    m.add_function(wrap_pyfunction!(html::detect_frameworks, m)?)?;
    m.add_function(wrap_pyfunction!(html::detect_responsive, m)?)?;
    m.add_function(wrap_pyfunction!(html::analyze_tech_stack, m)?)?;

    m.add_function(wrap_pyfunction!(scoring::calculate_fit_score, m)?)?;
    m.add_function(wrap_pyfunction!(scoring::calculate_opportunity_score, m)?)?;
    m.add_function(wrap_pyfunction!(scoring::score_prospects_batch, m)?)?;

    m.add_function(wrap_pyfunction!(geo::fast_cache_key, m)?)?;
    m.add_function(wrap_pyfunction!(geo::haversine_distance, m)?)?;
    m.add_function(wrap_pyfunction!(geo::batch_haversine, m)?)?;

    m.add_function(wrap_pyfunction!(export::serialize_prospects_csv, m)?)?;
    m.add_function(wrap_pyfunction!(export::serialize_prospects_json, m)?)?;

    m.add_function(wrap_pyfunction!(metadata::extract_html_metadata, m)?)?;

    Ok(())
}
