"""
Static reference data for all payment platforms supported by the
Cross Payment Platform. These baseline stats are used both to generate
the synthetic training dataset and to compute the Payment Reliability
Index (PRI) shown throughout the dashboard.

PRI formula (matches the dashboard's "Our Technology" panel):
    PRI = 0.40 * success_rate + 0.30 * efficiency + 0.20 * speed_score + 0.10 * cost_score
"""

PLATFORMS = {
    "M-PESA": {
        "network": "Vodacom",
        "category": "mobile",
        "base_success_rate": 98.6,
        "base_speed_seconds": 15,
        "fee_percent": 0.0066,   # ~330 TZS on 50,000
        "min_fee": 200,
        "max_fee": 7000,
        "logo": "mpesa.png",
        "color": "#e53935",
    },
    "Airtel Money": {
        "network": "Airtel",
        "category": "mobile",
        "base_success_rate": 96.9,
        "base_speed_seconds": 20,
        "fee_percent": 0.007,
        "min_fee": 200,
        "max_fee": 7000,
        "logo": "airtelmoney.png",
        "color": "#e30613",
    },
    "Mixx by Yas": {
        "network": "Tigo/Yas",
        "category": "mobile",
        "base_success_rate": 97.4,
        "base_speed_seconds": 18,
        "fee_percent": 0.0068,
        "min_fee": 200,
        "max_fee": 7000,
        "logo": "mixxbyyas.png",
        "color": "#004b93",
    },
    "Halo-Pesa": {
        "network": "Halotel",
        "category": "mobile",
        "base_success_rate": 95.1,
        "base_speed_seconds": 22,
        "fee_percent": 0.0072,
        "min_fee": 200,
        "max_fee": 7000,
        "logo": "halopesa.png",
        "color": "#f36f21",
    },
    "TTCL Pesa": {
        "network": "TTCL",
        "category": "mobile",
        "base_success_rate": 94.3,
        "base_speed_seconds": 24,
        "fee_percent": 0.0075,
        "min_fee": 200,
        "max_fee": 7000,
        "logo": "ttcl.png",
        "color": "#111111",
    },
    "CRDB Bank": {
        "network": "CRDB",
        "category": "bank",
        "base_success_rate": 99.1,
        "base_speed_seconds": 25,
        "fee_percent": 0.004,
        "min_fee": 1000,
        "max_fee": 15000,
        "logo": "crdb.png",
        "color": "#1b2b5b",
    },
    "NMB Bank": {
        "network": "NMB",
        "category": "bank",
        "base_success_rate": 98.3,
        "base_speed_seconds": 27,
        "fee_percent": 0.0042,
        "min_fee": 1000,
        "max_fee": 15000,
        "logo": "nmb.png",
        "color": "#f7941d",
    },
    "NBC Bank": {
        "network": "NBC",
        "category": "bank",
        "base_success_rate": 97.6,
        "base_speed_seconds": 28,
        "fee_percent": 0.0044,
        "min_fee": 1000,
        "max_fee": 15000,
        "logo": "nbc.png",
        "color": "#004a99",
    },
    "AzamPay/Selcom": {
        "network": "AzamPay/Selcom",
        "category": "aggregator",
        "base_success_rate": 96.2,
        "base_speed_seconds": 20,
        "fee_percent": 0.006,
        "min_fee": 300,
        "max_fee": 9000,
        "logo": "azampesa.png",
        "color": "#00a651",
    },
    "Bank Transfers (TIPS/EFT)": {
        "network": "TIPS/EFT",
        "category": "bank",
        "base_success_rate": 98.9,
        "base_speed_seconds": 45,
        "fee_percent": 0.002,
        "min_fee": 1500,
        "max_fee": 20000,
        "logo": "",
        "color": "#6a1b9a",
    },
}

TRANSACTION_TYPES = [
    "Mobile Money Transfer",
    "Merchant Payment",
    "Bill Payment",
    "Bank Transfer",
    "Airtime/Bundles",
    "Salary Payment",
]

LOCATIONS = [
    "Dar es Salaam", "Dodoma", "Arusha", "Mwanza", "Mbeya",
    "Morogoro", "Tanga", "Zanzibar", "Kigoma", "Iringa",
]

