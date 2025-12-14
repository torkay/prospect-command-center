"""
Constants with British/Australian spelling.

Australian English follows British spelling conventions:
- colour (not color)
- organisation (not organization)
- analyse (not analyze)
- centre (not center)
- favour (not favor)
- behaviour (not behavior)
- customise (not customize)
- optimise (not optimize)
"""

# UI Labels (British spelling)
LABELS = {
    # Actions
    "analyze": "Analyse",
    "analyzing": "Analysing",
    "analyzed": "Analysed",
    "customize": "Customise",
    "customizing": "Customising",
    "organize": "Organise",
    "organizing": "Organising",
    "optimize": "Optimise",
    "optimizing": "Optimising",
    # Nouns
    "color": "Colour",
    "colors": "Colours",
    "center": "Centre",
    "centers": "Centres",
    "behavior": "Behaviour",
    "behaviors": "Behaviours",
    "favor": "Favour",
    "favorite": "Favourite",
    "favorites": "Favourites",
    # Status messages
    "website_unreachable": "Website was unreachable during analysis",
    "analysing_website": "Analysing website...",
    "analysis_complete": "Analysis complete",
    "no_analytics": "No Google Analytics detected",
    "no_pixel": "No Facebook Pixel detected",
    # UI sections
    "colour_scheme": "Colour Scheme",
    "organisation": "Organisation",
    "organisations": "Organisations",
}


# Error messages (British spelling)
MESSAGES = {
    "unreachable": "Website was unreachable during analysis; technical details unknown.",
    "timeout": "Website timed out during analysis.",
    "blocked": "Website blocked our analysis request.",
    "error": "An error occurred during analysis.",
}


# Opportunity note templates (British spelling)
NOTES = {
    "unreachable": "Website was unreachable during analysis; technical details unknown",
    "no_website": "No website found - needs web presence",
    "has_gbp_no_site": "Has Google Business Profile but no site to drive traffic to",
    "no_analytics": "no Google Analytics",
    "no_pixel": "no Facebook Pixel",
    "no_booking": "no online booking",
    "no_email": "no visible contact email",
    "no_phone": "phone not easily found",
    "limited_platform": "limited platform",
    "good_tracking": "has good tracking setup",
    "already_running_ads": "already running ads",
    "well_optimised": "Well-optimised - limited obvious opportunities",
}
