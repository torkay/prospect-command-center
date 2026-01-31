# Roadmap: Prospect Command Center

## Overview

Transform PCC from working MVP to monetization-ready beta. Start with security hardening to pass the "enterprise-ready" gate, then build the user experience layer (onboarding, score visibility) that makes the Opportunity Score value obvious. Follow with workflow features (pipeline, templates, tracking) that embed PCC into daily agency operations. Each phase delivers standalone value toward the $1,490 MRR founding member goal.

## Domain Expertise

None

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Production Hardening** - Fix security issues blocking beta launch ✓
- [ ] **Phase 2: Onboarding Experience** - Welcome modal, guided first search, score explanations
- [ ] **Phase 3: Score Visibility** - Expand opportunity notes, visual score breakdowns
- [ ] **Phase 4: Pipeline/CRM** - Prospect status, follow-ups, campaign assignment
- [ ] **Phase 5: Outreach Templates** - Email/phone scripts based on opportunity signals
- [ ] **Phase 6: ROI Tracking** - Deal attribution, cost-per-lead calculations

## Phase Details

### Phase 1: Production Hardening ✓
**Goal**: Fix critical security issues identified in codebase mapping - JWT secret fallback, Stripe env validation, missing imports
**Depends on**: Nothing (first phase)
**Research**: Unlikely (internal fixes, established patterns)
**Plans**: 1 (complete)

Completed:
- ✓ JWT_SECRET_KEY validation at startup (fails in production if missing)
- ✓ STRIPE_SECRET_KEY validation at startup (fails in production if missing)
- ✓ STRIPE_PRICE_* placeholder detection (fails in production with placeholder values)
- ✓ onboarding.py stub module created
- ✓ .env.example updated with all security-critical variables

### Phase 2: Onboarding Experience
**Goal**: Guide new users to first successful search and help them understand what makes a high-scoring prospect valuable
**Depends on**: Phase 1
**Research**: Unlikely (spec exists in docs/product/pcc-onboarding-flow.md)
**Plans**: TBD

Deliverables:
- Welcome modal with value proposition
- Guided first search flow
- Score explanation tooltips
- Empty state handling

### Phase 3: Score Visibility
**Goal**: Make Opportunity Score value immediately obvious by showing the "why" behind each score
**Depends on**: Phase 2
**Research**: Unlikely (internal UI patterns)
**Plans**: TBD

Deliverables:
- Expandable opportunity notes on prospect cards
- Visual score breakdown (what factors contributed)
- Score comparison view

### Phase 4: Pipeline/CRM
**Goal**: Enable agencies to track prospect status through their sales process within PCC
**Depends on**: Phase 3
**Research**: Unlikely (standard CRUD patterns)
**Plans**: TBD

Deliverables:
- Prospect status field (New, Contacted, Qualified, Won, Lost)
- Follow-up reminders
- Campaign/list assignment
- Pipeline view (Kanban or list)

### Phase 5: Outreach Templates
**Goal**: Provide ready-to-use outreach scripts personalized to each prospect's opportunity signals
**Depends on**: Phase 4
**Research**: Unlikely (internal template generation)
**Plans**: TBD

Deliverables:
- Email templates using prospect signals
- Phone script templates
- Template customization
- Copy-to-clipboard functionality

### Phase 6: ROI Tracking
**Goal**: Help agencies measure PCC's value by tracking deals won from PCC-sourced leads
**Depends on**: Phase 5
**Research**: Unlikely (internal calculations)
**Plans**: TBD

Deliverables:
- Mark prospect as "Deal Won" with value
- Cost-per-lead calculation
- ROI dashboard/summary
- Export for reporting

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Production Hardening | 1/1 | Complete | 2026-01-31 |
| 2. Onboarding Experience | 1/2 | In progress | - |
| 3. Score Visibility | 0/TBD | Not started | - |
| 4. Pipeline/CRM | 0/TBD | Not started | - |
| 5. Outreach Templates | 0/TBD | Not started | - |
| 6. ROI Tracking | 0/TBD | Not started | - |
