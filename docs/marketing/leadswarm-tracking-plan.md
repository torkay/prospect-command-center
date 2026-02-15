# LeadSwarm Tracking Plan

## Key questions
- Which on-page signals (CTA clicks, scroll depth, sample toggles) best predict that a visitor will try the product?
- How do visitors flow from awareness (page view) to action (Start trial) to completion (trial signup success)?
- Are we capturing every paid/organic channel through UTMs so we can attribute the primary conversion to source/campaign?
- Is the marketing funnel instrumented end-to-end so we can debug drop-offs (CTA → signup started → form submit → success/failure)?
- Do dashboards and QA checks validate both real-time activation and long-term activation retention?

## Primary conversion: Start trial
`marketing.signup_started` is the funnel gate that marks intent to take a trial. It fires whenever a user clicks a `data-track` element whose name contains `start_trial`, so it is scoped to every primary CTA (hero buttons, sticky bars, footer links) that promote the trial. Treat this event as the core activation goal. Use it to compute Start trial CTAs per channel/UTM and as the denominator for downstream conversion rates (form submission, signup success).

### Supporting signals
- `marketing.trial_form_submit` (method: `password`) captures form intent once the user submits the trial form on `/register`.
- `marketing.trial_signup_success` carries the `email_domain` to help monitor enterprise vs. free address adoption.
- `marketing.trial_signup_failure` provides a `detail` string so we can triage friction sources (validation errors, rate limiting, network issues).

## Event table (`/api/v1/marketing/events`)
| Event | Trigger | `properties` payload | Notes |
| --- | --- | --- | --- |
| `marketing.page_view` | Page load (generic landing) | `title` = document title | Fires from `prospect/web/marketing/site.js` immediately after bootstrapping the marketing tracker. Includes metadata like `path`, `referrer`, UTMs, `anonymous_id`, and `session_id`. |
| `marketing.cta_click` | Click on any `[data-track]` element | `name` = CTA identifier, `text` = truncated visible text (80 chars) | Allows CTA-level attribution for every call to action placed on the marketing site. Mirrors the same DOM hook that also triggers `marketing.signup_started` when `name` contains `start_trial`. |
| `marketing.signup_started` | CTA click whose `data-track` contains `start_trial` | `source` = CTA name | Primary “start trial” intent signal. Log counts by UTM source/campaign in the dashboard. |
| `marketing.scroll_depth` | Scroll reaches 25/50/75/100% | `percent` = depth threshold | Provides engagement context to interpret CTA performance on long landing pages. |
| `marketing.sample_toggled` | Visitor toggles the sample panel | `open` = boolean for panel visibility after click | Measure interest in the “View a sample” section. |
| `marketing.page_view` | `/register` template initial load | `page` = `"register"` | Duplicate event on the registration page so that the funnel logic can segment authenticated flows. Includes `page_url` and the same metadata object. |
| `marketing.trial_form_submit` | `/register` form submit | `method` = `"password"` | Indicates intent to create a paid account; pair with `anonymous_id` and UTM to check whether the same session clicked Start trial earlier. |
| `marketing.trial_signup_success` | Successful response from `/auth/register` | `email_domain` = domain from submitted email | Activation completion signal. Tie it to actual account creation and localStorage session persistence (token + user). |
| `marketing.trial_signup_failure` | Registration API error or network failure | `detail` = server error detail or `"network_error"` | Failure chord for the funnel; log the distinct `detail` values alongside `utm_source` so paid campaigns know if they trigger new failure modes. |

Every event sends `utm` with the standard five keys (source, medium, campaign, term, content) and `path`/`referrer`. The server then hydrates `source` and `campaign` columns on `MarketingEvent` from the `utm` object before persisting, and captures metadata such as `session_id`, `user_agent`, and the raw `properties` for downstream analysis. Refer to `prospect/web/api/v1/marketing.py` and `prospect/web/database.py` for how the payload is normalized.

