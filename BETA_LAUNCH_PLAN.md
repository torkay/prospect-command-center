# Prospect Command Center: Beta Launch Plan

> **Goal**: Launch paid beta to 10 marketing agencies at $149/mo
> **Target MRR**: $1,490
> **Timeline**: 8 weeks (4 weeks build + 4 weeks sell)

---

## Executive Summary

### Strategic Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Pricing Model** | Base fee + usage tiers | Aligns with value, recovers API costs |
| **Beta Price** | $149/mo (Hunter tier) | 40% off $249, locked forever |
| **Commitment** | 12 months | Ensures serious customers, protects rate |
| **Target Customers** | 10 founding agencies | Small enough to support personally |
| **Hosting** | Shared instance, user isolation | Simplest ops for beta |
| **Auth** | Email/password | Works for all agencies |
| **Billing** | Monthly only for beta | Flexibility to adjust |

### Key Metrics

| Metric | Target |
|--------|--------|
| Beta customers | 10 |
| MRR | $1,490 |
| Activation (first search <24hr) | 80% |
| Weekly active (after 30 days) | 60% |
| NPS | >40 |
| Churn | <10% monthly |

---

## Phase 1: Build (Weeks 1-4)

### Week 1: Authentication + Database

**Objective**: Users can register, login, and have isolated data

| Day | Task | Deliverable |
|-----|------|-------------|
| Mon | Design user model schema | SQL migration file |
| Mon | Add user table to database | `users` table with id, email, password_hash, created_at |
| Tue | Implement registration endpoint | `POST /api/v1/auth/register` |
| Tue | Implement login endpoint | `POST /api/v1/auth/login` returns JWT |
| Wed | Add JWT middleware | All routes protected by default |
| Wed | Link prospects to users | `user_id` foreign key on prospects table |
| Thu | Implement password reset flow | Email-based reset token |
| Thu | Session management | Token refresh, logout |
| Fri | Testing + bug fixes | All auth flows working |

**Technical Decisions**:
- Use `python-jose` for JWT
- Use `passlib` with bcrypt for password hashing
- Token expiry: 7 days (refresh on activity)
- Store user_id in JWT claims

### Week 2: Billing + Stripe Integration

**Objective**: Customers can subscribe and pay

| Day | Task | Deliverable |
|-----|------|-------------|
| Mon | Set up Stripe account | API keys, test mode |
| Mon | Create products in Stripe | Scout, Hunter, Command products |
| Mon | Create prices in Stripe | Monthly prices for each tier |
| Tue | Implement checkout session | `POST /api/v1/billing/checkout` |
| Tue | Build success/cancel pages | Redirect handling |
| Wed | Implement Stripe webhooks | `checkout.session.completed`, `invoice.paid`, `customer.subscription.deleted` |
| Wed | Store subscription status | `subscriptions` table, link to user |
| Thu | Build billing portal link | Customer can manage subscription |
| Thu | Handle failed payments | Webhook for `invoice.payment_failed` |
| Fri | Testing + bug fixes | Full payment flow working |

**Stripe Products to Create**:
```
Scout:   $99/mo  - 100 searches, 50 enrichments
Hunter:  $149/mo - 500 searches, 300 enrichments (BETA PRICE)
         $249/mo - (regular price, create but don't use yet)
Command: $499/mo - 2000 searches, 1500 enrichments
```

### Week 3: Usage Metering + Limits

**Objective**: Track usage and enforce tier limits

| Day | Task | Deliverable |
|-----|------|-------------|
| Mon | Design usage tracking schema | `usage_metrics` table |
| Mon | Implement search counter | Increment on each search |
| Tue | Implement enrichment counter | Increment on each enrichment |
| Tue | Monthly reset logic | Cron job or check on access |
| Wed | Display usage in dashboard | "47/500 searches used" |
| Wed | Usage API endpoint | `GET /api/v1/usage` |
| Thu | Implement limit enforcement | Block search when limit hit |
| Thu | Upgrade prompts | Show when near/at limit |
| Fri | Testing + edge cases | Limits work correctly |

