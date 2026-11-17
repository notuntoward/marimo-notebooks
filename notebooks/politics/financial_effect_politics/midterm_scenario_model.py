# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "altair>=6.3.0",
#     "arch==8.0.0",
#     "marimo>=0.23.3",
#     "matplotlib==3.11.2",
#     "numpy==2.5.4",
#     "pandas==3.1.0",
#     "scipy==1.18.1",
#     "tabulate==0.10.0",
# ]
# ///

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _():
    import urllib.request
    import json
    import time
    import os
    import datetime as dt

    import numpy as np
    import pandas as pd
    import scipy.stats as st

    import altair as alt

    import warnings

    warnings.filterwarnings("ignore")

    HORIZON = 42  # trading days, roughly 2 months
    return HORIZON, alt, dt, json, np, os, pd, st, time, urllib


@app.cell
def _(dt, json, os, pd, time, urllib):
    # --- Download daily S&P 500 closes from Yahoo Finance ---------------------
    # Cached to gspc_daily.csv so the notebook stays reproducible across runs.

    _DATA_URL = (
        "https://query2.finance.yahoo.com/v8/finance/chart/%5EGSPC"
        "?period1=-631152000"
        f"&period2={int(time.time())}"
        "&interval=1d"
    )
    _LOCAL_CACHE = "gspc_daily.csv"

    def _fetch_gspc():
        req = urllib.request.Request(
            _DATA_URL,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
        result = json.loads(raw)["chart"]["result"][0]
        ts = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]
        df = pd.DataFrame(
            {
                "date": [
                    (
                        dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
                        + dt.timedelta(seconds=t)
                    ).date()
                    for t in ts
                ],
                "close": closes,
            }
        )
        df = df.dropna(subset=["close"]).reset_index(drop=True)
        df["date"] = pd.to_datetime(df["date"])
        return df

    if os.path.exists(_LOCAL_CACHE):
        prices = pd.read_csv(_LOCAL_CACHE, parse_dates=["date"])
        src_note = (
            f"Loaded cached {len(prices)} rows from "
            f"{prices.date.iloc[0].date()} to {prices.date.iloc[-1].date()}."
        )
    else:
        prices = _fetch_gspc()
        prices.to_csv(_LOCAL_CACHE, index=False)
        src_note = (
            f"Downloaded {len(prices)} daily closes from "
            f"{prices.date.iloc[0].date()} to {prices.date.iloc[-1].date()} "
            f"and cached to {_LOCAL_CACHE}."
        )
    return prices, src_note


@app.cell
def _(mo, src_note):
    mo.md("# Post-midterm S&P 500 scenario model")
    mo.md(src_note)
    mo.md("""
    We model the S&P 500 percentage gain in the 42 trading days (~2 months) after
    a midterm election, anchored at the close one trading day before election day.
    Daily data source: Yahoo Finance `^GSPC` daily closes.
    """)
    return


@app.cell
def _(np, prices):
    # --- Daily log returns ---------------------------------------------------
    prices_ret = prices.sort_values("date").reset_index(drop=True)
    prices_ret["log_ret"] = np.log(prices_ret["close"] / prices_ret["close"].shift(1))
    returns = prices_ret.dropna(subset=["log_ret"]).reset_index(drop=True)
    return prices_ret, returns


@app.cell
def _(mo, np, prices_ret, returns):
    mo.md(f"""
    - Rows: **{len(prices_ret)}** daily bars, **{len(returns)}** daily log returns.
    - Range: **{prices_ret.date.iloc[0].date()}** to **{prices_ret.date.iloc[-1].date()}**.
    - Sample mean daily log return: **{returns.log_ret.mean():.6f}**
      (≈ **{returns.log_ret.mean() * 252 * 100:.2f}%** annualized).
    - Sample daily volatility: **{returns.log_ret.std():.6f}**
      (≈ **{returns.log_ret.std() * np.sqrt(252) * 100:.1f}%** annualized).
    """)
    return


