use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use scraper::{Html, Selector};
use std::sync::LazyLock;

// Social media domains to match against <a href="..."> links
static SOCIAL_DOMAINS: &[&str] = &[
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "linkedin.com",
    "youtube.com",
    "tiktok.com",
];

// Pre-compiled selectors
static TITLE_SEL: LazyLock<Selector> =
    LazyLock::new(|| Selector::parse("title").unwrap());
static META_DESC_SEL: LazyLock<Selector> =
    LazyLock::new(|| Selector::parse("meta[name='description']").unwrap());
static LINK_SEL: LazyLock<Selector> =
    LazyLock::new(|| Selector::parse("a[href]").unwrap());

/// Extract HTML metadata (title, meta_description, social_links) from raw HTML.
///
/// Returns a dict with keys:
///   - "title": str | None
///   - "meta_description": str | None
///   - "social_links": list[str]
#[pyfunction]
pub fn extract_html_metadata(py: Python<'_>, html: &str) -> PyResult<PyObject> {
    let dict = PyDict::new(py);

    if html.is_empty() {
        dict.set_item("title", py.None())?;
        dict.set_item("meta_description", py.None())?;
        dict.set_item("social_links", PyList::empty(py))?;
        return Ok(dict.into());
    }

    let document = Html::parse_document(html);

    // Extract title
    let title = document
        .select(&TITLE_SEL)
        .next()
        .map(|el| el.text().collect::<String>().trim().to_string())
        .filter(|s| !s.is_empty());

    match title {
        Some(ref t) => dict.set_item("title", t)?,
        None => dict.set_item("title", py.None())?,
    }

    // Extract meta description
    let meta_desc = document
        .select(&META_DESC_SEL)
        .next()
        .and_then(|el| el.value().attr("content").map(|s| s.to_string()))
        .filter(|s| !s.is_empty());

    match meta_desc {
        Some(ref d) => dict.set_item("meta_description", d)?,
        None => dict.set_item("meta_description", py.None())?,
    }

    // Extract social links
    let mut social_links: Vec<String> = Vec::new();

    for element in document.select(&LINK_SEL) {
        if let Some(href) = element.value().attr("href") {
            for domain in SOCIAL_DOMAINS {
                if href.contains(domain) && !social_links.iter().any(|l| l == href) {
                    social_links.push(href.to_string());
                    break;
                }
            }
        }
    }

    dict.set_item("social_links", PyList::new(py, &social_links)?)?;

    Ok(dict.into())
}