## Naming convention
- Prefix every event with `marketing.` so dashboard teams immediately know the domain.
- Use snake_case for the action portion (e.g., `marketing.trial_form_submit`, `marketing.sample_toggled`).
- Favor verbs for action names and nouns for categorical context (e.g., `cta_click`, `page_view`).
- Include the CTA name, page, or control that generated the event via properties rather than inflating the event name.
- If the event measures a state change (expand/collapse), append `_toggled` or `_changed` and include the new value as a property.
- Document every new name in this plan before rolling it out so reporting stays consistent.

## UTM policy
- Always append `utm_source`, `utm_medium`, and `utm_campaign` to paid, owned, and earned marketing links. Optional but strongly recommended: `utm_term` and `utm_content` for keyword-level clarity.
- The marketing tracker stores the latest UTM bundle on the landing domain in `localStorage` (`leadswarm_utm`) and reuses it for every event until the user navigates away.
- Each `/api/v1/marketing/events` payload includes `utm` plus a `source`/`campaign` surface inherited by the `MarketingEvent` row, ensuring downstream dashboards can break the funnel by channel without chasing query params.
- All UTM links should match the naming conventions in the broader marketing playbook (e.g., `leadswarm_email`, `leadswarm_organic`, `leadswarm_paid_google`), and the `utm_campaign` should be human-readable to make reporting painless.
- When redirecting from gated landing pages or email blasts, preserve the UTM parameters so the tracker can rehydrate them (the site JS already reads the query string to populate the localStorage snapshot).

## Dashboard metrics
### Activation
- **Primary metric:** Count of `marketing.signup_started` events per day/weekly by `utm_source` and `utm_campaign`. Mark this as the activation target.
- **Activation conversion rate:** `marketing.trial_signup_success` ÷ `marketing.signup_started`, broken down by channel (source/campaign). Use the success event as a proxy for account creation and tie it back to server-side user records when possible.
- **Email domain mix:** Distribution of `email_domain` from `marketing.trial_signup_success` to understand whether we are attracting enterprise vs. consumer addresses.

### Funnel
- Visualize the following sequential steps: `marketing.page_view` → `marketing.cta_click` → `marketing.signup_started` → `marketing.trial_form_submit` → `{success|failure}`.
- Surface the `detail` property on `marketing.trial_signup_failure` as a breakdown so product/ops teams can fix the two or three most frequent failure modes.
- Monitor scroll depth (percentage of users reaching 25/50/75/100%) and sample toggles per session to correlate deeper engagement with conversion lifts.
- Track `marketing.page_view` counts for `/register` separately so you can normalize survey data by the size of the trial-ready audience.

## QA checklist
1. Load the marketing landing page with the browser dev tools network tab open and verify that each user interaction calls `POST /api/v1/marketing/events` with `event` and `properties` populated correctly.
2. Ensure every marketing CTA exposes a `data-track` attribute and that `marketing.cta_click` and `marketing.signup_started` fire for each control that should surface in the funnel.
3. Submit the `/register` form with valid/invalid data and confirm the `marketing.trial_form_submit`, `marketing.trial_signup_success`, and `marketing.trial_signup_failure` events include the expected `method`, `email_domain`, and `detail` fields.
4. Check that UTMs survive navigation by appending `?utm_source=test&utm_medium=email&utm_campaign=qa` to the landing URL and confirming every fired event contains that `utm` object in the payload.
5. Validate that failure events carry actionable `detail` strings (e.g., `validation_error`, `already_registered`, `network_error`) so the QA dashboard can highlight the dominant friction points per campaign.
6. Confirm `anonymous_id`/`session_id` persist across marketing interactions (CTA click → Start trial → form submit) so identity stitching works in the data warehouse.
7. Record every new event or property addition in this tracking plan before deploying to staging or production to avoid duplicate instrumentation and to keep dashboards accurate.
