# Prospect Command Center: Action Checklist

## Immediate Actions (Do Today)

### 1. Move the Project
```bash
mv "/Users/torrinkay/Desktop/Work/On Hold/Prospect Command Center" \
   "/Users/torrinkay/Desktop/Work/Prospect Command Center"
```
The folder name "On Hold" is a psychological anchor. Remove it.

### 2. Set Up Stripe (30 min)
- [ ] Go to https://dashboard.stripe.com
- [ ] Create account (if needed)
- [ ] Stay in TEST MODE
- [ ] Create 3 products:
  - Scout: $99/mo
  - Hunter: $149/mo (beta), $249/mo (regular)
  - Command: $499/mo
- [ ] Save API keys to `.env`

### 3. Start Your Prospect List (30 min)
Create a Google Sheet with these columns:
```
Name | Company | Email | LinkedIn | Source | Status | Notes
```

Add your first 10 names from memory:
- [ ] Anyone you know who runs an agency
- [ ] Anyone who works at an agency
- [ ] Anyone who might know agency owners

### 4. Ask for Intros (15 min)
Message 5 friends today:
```
Hey! I'm launching a SaaS tool for marketing agencies.
Looking for my first 10 beta customers. Know anyone who
runs an agency that does local business prospecting?
Would love an intro if you think they'd be a fit.
```

---

## This Week

### Development (Start Monday)

#### Day 1-2: User Model
```python
# prospect/web/database.py - Add User model

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String)
    company = Column(String)
    stripe_customer_id = Column(String)
    subscription_status = Column(String, default="none")
    tier = Column(String, default="scout")
    created_at = Column(DateTime, default=datetime.utcnow)

    prospects = relationship("Prospect", back_populates="user")
```

#### Day 3-4: Auth Endpoints
```python
# prospect/web/api/v1/auth.py

@router.post("/register")
@router.post("/login")
@router.post("/logout")
@router.post("/reset-password")
@router.get("/me")
```

#### Day 5: JWT Middleware
```python
# Add to all protected routes
from fastapi import Depends
from prospect.web.auth import get_current_user

@router.get("/prospects")
def list_prospects(user: User = Depends(get_current_user)):
    # Filter by user.id
    ...
```

### Outreach (Parallel to Dev)

- [ ] LinkedIn: Connect with 20 agency owners
- [ ] Email: Draft your cold email template
- [ ] Friends: Follow up on intro requests
- [ ] List: Add 30 more names to prospect sheet

---

## Week-by-Week Timeline

```
WEEK 1  ████████████████████  Auth + User Model
WEEK 2  ████████████████████  Stripe + Billing
WEEK 3  ████████████████████  Usage Metering + Limits
WEEK 4  ████████████████████  Onboarding + Polish + Deploy
        ░░░░░░░░░░░░░░░░░░░░  (Parallel: Build prospect list)

WEEK 5  ████████████████████  Warm Outreach + First Demos
WEEK 6  ████████████████████  Cold Outreach + More Demos
WEEK 7  ████████████████████  Pipeline Focus + Closes
WEEK 8  ████████████████████  Final Closes + Beta Full

        ════════════════════════════════════════════
        TARGET: 10 customers × $149/mo = $1,490 MRR
```

---

## Key Metrics to Track

### During Build (Weeks 1-4)
- [ ] Features completed vs planned
- [ ] Prospect list size (target: 100)
- [ ] Warm intros received (target: 15)

### During Launch (Weeks 5-8)
| Week | Outreach | Responses | Demos | Closes |
|------|----------|-----------|-------|--------|
| 5 | 50 | 10 | 5 | 1-2 |
| 6 | 80 | 15 | 7 | 2-3 |
| 7 | 50 | 10 | 5 | 3-4 |
| 8 | 20 | 5 | 3 | 2-3 |
| **Total** | **200** | **40** | **20** | **10** |

### During Beta (Weeks 9+)
- Daily: Who logged in? Anyone inactive 5+ days?
- Weekly: Total searches, active users, health scores
- Monthly: Feedback calls, NPS, deals attributed

---

## Demo Script (Memorize This)

```
1. DISCOVER (2 min)
   "How do you currently find new prospects?"
   "How many hours a week does that take?"

2. DEMO (8 min)
   "What vertical do you serve? Let me search that..."
   [Run live search]
   "See this? Opportunity score 78. No GA, no pixel,
    DIY WordPress. They NEED help."

3. CLOSE (5 min)
   "I'm taking 10 agencies as founding members.
    $149/mo locked forever - will be $249.
    In exchange: monthly feedback call, testimonial at 90 days.
    Want one of the spots?"
```

---

## Objection Responses (Memorize These)

| They Say | You Say |
|----------|---------|
| "Too expensive" | "One client from PCC pays for 2 years. What's a new client worth?" |
| "I use Apollo" | "Apollo gives contact data. PCC tells you WHO needs marketing help." |
| "I need to think" | "Totally fair. I've got X spots left. Can I follow up Friday?" |
| "12 months is long" | "It protects your rate - $149 forever vs $249. Worth it." |

---

## Files to Create

```
This Week:
├── prospect/web/api/v1/auth.py      ← User authentication
├── prospect/web/auth.py             ← JWT utilities
├── prospect/web/api/v1/billing.py   ← Stripe integration
├── prospect/web/api/v1/usage.py     ← Usage tracking

Assets:
├── Landing page (Carrd)
├── Prospect list (Google Sheet)
├── Metrics dashboard (Google Sheet)
├── Demo script (memorized)
├── Email templates (saved)
```

---

## Success = 10 × $149 = $1,490 MRR

That's it. Ten customers. Not a thousand. Not a hundred. Ten.

Every action should move you toward those 10 closes.

---

## Start Now

1. **Move the folder** (2 min)
2. **Create Stripe account** (10 min)
3. **Start prospect list** (20 min)
4. **Message 5 friends for intros** (10 min)
5. **Write first line of auth code** (start the momentum)

The software is 90% done. The launch is 0% done. Flip that ratio.
