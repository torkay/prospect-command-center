# LeadSwarm Trial definition

This document captures how **Start trial** is defined today, what a trial should give prospects access to, the minimum activation checklist, an explicit 7‑day onboarding path, and the in‑app prompts that live inside `/app`.

## 1. “Start trial” == account creation + immediate /app access
- **Marketing messaging:** `/marketing/index.html` already explains the trial: “Create an account and you can run searches in the app. Usage limits depend on your plan and configuration.” That lives on every Start trial CTA in the hero, proof, and FAQ sections.
- **What a user actually does:** the register page (`/register`) collects name, email, and password, POSTs to `/api/v1/auth/register`, records the JWT in `localStorage`, and redirects straight into `/app` once the token is issued.
- **No card needed:** there is no billing step, so the trial is fully gated by authentication + onboarding.
- **Default plan:** newly created `User` rows default to the `scout` tier (`tier="scout"`, 100 searches / 50 enrichments, `subscription_status="none"`) as defined in `prospect/web/database.py`. Usage enforcement and 80%/100% warnings are already wired via `prospect/web/api/v1/usage.py`.

## 2. Proposed limits for the trial period
| Phase | Tier + usage | Search/Enrichment budget | Why this makes sense |
| --- | --- | --- | --- |
| Days 0‑7 (Reverse trial) | Temporary command/Scale tier with 2000 searches & 1500 enrichments (same as the “command” tier in `usage.py`). This is the “wow period” described in `docs/research/pcc-pricing-optimization-audit.md` that drives urgency for the Founding Member offer. | 0‑7 days: essentially unlimited within those caps, enough to run multiple deep searches, exports, and campaigns. | Demonstrates the full lead discovery power before the free tier. Loss‑aversion messaging at day 7 keeps them engaged. |
| Day 8+ (base free tier) | Revert to scout defaults: 100 searches / 50 enrichments per rolling month (per `database.py`). | Alerts fire automatically at 80% usage and block at 100% via `usage.py`; use those thresholds to trigger upgrade CTAs. | Forces the user to decide: stay limited/free or upgrade to keep the command capabilities they just experienced. |

## 3. Activation checklist (minimum success)
1. **Run a search from the Dashboard Quick Search card.** The form with `id="quick-search-form"` is the fastest path to results and validates that we can pull prospects from their first query.
2. **Run a full search via the Search screen** (`page-title = New Search`). Guide them to set the depth slider (`id="depth-slider"`) to “Standard” so they understand how depth tiers translate to prospect volume, API calls, and cost.
3. **Observe the progress card.** The `#search-progress` panel and its progress bar show real-time activity; once it completes, remind them to visit the Prospects page so the scan isn’t wasted.
4. **Open one prospect detail.** The detail panel (`#detail-panel`) surfaces Fit/Opportunity/Priority scores plus contact info and technical analysis; they can’t sell without understanding the score explanation and copy buttons on phone/email.
5. **Mark at least one prospect status or take an action.** Use the “Qualify”, “Contacted”, or “Skip” buttons inside the detail view so we know they can move a prospect through the pipeline.
6. **Export or save a campaign.** Click “Export” (CSV/JSON/Sheets) from `/prospects` or press the “Save as Campaign” button from the search form to prove they can build reusable data sources.

Completing this checklist moves a user from “signed up” to “activated” (mirrors the onboarding_step field in `User` and the tour steps that endpoint tracks). Finishing the score tooltip (`.score-tooltip` hover) should mark `score_explained` to close the loop.

