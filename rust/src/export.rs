use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;

// ---------------------------------------------------------------------------
// Helpers – reuse the same extract pattern from scoring.rs
// ---------------------------------------------------------------------------

fn extract_opt_string(py: Python<'_>, map: &HashMap<String, PyObject>, key: &str) -> Option<String> {
    map.get(key)
        .and_then(|obj| obj.extract::<Option<String>>(py).ok())
        .flatten()
}

fn extract_opt_f64(py: Python<'_>, map: &HashMap<String, PyObject>, key: &str) -> Option<f64> {
    map.get(key)
        .and_then(|obj| obj.extract::<Option<f64>>(py).ok())
        .flatten()
}

fn extract_opt_i64(py: Python<'_>, map: &HashMap<String, PyObject>, key: &str) -> Option<i64> {
    map.get(key)
        .and_then(|obj| obj.extract::<Option<i64>>(py).ok())
        .flatten()
}

fn extract_bool(py: Python<'_>, map: &HashMap<String, PyObject>, key: &str) -> bool {
    map.get(key)
        .and_then(|obj| obj.extract::<bool>(py).ok())
        .unwrap_or(false)
}

fn extract_opt_bool(py: Python<'_>, map: &HashMap<String, PyObject>, key: &str) -> Option<bool> {
    map.get(key)
        .and_then(|obj| obj.extract::<Option<bool>>(py).ok())
        .flatten()
}

fn extract_string_list(py: Python<'_>, map: &HashMap<String, PyObject>, key: &str) -> Vec<String> {
    map.get(key)
        .and_then(|obj| obj.extract::<Option<Vec<String>>>(py).ok())
        .flatten()
        .unwrap_or_default()
}

fn str_or_empty(opt: Option<String>) -> String {
    opt.unwrap_or_default()
}

fn yes_no(val: bool) -> &'static str {
    if val { "Yes" } else { "No" }
}

fn extract_signals(py: Python<'_>, map: &HashMap<String, PyObject>) -> Option<HashMap<String, PyObject>> {
    map.get("signals")
        .and_then(|obj| obj.extract::<Option<HashMap<String, PyObject>>>(py).ok())
        .flatten()
}

// ---------------------------------------------------------------------------
// CSV serialization – matches export_csv_string() field order exactly
// ---------------------------------------------------------------------------

const CSV_FIELDS: &[&str] = &[
    "name", "website", "phone", "address", "emails",
    "rating", "review_count", "fit_score", "opportunity_score",
    "priority_score", "opportunity_notes", "found_in_ads",
    "found_in_maps", "found_in_organic", "cms",
    "has_google_analytics", "has_booking_system",
];

#[pyfunction]
pub fn serialize_prospects_csv(prospects: Vec<HashMap<String, PyObject>>) -> PyResult<String> {
    Python::with_gil(|py| {
        let mut wtr = csv::Writer::from_writer(Vec::new());

        // Header
        wtr.write_record(CSV_FIELDS)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;

        for p in &prospects {
            let signals = extract_signals(py, p);

            let cms = signals.as_ref()
                .and_then(|s| extract_opt_string(py, s, "cms"))
                .unwrap_or_default();
            let has_analytics = signals.as_ref()
                .map(|s| extract_opt_bool(py, s, "has_google_analytics").unwrap_or(false))
                .unwrap_or(false);
            let has_booking = signals.as_ref()
                .map(|s| extract_opt_bool(py, s, "has_booking_system").unwrap_or(false))
                .unwrap_or(false);

            let emails = extract_string_list(py, p, "emails").join("; ");
            let rating = extract_opt_f64(py, p, "rating")
                .map(|v| v.to_string())
                .unwrap_or_default();
            let review_count = extract_opt_i64(py, p, "review_count")
                .map(|v| v.to_string())
                .unwrap_or_default();
            let fit_score = extract_opt_i64(py, p, "fit_score")
                .map(|v| v.to_string())
                .unwrap_or_else(|| "0".to_string());
            let opp_score = extract_opt_i64(py, p, "opportunity_score")
                .map(|v| v.to_string())
                .unwrap_or_else(|| "0".to_string());
            let priority = extract_opt_f64(py, p, "priority_score")
                .map(|v| format!("{:.1}", v))
                .unwrap_or_else(|| "0.0".to_string());

            let record: Vec<String> = vec![
                str_or_empty(extract_opt_string(py, p, "name")),
                str_or_empty(extract_opt_string(py, p, "website")),
                str_or_empty(extract_opt_string(py, p, "phone")),
                str_or_empty(extract_opt_string(py, p, "address")),
                emails,
                rating,
                review_count,
                fit_score,
                opp_score,
                priority,
                str_or_empty(extract_opt_string(py, p, "opportunity_notes")),
                yes_no(extract_bool(py, p, "found_in_ads")).to_string(),
                yes_no(extract_bool(py, p, "found_in_maps")).to_string(),
                yes_no(extract_bool(py, p, "found_in_organic")).to_string(),
                cms,
                yes_no(has_analytics).to_string(),
                yes_no(has_booking).to_string(),
            ];

            wtr.write_record(&record)
                .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
        }

        let bytes = wtr.into_inner()
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
        String::from_utf8(bytes)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
    })
}

