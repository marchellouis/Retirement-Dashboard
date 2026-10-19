# RetireSmart 🌱

A mobile-friendly retirement calculator supporting AUD, IDR, and USD.

## Features
- Calculate minimum fixed monthly investment to retire at a chosen age.
- Calculate earliest sustainable whole-number retirement age for a fixed monthly contribution.
- Enter current invested savings, inflation, annual investment return, today's retirement spending, and expected lifespan.
- Compare lower/base/higher investment return assumptions (±2 percentage points).
- View charts, annual cash flows, and download CSV projections.

## Publish free with Streamlit Community Cloud
1. Create a GitHub repository.
2. Upload `app.py` and `requirements.txt` into the repository root.
3. Visit https://share.streamlit.io and sign in with GitHub.
4. Select the repository, branch, and `app.py` as the main file.
5. Deploy, then share the generated `.streamlit.app` URL.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Calculation notes
- Nominal annual return and inflation are converted to effective monthly rates.
- Existing savings are assumed invested at the beginning of the projection.
- Contributions are fixed in nominal currency and invested at the end of each working month.
- Withdrawals are made at the start of each retirement month, indexed from today's spending level.
- A retirement is feasible if the balance never becomes negative through the last month before the expected lifespan.
- Taxes, fees, pension income, currency conversion and return volatility are omitted.
- The return sensitivities are not probabilistic confidence intervals.