@app.cell
def _(pd):
    # --- Midterm election dates ----------------------------------------------
    _MIDTERM_YEARS = [y for y in range(1950, 2023, 2) if y % 4 != 0]

    def _first_tuesday_after_first_monday(year: int):
        nov1 = pd.Timestamp(year=year, month=11, day=1)
        offset_to_monday = (0 - nov1.dayofweek) % 7
        first_monday = nov1 + pd.Timedelta(days=offset_to_monday)
        tuesday_offset = (1 - first_monday.dayofweek) % 7
        return first_monday + pd.Timedelta(days=tuesday_offset)

    ELECTION_DATES = {
        y: _first_tuesday_after_first_monday(y) for y in _MIDTERM_YEARS
    }
    MIDTERM_YEARS = _MIDTERM_YEARS
    return (ELECTION_DATES,)


@app.cell
def _(ELECTION_DATES, mo, pd):
    _rows = [
        {"year": y, "election_date": d.date()} for y, d in ELECTION_DATES.items()
    ]
    mo.md(pd.DataFrame(_rows).to_markdown(index=False))
    return


@app.cell
def _(ELECTION_DATES, HORIZON, mo, np, pd, prices_ret):
    # --- Build 42-trading-day post-election windows ---------------------------

    _windows = []
    for _year, _election_date in ELECTION_DATES.items():
        _pre_mask = prices_ret["date"] < _election_date
        if _pre_mask.sum() == 0:
            continue
        _anchor_idx = prices_ret.index[_pre_mask][-1]
        _end_idx = _anchor_idx + HORIZON
        if _end_idx >= len(prices_ret):
            continue
        _sub = prices_ret.loc[_anchor_idx:_end_idx].copy()
        _sub["t"] = np.arange(len(_sub))
        _sub.loc[_anchor_idx, "log_ret"] = 0.0
        _sub["cum_log_ret"] = _sub["log_ret"].cumsum()
        _sub["year"] = _year
        _windows.append(_sub)

    window_df = pd.concat(_windows, ignore_index=True)
    mo.md(
        f"Built **{len(_windows)}** post-election windows of {HORIZON + 1} trading days each."
    )
    return (window_df,)


@app.cell
def _(window_df):
    paths_wide = window_df.pivot(index="year", columns="t", values="cum_log_ret")
    return (paths_wide,)


@app.cell
def _(alt, np, paths_wide, pd):
    # Historical fan of cumulative percentage gain
    _pct_paths = np.exp(paths_wide.values) - 1
    _historical = pd.DataFrame(_pct_paths * 100, index=paths_wide.index, columns=paths_wide.columns)
    _historical.index.name = "year"
    _plot_data = _historical.reset_index().melt(
        id_vars="year", var_name="day", value_name="gain_pct"
    )
    _plot_data["day"] = pd.to_numeric(_plot_data["day"])

    _paths = alt.Chart(_plot_data).mark_line(opacity=0.55).encode(
        x=alt.X("day:Q", title="Trading days after (election day − 1)"),
        y=alt.Y("gain_pct:Q", title="Cumulative percentage gain (%)"),
        color=alt.Color("year:N", title="Midterm year", scale=alt.Scale(scheme="tableau20")),
        tooltip=["year:N", "day:Q", alt.Tooltip("gain_pct:Q", format=".2f")],
    )
    _zero = alt.Chart(pd.DataFrame({"gain_pct": [0]})).mark_rule(color="black", strokeWidth=1).encode(
        y="gain_pct:Q"
    )
    alt.layer(_paths, _zero).properties(
        title="Historical 2-month post-midterm paths (S&P 500 price index)",
        width=800,
        height=420,
    ).interactive()
    return


@app.cell
def _(mo):
    mo.md("## Volatility model (t-EGARCH)")
    mo.md("""
    We fit a t-EGARCH(1,1) on daily log returns (in percent) to get a conditional
    volatility σ_t for every day. This σ_t is used to standardize the election
    windows and to calibrate the simulation.
    """)
    return


@app.cell
def _(mo):
    _arch_msg = None
    try:
        from arch import arch_model
    except ImportError:
        arch_model = None
        _arch_msg = mo.md("""
        `arch` is not installed. Install with `pip install arch`.
        Falling back to EWMA(λ=0.94) conditional volatility.
        """)
    else:
        _arch_msg = mo.md("Using `arch` to fit a t-EGARCH(1,1) model on daily log returns.")
    return (arch_model,)