// ---------------------------------------------------------------------------
// JSON serialization – matches prospect_to_dict() nested structure
// ---------------------------------------------------------------------------

fn prospect_to_json_value(py: Python<'_>, p: &HashMap<String, PyObject>) -> serde_json::Value {
    let emails = extract_string_list(py, p, "emails");
    let signals = extract_signals(py, p);

    let mut data = serde_json::Map::new();
    data.insert("name".into(), json_opt_str(extract_opt_string(py, p, "name")));
    data.insert("website".into(), json_opt_str(extract_opt_string(py, p, "website")));
    data.insert("domain".into(), json_opt_str(extract_opt_string(py, p, "domain")));
    data.insert("phone".into(), json_opt_str(extract_opt_string(py, p, "phone")));
    data.insert("address".into(), json_opt_str(extract_opt_string(py, p, "address")));
    data.insert("emails".into(), serde_json::Value::Array(
        emails.into_iter().map(serde_json::Value::String).collect()
    ));

    // serp_presence
    let serp = serde_json::json!({
        "ads": {
            "found": extract_bool(py, p, "found_in_ads"),
            "position": json_opt_i64(extract_opt_i64(py, p, "ad_position")),
        },
        "maps": {
            "found": extract_bool(py, p, "found_in_maps"),
            "position": json_opt_i64(extract_opt_i64(py, p, "maps_position")),
        },
        "organic": {
            "found": extract_bool(py, p, "found_in_organic"),
            "position": json_opt_i64(extract_opt_i64(py, p, "organic_position")),
        },
    });
    data.insert("serp_presence".into(), serp);

    // google_business
    let gb = serde_json::json!({
        "rating": json_opt_f64(extract_opt_f64(py, p, "rating")),
        "review_count": json_opt_i64(extract_opt_i64(py, p, "review_count")),
        "category": json_opt_str(extract_opt_string(py, p, "category")),
    });
    data.insert("google_business".into(), gb);

    // scores
    let priority = extract_opt_f64(py, p, "priority_score")
        .map(|v| (v * 100.0).round() / 100.0)
        .unwrap_or(0.0);
    let scores = serde_json::json!({
        "fit": extract_opt_i64(py, p, "fit_score").unwrap_or(0),
        "opportunity": extract_opt_i64(py, p, "opportunity_score").unwrap_or(0),
        "priority": priority,
    });
    data.insert("scores".into(), scores);

    data.insert("opportunity_notes".into(), json_opt_str(extract_opt_string(py, p, "opportunity_notes")));
    data.insert("source".into(), json_opt_str(extract_opt_string(py, p, "source")));
    data.insert("scraped_at".into(), json_opt_str(extract_opt_string(py, p, "scraped_at")));

    // signals (optional)
    if let Some(sig) = signals {
        let sig_val = serde_json::json!({
            "reachable": extract_opt_bool(py, &sig, "reachable"),
            "cms": json_opt_str(extract_opt_string(py, &sig, "cms")),
            "tracking": {
                "google_analytics": extract_opt_bool(py, &sig, "has_google_analytics"),
                "facebook_pixel": extract_opt_bool(py, &sig, "has_facebook_pixel"),
                "google_ads": extract_opt_bool(py, &sig, "has_google_ads"),
            },
            "has_booking_system": extract_opt_bool(py, &sig, "has_booking_system"),
            "load_time_ms": json_opt_i64(extract_opt_i64(py, &sig, "load_time_ms")),
            "title": json_opt_str(extract_opt_string(py, &sig, "title")),
            "meta_description": json_opt_str(extract_opt_string(py, &sig, "meta_description")),
            "social_links": serde_json::Value::Array(
                extract_string_list(py, &sig, "social_links")
                    .into_iter()
                    .map(serde_json::Value::String)
                    .collect()
            ),
        });
        data.insert("signals".into(), sig_val);
    }

    serde_json::Value::Object(data)
}

fn json_opt_str(opt: Option<String>) -> serde_json::Value {
    match opt {
        Some(s) => serde_json::Value::String(s),
        None => serde_json::Value::Null,
    }
}

fn json_opt_i64(opt: Option<i64>) -> serde_json::Value {
    match opt {
        Some(v) => serde_json::Value::Number(v.into()),
        None => serde_json::Value::Null,
    }
}

fn json_opt_f64(opt: Option<f64>) -> serde_json::Value {
    match opt {
        Some(v) => serde_json::Number::from_f64(v)
            .map(serde_json::Value::Number)
            .unwrap_or(serde_json::Value::Null),
        None => serde_json::Value::Null,
    }
}

#[pyfunction]
pub fn serialize_prospects_json(prospects: Vec<HashMap<String, PyObject>>, pretty: bool) -> PyResult<String> {
    Python::with_gil(|py| {
        let items: Vec<serde_json::Value> = prospects
            .iter()
            .map(|p| prospect_to_json_value(py, p))
            .collect();

        let result = if pretty {
            serde_json::to_string_pretty(&items)
        } else {
            serde_json::to_string(&items)
        };

        result.map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
    })
}
