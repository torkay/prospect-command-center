use pyo3::prelude::*;
use xxhash_rust::xxh3::xxh3_64;

/// Generate a cache key from query + location using xxHash3.
/// Lowercases both inputs, joins with "|", returns hex digest.
#[pyfunction]
pub fn fast_cache_key(query: &str, location: &str) -> String {
    let raw = format!("{}|{}", query.to_lowercase(), location.to_lowercase());
    let hash = xxh3_64(raw.as_bytes());
    format!("{:016x}", hash)
}

/// Calculate the haversine distance between two lat/lon points in kilometres.
#[pyfunction]
pub fn haversine_distance(lat1: f64, lon1: f64, lat2: f64, lon2: f64) -> f64 {
    const R: f64 = 6371.0; // Earth's radius in km

    let lat1_rad = lat1.to_radians();
    let lat2_rad = lat2.to_radians();
    let delta_lat = (lat2 - lat1).to_radians();
    let delta_lon = (lon2 - lon1).to_radians();

    let a = (delta_lat / 2.0).sin().powi(2)
        + lat1_rad.cos() * lat2_rad.cos() * (delta_lon / 2.0).sin().powi(2);

    let c = 2.0 * a.sqrt().atan2((1.0 - a).sqrt());

    R * c
}

/// Batch haversine: compute distances from a base point to many target points.
/// Returns a Vec of distances in km, one per input point.
#[pyfunction]
pub fn batch_haversine(base_lat: f64, base_lng: f64, points: Vec<(f64, f64)>) -> Vec<f64> {
    points
        .iter()
        .map(|&(lat, lng)| haversine_distance(base_lat, base_lng, lat, lng))
        .collect()
}