@app.cell
def _(arch_model, mo, np, returns):
    if arch_model is not None:
        _am = arch_model(
            returns["log_ret"] * 100.0,
            mean="Constant",
            vol="EGARCH",
            p=1,
            q=1,
            dist="t",
        )
        fit = _am.fit(disp="off")
        _cond_vol = fit.conditional_volatility.values / 100.0
        summary_str = str(fit.summary())
        model_used = "t-EGARCH(1,1)"
    else:
        _lam = 0.94
        _sq = (returns["log_ret"] ** 2).values
        _var = np.empty_like(_sq)
        _var[0] = _sq[0]
        for _j in range(1, len(_sq)):
            _var[_j] = _lam * _var[_j - 1] + (1 - _lam) * _sq[_j - 1]
        _cond_vol = np.sqrt(_var)
        fit = None
        summary_str = None
        model_used = "EWMA(λ=0.94)"

    returns_vol = returns.copy()
    returns_vol["cond_vol"] = _cond_vol
    returns_vol["z"] = returns_vol["log_ret"] / returns_vol["cond_vol"]

    mo.md(f"Volatility model used: **{model_used}**.")
    if fit is not None:
        _fit_md = mo.md(f"```\n{summary_str}\n```")
    else:
        _fit_md = None
    return (returns_vol,)


@app.cell
def _(mo, returns_vol, st):
    # Diagnostics on standardized residuals
    _z = returns_vol["z"].dropna()
    _jb_p = st.jarque_bera(_z).pvalue
    _ks_p = st.kstest(_z, "norm").pvalue

    mo.md(f"""
    Standardized residuals:
    - N = **{len(_z)}**, mean = **{_z.mean():.4f}**, std = **{_z.std():.4f}**
    - Jarque-Bera p = **{_jb_p:.3g}** (small → fat tails present)
    - KS vs N(0,1) p = **{_ks_p:.3g}**
    """)
    return


@app.cell
def _(mo, returns_vol, window_df):
    # --- Standardize each election window by its conditional volatility --------
    _vol_by_date = returns_vol.set_index("date")["cond_vol"]

    def _lookup_vol(d):
        _idx = _vol_by_date.index.searchsorted(d, side="right") - 1
        if _idx < 0:
            return float("nan")
        return _vol_by_date.iloc[_idx]

    window_df_std = window_df.copy()
    window_df_std["cond_vol"] = window_df_std["date"].map(_lookup_vol)
    window_df_std["z"] = window_df_std["log_ret"] / window_df_std["cond_vol"]

    mo.md(f"Missing cond_vol rows: **{int(window_df_std['cond_vol'].isna().sum())}**")
    return (window_df_std,)


@app.cell
def _(window_df_std):
    z_daily_wide = window_df_std.pivot(index="year", columns="t", values="z")
    z_wide = z_daily_wide.cumsum(axis=1)
    r_wide = window_df_std.pivot(index="year", columns="t", values="log_ret").cumsum(axis=1)
    return r_wide, z_daily_wide, z_wide


@app.cell
def _(mo, np, pd, returns_vol, window_df_std, z_wide):
    # Pre-election 21-day average σ_t for each year
    _pre_vol = {}
    for _yr in z_wide.index:
        _anchor_date = window_df_std.loc[
            (window_df_std["year"] == _yr) & (window_df_std["t"] == 0), "date"
        ].iloc[0]
        _pre_vols = returns_vol.loc[
            returns_vol["date"] <= _anchor_date, "cond_vol"
        ].tail(21)
        _pre_vol[_yr] = _pre_vols.mean()
    pre_vol = pd.Series(_pre_vol)

    mo.md(f"""
    - **{len(z_wide)}** windows.
    - Median pre-election daily vol (21-day avg of σ_t):
      **{pre_vol.median() * np.sqrt(252) * 100:.1f}%** annualized.
    - Range across years:
      **{pre_vol.min() * np.sqrt(252) * 100:.1f}%** to
      **{pre_vol.max() * np.sqrt(252) * 100:.1f}%**.
    """)
    return (pre_vol,)