**Usage Tracking Schema**:
```sql
CREATE TABLE usage_metrics (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    period_start DATE,
    period_end DATE,
    searches_used INTEGER DEFAULT 0,
    searches_limit INTEGER,
    enrichments_used INTEGER DEFAULT 0,
    enrichments_limit INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Week 4: Onboarding + Polish

**Objective**: Great first-run experience

| Day | Task | Deliverable |
|-----|------|-------------|
| Mon | Design onboarding flow | 3-step wizard mockup |
| Mon | Implement welcome modal | Shows on first login |
| Tue | Guided first search | Pre-filled example, tooltips |
| Tue | Explain scores | Tooltip on Fit/Opportunity/Priority |
| Wed | Empty states | Helpful messages when no data |
| Wed | Error messages | User-friendly, actionable |
| Thu | Email notifications | Search complete, weekly summary |
| Thu | Set up transactional email | SendGrid or Resend |
| Fri | Final testing | Full user journey works |
| Fri | Deploy to production | Railway production environment |

**Onboarding Steps**:
1. Welcome + value prop reminder
2. Run your first search (guided)
3. Understand the scores (interactive)
4. Take action on a prospect (pipeline)

---

## Phase 2: Prepare (Week 4, Parallel)

### Build Prospect List (While Coding)

**Target**: 100 qualified agency contacts

| Source | Target | Method |
|--------|--------|--------|
| Personal network | 10 | Manual list |
| Friend referrals | 15 | Ask 10 friends for intros |
| LinkedIn 1st connections | 15 | Filter for agency owners |
| LinkedIn Sales Navigator | 40 | Search + connect |
| Agency directories | 20 | Clutch, DesignRush scrape |

**Qualification Criteria**:
- Runs a marketing/digital agency
- 5-50 employees (not solo, not huge)
- Does local business work (not just enterprise)
- Active on LinkedIn (will see messages)

**Tracking Spreadsheet Columns**:
```
Name | Company | Email | LinkedIn | Source | Status | Last Contact | Notes
```

### Create Landing Page

**Tool**: Carrd ($19/year)

**Structure**:
```
HEADER: Prospect Command Center
SUBHEAD: Find local businesses that actually need your help

[Screenshot of scored prospects UI]

PROBLEM:
- Manual Google searching wastes hours
- No way to know who needs marketing help
- Spreadsheet chaos

SOLUTION:
- Automated discovery via Google
- Website enrichment (CMS, analytics, pixels)
- Opportunity scoring (who needs you?)

FOUNDING MEMBER PROGRAM
(Only 10 spots)

$149/mo forever (will be $249)
- 500 searches/month
- 300 enrichments/month
- Full opportunity scoring
- Direct founder access

[REQUEST DEMO BUTTON]

"X of 10 spots remaining"
```

**CTA**: Calendly link for 15-min demo

### Prepare Demo Flow

**Demo Script** (15 minutes):

```
0-2 min: Rapport
- "Thanks for taking the time"
- "Before I show you anything, quick question..."

2-5 min: Discovery
- "How do you currently find new prospects?"
- "How many hours a week does that take?"
- "What's frustrating about it?"

5-10 min: Live Demo
- "Let me show you something. What vertical do you serve?"
- [Run live search for their vertical + location]
- "See this prospect? Opportunity score 78. Here's why..."
- [Show opportunity notes: no GA, DIY WordPress, no booking]
- "This is someone who actually needs help"

10-12 min: Scores Deep Dive
- Explain Fit vs Opportunity vs Priority
- Show pipeline workflow
- Show export to Sheets