PEAK_HOURS = [
    {"platform": "Mobile Money (All Networks)", "hours": "07:30-09:00", "reason": "Salary commuters, transport payments, school fees"},
    {"platform": "M-PESA", "hours": "08:00-09:30, 12:00-14:00", "reason": "Morning merchant payments; lunch-time business payments"},
    {"platform": "M-PESA (Evening)", "hours": "17:00-20:30", "reason": "Highest daily load after work - primary peak-time alert window"},
    {"platform": "Airtel Money", "hours": "08:00-09:00, 17:30-20:00", "reason": "Morning transfers; evening cash transfers"},
    {"platform": "Mixx by Yas", "hours": "08:00-09:00, 17:00-20:00", "reason": "Morning business transactions; historical instability during heavy evening demand"},
    {"platform": "Halo-Pesa", "hours": "12:00-14:00, 17:00-19:30", "reason": "Moderate lunchtime usage; evening transfers"},
    {"platform": "CRDB Bank", "hours": "08:00-10:00, 16:30-18:30", "reason": "Business opening hours; corporate payment batches"},
    {"platform": "NMB Bank", "hours": "08:00-10:00, 17:00-19:00", "reason": "Morning banking; after-work banking"},
    {"platform": "NBC Bank", "hours": "08:00-10:00", "reason": "Corporate and retail activity"},
    {"platform": "AzamPay/Selcom", "hours": "11:30-14:00, 12:00-14:00", "reason": "Merchant collections and payment processing"},
    {"platform": "Bank Transfers (TIPS/EFT)", "hours": "09:00-11:00, 15:00-17:00", "reason": "Business settlements; end-of-day settlement batches"},
]

CONGESTION_WINDOWS = [
    {"window": "22:00-06:00", "level": 20, "label": "Low"},
    {"window": "06:00-07:30", "level": 45, "label": "Low"},
    {"window": "07:30-09:00", "level": 80, "label": "High"},
    {"window": "09:00-12:00", "level": 55, "label": "Moderate"},
    {"window": "12:00-14:00", "level": 78, "label": "High"},
    {"window": "14:00-17:00", "level": 50, "label": "Moderate"},
    {"window": "17:00-20:30", "level": 96, "label": "Very High"},
    {"window": "20:30-22:00", "level": 40, "label": "Low"},
]

SMART_ROUTING_THRESHOLD = 5_000_000  # TZS - above this, auto-route to bank transfer platforms

# Which platform categories are eligible for each transaction type. This is
# what keeps "Bank Transfer" from recommending mobile-money platforms (and
# vice versa). Types not listed here are unrestricted (any category can be
# recommended) because they're plausibly served by either rail.
TRANSACTION_TYPE_CATEGORIES = {
    "Bank Transfer": ("bank",),
    "Salary Payment": ("bank", "aggregator"),
    "Mobile Money Transfer": ("mobile",),
    "Airtime/Bundles": ("mobile",),
    # "Merchant Payment" and "Bill Payment" are left unrestricted on purpose -
    # both rails commonly serve these in practice.
}

# Approximate Tanzania mobile-money market share (illustrative/demo figures,
# loosely reflecting M-Pesa/Vodacom's well-known lead in the market).
MARKET_SHARE = {
    "M-PESA": 47,
    "Airtel Money": 27,
    "Mixx by Yas": 13,
    "Halo-Pesa": 5,
    "TTCL Pesa": 2,
    "CRDB Bank": 2,
    "NMB Bank": 2,
    "NBC Bank": 1,
    "AzamPay/Selcom": 1,
    "Bank Transfers (TIPS/EFT)": 0,
}

# Demo platform-wide counters shown on the dashboard header stats (not tied
# to any single user - illustrative baseline for the "happy users" style
# metrics seen on the live Figma prototype).
PLATFORM_BASE_STATS = {
    "total_transactions_baseline": 1500,
    "happy_users_baseline": 843,
}


def current_traffic_period(hour: int):
    """Return the congestion window description covering the given hour."""
    windows = [
        (22, 6, "Low", "Minimal network congestion. Ideal time for large or batch transactions. All platforms operating at full capacity.", "22:00-06:00"),
        (6, 7, "Low", "Minimal network congestion. Ideal time for large or batch transactions. All platforms operating at full capacity.", "06:00-07:00"),
        (7, 9, "High", "Morning rush - salary commuters and merchant payments driving heavy traffic.", "07:00-09:00"),
        (9, 12, "Moderate", "Steady daytime activity across most platforms.", "09:00-12:00"),
        (12, 14, "High", "Lunch-hour merchant and business payments surging.", "12:00-14:00"),
        (14, 17, "Moderate", "Steady afternoon activity across most platforms.", "14:00-17:00"),
        (17, 20, "Very High", "Highest daily load after work hours - expect slower confirmations on some platforms.", "17:00-20:00"),
        (20, 22, "Low", "Traffic easing after the evening peak.", "20:00-22:00"),
    ]
    for start, end, level, reason, label in windows:
        if start <= end:
            if start <= hour < end:
                return {"level": level, "reason": reason, "window": label}
        else:  # wraps past midnight
            if hour >= start or hour < end:
                return {"level": level, "reason": reason, "window": label}
    return {"level": "Moderate", "reason": "Typical activity levels.", "window": ""}
