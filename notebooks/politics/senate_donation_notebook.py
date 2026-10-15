import marimo

app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import requests
    return mo, pd, requests


@app.cell
def _(mo):
    mo.md(r"""
    # Senate donation targeting, 2026
    Ranks non-Republican Senate candidates by **need** (cash gap vs. the Republican)
    and **winnability** (race closeness). Inputs you must verify and edit:
    `races` (ratings/poll margin) below. Cash figures come live from the OpenFEC API.

    Score = closeness x need, where
    - closeness = 1 - |margin|/15, clipped to 0..1 (margin = Dem minus Rep, points)
    - need = share of the two candidates' combined cash that the Republican holds,
      scaled so a 50/50 split scores 0.5.
    """)
    return


@app.cell
def _(mo):
    api_key = mo.ui.text(value="DEMO_KEY", label="OpenFEC API key (api.data.gov)")
    api_key
    return (api_key,)


@app.cell
def _(pd):
    # EDIT: poll_margin = Dem/non-Rep minus Rep (points) from a poll average you trust.
    # Leave NaN if unknown; rating is a fallback (see RATING_MARGIN).
    # fec_dem / fec_rep: FEC candidate IDs (find at fec.gov/data/candidates/senate).
    races = pd.DataFrame([
        {"state": "OH", "dem": "Sherrod Brown",  "rating": "Toss Up", "poll_margin": float("nan"), "fec_dem": "", "fec_rep": ""},
        {"state": "MI", "dem": "Abdul El-Sayed", "rating": "Toss Up", "poll_margin": float("nan"), "fec_dem": "", "fec_rep": ""},
        {"state": "IA", "dem": "Josh Turek",     "rating": "Lean R",  "poll_margin": float("nan"), "fec_dem": "", "fec_rep": ""},
        {"state": "TX", "dem": "James Talarico", "rating": "Lean R",  "poll_margin": float("nan"), "fec_dem": "", "fec_rep": ""},
        {"state": "GA", "dem": "Jon Ossoff",     "rating": "Lean D",  "poll_margin": float("nan"), "fec_dem": "", "fec_rep": ""},
    ])
    RATING_MARGIN = {"Solid D": 20, "Likely D": 10, "Lean D": 5, "Toss Up": 0,
                     "Lean R": -5, "Likely R": -10, "Solid R": -20}
    return RATING_MARGIN, races


@app.cell
def _(api_key, pd, requests):
    BASE = "https://api.open.fec.gov/v1"

    def cash_on_hand(cid, cycle=2026):
        if not cid:
            return float("nan")
        r = requests.get(f"{BASE}/candidate/{cid}/totals/",
                         params={"api_key": api_key.value, "cycle": cycle}, timeout=30)
        r.raise_for_status()
        res = r.json().get("results", [])
        return res[0].get("cash_on_hand_end_period", float("nan")) if res else float("nan")

    def find_candidate(name, state):
        r = requests.get(f"{BASE}/candidates/search/",
                         params={"api_key": api_key.value, "q": name, "state": state,
                                 "office": "S", "cycle": 2026}, timeout=30)
        r.raise_for_status()
        return pd.DataFrame(r.json().get("results", []))[["candidate_id", "name", "party"]]
    return cash_on_hand, find_candidate


@app.cell
def _(RATING_MARGIN, cash_on_hand, pd, races):
    def score(df):
        d = df.copy()
        d["dem_cash"] = d["fec_dem"].map(cash_on_hand)
        d["rep_cash"] = d["fec_rep"].map(cash_on_hand)
        d["margin"] = d["poll_margin"].fillna(d["rating"].map(RATING_MARGIN))
        d["closeness"] = (1 - d["margin"].abs() / 15).clip(0, 1)
        tot = d["dem_cash"] + d["rep_cash"]
        d["need"] = (d["rep_cash"] / tot).where(tot > 0)
        d["score"] = d["closeness"] * d["need"]
        return d.sort_values("score", ascending=False)

    ranked = score(races)
    ranked
    return ranked, score


@app.cell
def _(mo):
    mo.md(r"""
    ## Caveats
    - FEC cash lags (quarterly; Q3 report due Oct 15) and ignores outside spending (super PACs).
    - Closeness uses a crude linear rule; replace with a calibrated model if desired.
    - Individual limit: $3,500 per election per candidate; designate the general election.
    - Look up IDs with `find_candidate("Name", "OH")`.
    """)
    return


if __name__ == "__main__":
    app.run()