## 4. 7-day onboarding flow
| Day | Trigger | Promises + actions | Supporting content |
| --- | --- | --- | --- |
| 0 (Registration) | Immediately after `/auth/register` returns a token | Show welcome modal in `/app` that invites them to start the tour (calls `/onboarding/step/welcome_seen` and opens the Search page). Send the instant welcome email from `docs/product/pcc-onboarding-flow.md` (“Your PCC access is ready — here’s how to start”) with the first CTA to log into `/app` and run a search. | Welcome email + modal + Dashboard quick search card. |
| 1 | Day‑1 email (3 searches that show PCC’s power) | Encourage a curated search list (friendly, risky, in‑pipeline). In-app, highlight the Quick Search card and the depth slider hero so they execute one of the suggested queries. | Email: “3 searches that show PCC's power.” In-app: quick search helper copy (see §5 below). |
| 2 | UI nudge in `/app` | Prompt them to explore Prospects: show a CTA on the Dashboard pointing to “View results from your latest search.” | Use insight cards from Dashboard + “Recent Activity” list to direct them to `/prospects`. |
| 3 | Day‑3 email | Variation depending on usage (power user vs. re-engagement). Encourage score breakdown exploration or re‑engagement. In-app, trigger the rich tooltip (`.score-tooltip`) by highlighting the Fit/Opportunity/ Priority badges. | Email: “Are you getting value yet?” In-app prompt to hover/click score chips with microcopy referencing tooltip content. |
| 4 | In-app milestone | After the first prospect is marked “Qualified” or exported, show a “Saved your first insight” toast referencing the detail panel buttons plus the “Export” and “Save as Campaign” CTAs. | Use detail panel quick actions to reinforce progress. |
| 5 | Usage warning email/prompt | If 80% of the post-trial scout quota has been used, send a warning email and show the alerts endpoint message in-app (per `usage.py`). | In-app: overlay pointing to `/billing` or `/upgrade` options; mention what upgrading unlocks (campaign automation, deeper depth tiers, more exports). |
| 6 | Reminder prompt | Prompt them to save a campaign (from the Search form “Save as Campaign” button) or run a bulk campaign so they see how repeating searches works. | Tie to saved campaigns list in Dashboard (top campaigns card). |
| 7 | Trial expiration notice | Send loss-aversion email on the morning of day 7/8 referencing the Reverse Trial plan from `docs/research/pcc-pricing-optimization-audit.md` (“Scale access expires tomorrow, keep command features for $149/mo as a Founding Member”). In-app, show a modal (from the Dashboard or `/app` nav) reminding them that the Scale tier drops to Scout in ~24 hours and linking to the upgrade path. | Combine email + in-app modal + CTA to `/billing/upgrade`. |

## 5. Recommended in-app prompts (all tied to existing `/app` components)
| Location | Prompt copy | Trigger & design | Purpose |
| --- | --- | --- | --- |
| Dashboard Quick Search card (`#quick-search-form`) | “Let’s find your first high-priority prospect — enter a business type & location and tap Find Prospects.” | Show on first login until `searches_used > 0`. Keep the button state green with the search icon. | Guides them into the primary discovery action without leaving the dashboard. |
| Search depth slider panel (`#depth-slider`, `#depth-details-toggle`) | “Standard depth gives you 20‑40 vetted prospects in < 15s. Slide to Deep once you need more.” Add a tooltip summarizing API calls/cost. | Persist for the first 3 searches while the slider is near Standard. | Teaches them the meaning of depth tiers so they choose the right mix of velocity vs coverage. |
| Search progress card (`#search-progress`) | “Looking up prospects now — you’ll get a full list, sorting, and exports when the bar finishes.” | Show the card immediately after submitting a search; keep progress details updated by the WebSocket. | Normalizes wait time and keeps them confident the search is running. |
| Prospects table (`#prospects-table-body`) | Inline banner above the table: “Click a prospect to see Fit + Opportunity, then copy their contact info.” Highlight the first row with a subtle pulse. | Banner appears until `openDetailPanel()` fires or 3 detail panels have been seen. | Moves them from “see the list” to “act on a single prospect.” |
| Detail panel quick actions (`#detail-panel` and `.detail-section button`) | “Mark this prospect Qualified or Contacted to add it to your pipeline.” Add a small reminder above the action buttons to copy phone/email. | Banner shows while the detail panel is open and disappears once a status update occurs. | Reinforces the pipeline behavior we want them to adopt during trial. |
| Prospects export controls (`Export` button + `#prospect-filter` area) | “Need these in your CRM? Export this list as CSV/JSON/Sheets or save it as a campaign.” | Unlocked after prospect list is non-empty. Add a tooltip linking to the Campaigns page. | Shows tangible output and ties it to billing value. |
| Campaigns page (`/campaigns` view) | “Saved searches turn into reusable campaigns. Run one whenever you want fresh prospects.” | Use the “Saved Campaigns” card + “New Campaign” button. Show after they click “Save as Campaign” once. | Demonstrates how to repeat the workflow without rebuilding queries every time. |

These prompts rely on existing DOM ids/classes in `/app` and can be implemented with small banners, tooltips, or conditional copy updates without rewriting the UI.
