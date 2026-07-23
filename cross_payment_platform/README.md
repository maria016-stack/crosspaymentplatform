# Cross Payment Platform

Tanzania Payment Intelligence System — an AI-powered dashboard that recommends
the best digital payment platform (M-PESA, Airtel Money, Mixx by Yas, Halo-Pesa,
TTCL Pesa, CRDB, NMB, NBC, AzamPay/Selcom, Bank Transfers) for any transaction,
based on a Random Forest success-prediction model and a Gradient Boosting
risk-flag model trained on a synthetic Tanzanian transactions dataset.

This implements the full stack shown in your Figma design: login page,
sidebar-navigation dashboard, new transaction flow, recommendations history,
analytics charts, platform comparison, industry/congestion details, settings,
and about/team page.

## Project structure

```
cross_payment_platform/
├── backend/
│   ├── main.py                # FastAPI app: pages + JSON API
│   ├── database.py            # SQLite persistence (users, settings, transactions)
│   ├── auth.py                 # Cookie-session authentication
│   ├── platforms.py            # Static platform reference data (fees, PRI inputs, peak hours)
│   ├── requirements.txt
│   ├── data/                   # synthetic_transactions.csv + app.db generated here at runtime
│   └── models/
│       ├── train_model.py      # Generates synthetic data + trains RF & GB models
│       └── recommender.py      # Loads trained models, computes PRI & recommendations
└── frontend/
    ├── templates/              # Jinja2 HTML templates (matches your Figma screens)
    └── static/
        ├── css/style.css       # Dark sidebar + light content theme, matches Figma
        └── js/app.js
```

## How to run it

1. **Install dependencies** (Python 3.10+ recommended):
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **(Optional) Pre-train the models.** This isn't required — the app will
   generate the synthetic dataset and train both models automatically the
   first time a recommendation is requested — but you can do it up front so
   the first request isn't slow:
   ```bash
   cd backend/models
   python train_model.py
   cd ..
   ```
   This prints accuracy/F1 for both models and saves `model_bundle.pkl`.

3. **Run the server:**
   ```bash
   cd backend
   python main.py
   ```
   or, equivalently:
   ```bash
   uvicorn main:app --reload
   ```

4. Open **http://localhost:8000** in your browser. You'll land on the login page.
   - **Continue with Email** → sign up with a username/password (real local
     account, stored in SQLite).
   - **Continue with Google** → a demo sign-in (creates/reuses a local
     "banzimaria007" account). Real Google Sign-In requires an OAuth client
     ID/secret from Google Cloud Console — swap the `/login/google-demo`
     route in `main.py` for a real OAuth flow (e.g. with `authlib`) once you
     have those credentials.

## How the recommendation engine works

- **Random Forest classifier** predicts the probability a transaction will
  **succeed** on a given platform, based on amount, transaction type,
  location, hour of day, and peak-time congestion.
- **Gradient Boosting classifier** predicts a **risk/fraud-flag** probability
  (mirrors the "fraud detection model" in your project notes — implemented
  with scikit-learn's `GradientBoostingClassifier` rather than XGBoost, so
  the project has no extra native-library dependency; swap in `xgboost` if
  you'd prefer to match that exactly).
- Both feed into the **Payment Reliability Index (PRI)**:
  `PRI = 0.40 × Success Rate + 0.30 × Efficiency + 0.20 × Speed + 0.10 × Cost`
- **Smart routing:** transactions above TZS 5,000,000 are automatically
  restricted to bank/aggregator platforms.
- **Peak-hour awareness:** the model factors in Tanzania's known congestion
  windows (07:30-09:30, 12:00-14:00, 17:00-20:30 EAT).

## Deploying

This is a standard FastAPI app, so it deploys the same way your earlier
FastAPI + Jinja2 backend did — e.g. to Render, Railway, or a VPS. Point the
start command at `uvicorn main:app --host 0.0.0.0 --port $PORT` from the
`backend/` directory, and set `APP_SECRET_KEY` as an environment variable in
production instead of relying on the default dev key in `auth.py`.

## Notes / things you may want to customize

- The synthetic dataset (20,500 rows) is regenerated fresh every time you
  delete `backend/data/synthetic_transactions.csv` and
  `backend/models/model_bundle.pkl` — useful if you want to tune the
  generation logic in `train_model.py` to better match your real project
  data or Gemini-generated dataset.
- Platform logos are currently emoji/color placeholders in `platforms.py`
  and the CSS — drop real logo image files into
  `frontend/static/img/` and reference them in the templates if you want
  the exact brand icons from your Figma file.
- The `/login/google-demo` route is a placeholder — see above for how to
  replace it with real Google OAuth.