@app.cell
def _(mo):
    mo.md("## Scenario and quantile model")
    mo.md("""
    Target: the cumulative standardized return \\(C_k = \\sum_{t\\le k} z_t\\) over the
    42-day window. Two sample variants:

    1. **From 1950** – all midterms in the data.
    2. **From 1973** – only windows since the 1973–74 bear-market era, which
       excludes the Bretton-Woods / fixed-exchange-rate period.

    The per-year drift is resampled from the empirical distribution of
    historical per-year drifts (a nonparametric hierarchical prior). Daily
    innovations are resampled from the pooled standardized-residual pool, which
    preserves fat tails and volatility clustering within a window.

    Conversion back to percentage gain:
    \\( \\text{gain}_k = \\exp(\\sigma_{\\text{pre}} \\cdot C_k) - 1 \\),
    with \\(\\sigma_{\\text{pre}}\\) drawn from the historical pre-election vol distribution.
    """)
    return


@app.cell
def _(z_daily_wide):
    def fit_variant(start_year: int):
        _sub = z_daily_wide[z_daily_wide.index >= start_year]
        _years = _sub.index.values
        _n_years = len(_years)
        # per-year drift = mean of DAILY z (t=1..HORIZON), not cumulative
        _per_year_drift = _sub.values[:, 1:].mean(axis=1)
        # innovation pool = daily z values (excluding t=0 which is 0)
        _z_pool = _sub.values[:, 1:].ravel()
        return {
            "start_year": start_year,
            "years": _years,
            "n_years": _n_years,
            "pooled_mean_z": float(_sub.values[:, 1:].mean()),
            "per_year_drift": _per_year_drift,
            "z_pool": _z_pool,
        }

    v1950 = fit_variant(1950)
    v1973 = fit_variant(1973)
    return v1950, v1973


@app.cell
def _(mo, v1950, v1973):
    mo.md(f"""
    - From **1950**: **{v1950['n_years']}** windows, pooled mean daily z =
      **{v1950['pooled_mean_z']:.5f}**.
    - From **1973**: **{v1973['n_years']}** windows, pooled mean daily z =
      **{v1973['pooled_mean_z']:.5f}**.
    """)
    return


@app.cell
def _(np):
    # --- Simulation -----------------------------------------------------------
    RNG = np.random.default_rng(20261102)
    N_SIM = 4000
    QS = [0.05, 0.25, 0.50, 0.75, 0.95]

    def simulate(variant, pre_vol_series, horizon):
        _n_years = variant["n_years"]
        _years = variant["years"]
        _z_pool = variant["z_pool"]
        _pool_mean = float(np.mean(_z_pool))

        _drift_idx = RNG.integers(0, _n_years, size=N_SIM)
        _drifts = variant["per_year_drift"][_drift_idx]

        _pre_vols = pre_vol_series.loc[_years].values
        _vol_idx = RNG.integers(0, _n_years, size=N_SIM)
        _sim_pre_vols = _pre_vols[_vol_idx]

        # centered innovations so we don't double-count the unconditional drift
        _eps = RNG.choice(_z_pool, size=(N_SIM, horizon), replace=True) - _pool_mean
        _cum_z = np.cumsum(_drifts[:, None] + _eps, axis=1)
        _pct_gain = np.exp(_sim_pre_vols[:, None] * _cum_z) - 1
        return _pct_gain

    return QS, simulate


@app.cell
def _(HORIZON, pre_vol, simulate, v1950, v1973):
    pct_1950 = simulate(v1950, pre_vol, HORIZON)
    pct_1973 = simulate(v1973, pre_vol, HORIZON)
    return pct_1950, pct_1973