12-15 min: Close
- "I'm looking for 10 agencies as founding members"
- "$149/mo locked forever, normally $249"
- "In exchange: monthly feedback call, testimonial at 90 days"
- "Want one of the spots?"
```

### Prepare Outreach Templates

**LinkedIn Connection Request**:
```
Hey [Name] - saw you're running [Agency]. I'm building something
for agencies doing local business prospecting and looking for
feedback. Mind connecting?
```

**LinkedIn Message 1** (after accept):
```
Thanks for connecting! Quick q - when prospecting for new clients,
how do you currently find local businesses that might need help?
Manual Google? A tool? Referrals only?
```

**LinkedIn Message 2** (if they respond):
```
That's what I keep hearing. I built something that automates
discovery AND scores prospects on how much they need marketing
help (no analytics, DIY site, etc.).

Looking for 10 agencies as founding members - $149/mo locked
forever (will be $249). 15-min demo this week?
```

**Cold Email**:
```
Subject: Quick question about prospecting at [Agency]

Hey [Name],

I'll keep this short - I built a tool for agencies that prospect
local businesses.

It automates what most do manually:
→ Search Google for [industry] in [location]
→ Check each website for analytics, booking, etc.
→ Track in a spreadsheet

Instead, you get scored prospects showing WHO needs help.

Looking for 10 founding agencies at $149/mo (will be $249).
In exchange: 30-min onboarding, monthly feedback, testimonial.

15-min demo this week?

[Your name]
```

---

## Phase 3: Launch (Weeks 5-8)

### Week 5: Warm Outreach

| Day | Activity | Target |
|-----|----------|--------|
| Mon | Personal network messages | 10 sent |
| Mon | Request intros from friends | 10 friends asked |
| Tue | LinkedIn connections (warm) | 20 sent |
| Tue | Follow up on intro requests | 5+ intros |
| Wed | First demos (warm leads) | 2-3 demos |
| Thu | More warm demos | 2-3 demos |
| Fri | Cold LinkedIn batch 1 | 20 connections |

**Week 5 Targets**:
- Outreach: 50
- Responses: 10
- Demos: 5
- Closes: 1-2

### Week 6: Cold Outreach

| Day | Activity | Target |
|-----|----------|--------|
| Mon | LinkedIn follow-ups | 20 messages |
| Mon | Cold email batch 1 | 30 emails |
| Tue | Demos | 2-3 |
| Wed | LinkedIn connections batch 2 | 20 sent |
| Thu | Demos | 2-3 |
| Fri | Follow-ups + cold email batch 2 | 30 emails |

**Week 6 Targets**:
- Cumulative outreach: 130
- Cumulative responses: 25
- Cumulative demos: 12
- Cumulative closes: 4-5

### Week 7: Pipeline Focus

| Day | Activity | Target |
|-----|----------|--------|
| Mon | Follow up all open demos | 10+ follow-ups |
| Tue | Demos | 3-4 |
| Wed | Urgency messaging ("5 spots left") | All pipeline |
| Thu | Demos + closes | 2-3 closes |
| Fri | More outreach if needed | Top up pipeline |

**Week 7 Targets**:
- Cumulative demos: 18
- Cumulative closes: 7-8

### Week 8: Close Out

| Day | Activity | Target |
|-----|----------|--------|
| Mon | Final demos | 2-3 |
| Tue | "Last 2 spots" messaging | All pipeline |
| Wed | Close remaining spots | 2-3 closes |
| Thu | Onboarding calls for new customers | 3-4 calls |
| Fri | Announce "Beta Full" | Close program |

**Week 8 Targets**:
- Total demos: 20+
- Total closes: 10
- MRR: $1,490

---

## Phase 4: Operate (Weeks 9+)

### Daily Tasks

```
□ Check dashboard for inactive users (5+ days)
□ Respond to any support requests (<2 hours)
□ Monitor health scores, act on <60
```

### Weekly Tasks

```
□ Review usage metrics (Mon)
□ Send weekly summary to yourself (Mon)
□ Check-in with at-risk customers (Tue)
□ Review pipeline actions across all customers (Fri)
```

### Monthly Tasks

```
□ Conduct feedback calls with all 10 customers
□ Update health scores from call sentiment
□ Collect NPS scores
□ Ask for testimonials (day 90+)
□ Capture deals attributed to PCC
□ Update ROI case study data
```

### Feedback Call Schedule

| Customer | Onboarding | Month 1 | Month 2 | Month 3 |
|----------|------------|---------|---------|---------|
| Customer 1 | Week 5 | Week 9 | Week 13 | Week 17 |
| Customer 2 | Week 5 | Week 9 | Week 13 | Week 17 |
| ... | ... | ... | ... | ... |

---

## Success Criteria

### Beta Success (90 days)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Customers retained | 10/10 | Billing status |
| Weekly active rate | 60%+ | Login data |
| Avg searches/customer/mo | 50+ | Usage metrics |
| Deals attributed | 10+ total | Feedback calls |
| NPS | >40 | Monthly survey |
| Testimonials | 5+ written, 3+ video | Collected |
| Case study | 1 with ROI numbers | Written |

### Ready for Public Launch

```
□ 90-day retention proven (10/10 customers)
□ Product stable (no major bugs for 30 days)
□ Billing system smooth (no payment issues)
□ Usage metering accurate
□ 5+ testimonials collected
□ 1+ case study with ROI
□ Waitlist of 20+ interested agencies
□ Pricing validated ($249 accepted)
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Can't find 10 customers | Start outreach in Week 4, parallel to dev |
| High churn after month 1 | Weekly health checks, proactive outreach |
| Product bugs hurt retention | Prioritize stability over features |
| SerpAPI costs too high | Monitor closely, set hard limits |
| Customer doesn't see value | Monthly calls, help them win deals |

