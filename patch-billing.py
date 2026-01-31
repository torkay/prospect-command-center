import re

# Read the file
with open("prospect/web/api/v1/billing.py", "r") as f:
    content = f.read()

# Replace the TIER_PRICES with env-based version
old_tier_prices = TIER_PRICES = {