@app.cell
def _(HORIZON, QS, alt, np, pct_1950, pct_1973, pd):
    # --- Fan charts -----------------------------------------------------------
    _fan_rows = []
    for _label, _sim in [
        ("Sample from 1950", pct_1950),
        ("Sample from 1973", pct_1973),
    ]:
        _q = np.quantile(_sim, QS, axis=0) * 100
        for _i, _day in enumerate(range(1, HORIZON + 1)):
            _fan_rows.append({
                "variant": _label,
                "day": _day,
                "q05": _q[0, _i],
                "q25": _q[1, _i],
                "median": _q[2, _i],
                "q75": _q[3, _i],
                "q95": _q[4, _i],
            })
    _fan_data = pd.DataFrame(_fan_rows)
    _fan_base = alt.Chart(_fan_data).encode(
        x=alt.X("day:Q", title="Trading days after (election day − 1)"),
    )
    _outer_band = _fan_base.mark_area(color="#4c78a8", opacity=0.20).encode(
        y=alt.Y("q05:Q", title="Cumulative percentage gain (%)"),
        y2="q95:Q",
    )
    _inner_band = _fan_base.mark_area(color="#4c78a8", opacity=0.42).encode(
        y="q25:Q",
        y2="q75:Q",
    )
    _median = _fan_base.mark_line(color="#e45756", strokeWidth=2.2).encode(
        y="median:Q",
    )
    _zero = alt.Chart(_fan_data).mark_rule(color="black", strokeWidth=0.8).encode(
        y=alt.datum(0),
    )
    alt.layer(_outer_band, _inner_band, _median, _zero).facet(
        column=alt.Column("variant:N", title=None, sort=["Sample from 1950", "Sample from 1973"]),
    ).resolve_scale(y="shared").properties(
        title="2-month post-midterm S&P 500 scenario fan chart",
        description="Shading shows the 5–95% and 25–75% intervals; the red line is the median.",
    ).interactive()
    return


@app.cell
def _(mo, np, pct_1950, pct_1973, pd):
    # --- Quantile table at t = 21 and t = 42 ----------------------------------
    _rows = []
    for _label, _sim in [("1950", pct_1950), ("1973", pct_1973)]:
        for _t_probe in [21, 42]:
            _col = _sim[:, _t_probe - 1]
            _q = np.quantile(_col, [0.05, 0.25, 0.50, 0.75, 0.95])
            _rows.append(
                {
                    "variant": _label,
                    "t (days)": _t_probe,
                    "5%": f"{_q[0] * 100:.2f}%",
                    "25%": f"{_q[1] * 100:.2f}%",
                    "median": f"{_q[2] * 100:.2f}%",
                    "75%": f"{_q[3] * 100:.2f}%",
                    "95%": f"{_q[4] * 100:.2f}%",
                    "P(gain > 0)": f"{(_col > 0).mean() * 100:.1f}%",
                }
            )
    mo.md(pd.DataFrame(_rows).to_markdown(index=False))
    return


@app.cell
def _(QS, alt, np, pct_1950, pct_1973, pd, r_wide):
    # --- Model vs. empirical quantiles at the 2-month horizon -----------------
    _t_probe = 42
    _t_idx = _t_probe - 1

    _hist_gains = np.exp(r_wide.iloc[:, _t_probe].to_numpy()) - 1
    _comparison_rows = []
    for _sim, _label in [
        (pct_1950, "Model (from 1950)"),
        (pct_1973, "Model (from 1973)"),
    ]:
        _q = np.quantile(_sim[:, _t_idx], QS)
        _comparison_rows.extend(
            {"series": _label, "quantile": _prob, "gain_pct": _value * 100}
            for _prob, _value in zip(QS, _q)
        )
    _emp_q = np.quantile(_hist_gains, QS)
    _comparison_rows.extend(
        {"series": "Empirical (all midterms)", "quantile": _prob, "gain_pct": _value * 100}
        for _prob, _value in zip(QS, _emp_q)
    )
    _comparison_data = pd.DataFrame(_comparison_rows)
    alt.Chart(_comparison_data).mark_line(point=True).encode(
        x=alt.X("quantile:Q", title="Quantile", axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 1])),
        y=alt.Y("gain_pct:Q", title=f"Cumulative gain at t = {_t_probe} days (%)"),
        color=alt.Color("series:N", title="Series"),
        order=alt.Order("quantile:Q"),
        tooltip=["series:N", alt.Tooltip("quantile:Q", format=".0%"), alt.Tooltip("gain_pct:Q", format=".2f")],
    ).properties(
        title="Model vs. empirical quantiles at the 2-month horizon",
        width=700,
        height=400,
    ).interactive()
    return