---

## Budget

### One-Time Costs

| Item | Cost |
|------|------|
| Carrd landing page | $19/year |
| Stripe setup | Free |
| SendGrid (transactional email) | Free tier |
| Calendly (scheduling) | Free tier |
| **Total** | **~$20** |

### Monthly Costs (at 10 customers)

| Item | Cost |
|------|------|
| Railway hosting | ~$20-50 |
| SerpAPI | ~$50-100 (usage-based) |
| SendGrid | Free tier |
| **Total** | **~$70-150** |

### Revenue vs Cost

| Metric | Value |
|--------|-------|
| MRR | $1,490 |
| Monthly costs | ~$100 |
| **Gross profit** | **~$1,390** |
| **Gross margin** | **~93%** |

---

## Quick Reference

### Key Links (To Create)

```
Landing page:     [carrd URL]
Demo scheduling:  [calendly URL]
Stripe dashboard: https://dashboard.stripe.com
Railway:          https://railway.app
Prospect list:    [Google Sheet URL]
Metrics dashboard:[Google Sheet URL]
```

### Key Contacts

```
First 10 beta targets:
1. [Name] - [Agency] - [Status]
2. [Name] - [Agency] - [Status]
...
```

### Emergency Playbook

| Situation | Action |
|-----------|--------|
| Customer can't login | Check JWT, reset password manually |
| Billing failed | Check Stripe, contact customer |
| Search not working | Check SerpAPI quota and status |
| Customer angry | Founder call within 2 hours |
| Churn request | Offer pause, understand why, save if possible |

---

## Appendix: File Locations

```
/prospect-command-center
├── BETA_LAUNCH_PLAN.md      ← This file
├── prospect/
│   ├── web/
│   │   ├── api/v1/
│   │   │   ├── auth.py      ← To create (Week 1)
│   │   │   ├── billing.py   ← To create (Week 2)
│   │   │   └── usage.py     ← To create (Week 3)
│   │   └── ...
│   └── ...
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API.md
│   └── ...
└── ...
```

---

## Next Actions (Start Here)

### This Week

1. [ ] Move project out of "On Hold" folder
2. [ ] Set up Stripe account (test mode)
3. [ ] Create user authentication schema
4. [ ] Build personal network prospect list (10 names)
5. [ ] Ask 5 friends for agency intros

### First Commit

```bash
git checkout -b feature/beta-launch
# Start with auth implementation
```

---

*Last updated: [Date]*
*Plan version: 1.0*