@app.cell
def _(mo, np, pd, r_wide, st, z_daily_wide):
    # --- Leave-one-election-out cross-validation -------------------------------

    def _crps_normal(y, mu, sigma):
        _z = (y - mu) / sigma
        return sigma * (
            _z * (2 * st.norm.cdf(_z) - 1) + 2 * st.norm.pdf(_z) - 1 / np.sqrt(np.pi)
        )

    _results = []
    for _label, _start in [("1950", 1950), ("1973", 1973)]:
        _sub_z = z_daily_wide[z_daily_wide.index >= _start]
        _sub_r = r_wide[r_wide.index >= _start]
        for _t_probe in [21, 42]:
            _errs = []
            for _holdout in _sub_z.index:
                _train_z = _sub_z.drop(index=_holdout)
                # daily drift and std in z-units
                _mu_day = _train_z.values[:, 1 : _t_probe + 1].mean()
                _sigma_day = _train_z.values[:, 1 : _t_probe + 1].std()
                # cumulative z at t_probe
                _mu = _mu_day * _t_probe
                _sigma = np.sqrt(_t_probe) * _sigma_day
                # actual cumulative z of the held-out year (in z-units)
                _y = _sub_z.loc[_holdout].values[1 : _t_probe + 1].sum()
                _errs.append(_crps_normal(_y, _mu, _sigma))
            _results.append(
                {
                    "variant": _label,
                    "t": _t_probe,
                    "mean CRPS (z-units)": float(np.mean(_errs)),
                }
            )

    mo.md(pd.DataFrame(_results).to_markdown(index=False))
    return


@app.cell
def _(z_daily_wide):
    per_year_drift_1950 = z_daily_wide[z_daily_wide.index >= 1950].values[:, 1:].mean(axis=1)
    per_year_drift_1973 = z_daily_wide[z_daily_wide.index >= 1973].values[:, 1:].mean(axis=1)
    return per_year_drift_1950, per_year_drift_1973


@app.cell
def _(mo, per_year_drift_1950, per_year_drift_1973):
    mo.md(f"""
    Mean per-year daily drift in z-units:
    - From 1950: **{per_year_drift_1950.mean():.5f}**
      (sd = {per_year_drift_1950.std():.5f})
    - From 1973: **{per_year_drift_1973.mean():.5f}**
      (sd = {per_year_drift_1973.std():.5f})

    The 1950s had unusually strong post-election drifts, which pulls the
    full-sample mean up. That's the main sensitivity between the two variants.
    """)
    return


@app.cell
def _(alt, np, pd, per_year_drift_1950, per_year_drift_1973):
    # Histogram of per-year drift
    _drift_data = pd.DataFrame({
        "drift": np.concatenate([per_year_drift_1950, per_year_drift_1973]),
        "sample": ["From 1950"] * len(per_year_drift_1950)
        + ["From 1973"] * len(per_year_drift_1973),
    })
    _histogram = alt.Chart(_drift_data).mark_bar(opacity=0.65).encode(
        x=alt.X("drift:Q", bin=alt.Bin(maxbins=12), title="Per-year mean daily z (drift)"),
        xOffset=alt.XOffset("sample:N"),
        y=alt.Y("count():Q", title="Count"),
        color=alt.Color("sample:N", title="Sample"),
        tooltip=["sample:N", alt.Tooltip("count():Q", title="Count")],
    )
    _zero = alt.Chart(pd.DataFrame({"drift": [0]})).mark_rule(color="black", strokeWidth=0.8).encode(
        x="drift:Q",
    )
    alt.layer(_histogram, _zero).properties(
        title="Per-year drift in the post-election window",
        width=700,
        height=360,
    ).interactive()
    return


if __name__ == "__main__":
    app.run()
