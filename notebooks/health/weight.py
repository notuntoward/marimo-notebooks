# /// script
# dependencies = [
#     "altair==6.2.2",
#     "marimo",
#     "matplotlib==3.11.1",
#     "numpy==2.5.2",
#     "pandas==3.0.5",
#     "plotly==7.0.0",
#     "pyarrow",
#     "scipy==1.18.1",
# ]
# requires-python = ">=3.12"
# ///

import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Weight Trend & Rate-of-Change Estimation via Savitzky–Golay Filtering

    This notebook estimates, for **every day** in your weight log, two quantities:

    1. A **smoothed weight estimate** \(\hat{w}(t)\) — your underlying weight with
       day-to-day noise (water, food, digestion, weekly cycle) removed.
    2. A **smoothed rate-of-change estimate** \(\hat{w}'(t)\), in units per day
       (multiply by 7 for a weekly rate), suitable for tracking whether you are
       gaining or losing and how fast.

    Both come from the **same underlying tool**: a local polynomial
    (Savitzky–Golay, "SG") least-squares fit computed in a sliding window around
    each day. The 0th derivative of the local polynomial *at its center* gives the
    smoothed weight; the 1st derivative gives the slope. At the two ends of your
    data — the beginning of your log and *today* — the window can't be
    centered, so the filter automatically falls back to a one-sided fit using
    only the data that exists, rather than requiring a symmetric window. This
    notebook explains why this method was chosen, states its assumptions
    explicitly, and shows how the window length is selected from your own data
    rather than assumed.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. The Problem, Framed as Signal Processing

    Daily weight \(y_t\) is modeled as

    \[
    y_t = w(t) + \varepsilon_t
    \]

    where \(w(t)\) is the true, slowly evolving "dry" body-mass trend you actually
    care about, and \(\varepsilon_t\) is noise: water retention, meal timing,
    digestion state, and measurement variability. Clinical sources report that
    normal day-to-day fluctuation for an adult is on the order of **2–6 lb**
    peak-to-peak, arising mostly from water and food mass rather than true fat or
    lean-mass change (Cleveland Clinic 2024 [web:1], [health.clevelandclinic.org/weight-fluctuations](https://health.clevelandclinic.org/weight-fluctuations)
    [web:1]; Healthline 2018 [web:2], [healthline.com/health/weight-fluctuation](https://www.healthline.com/health/weight-fluctuation)
    [web:2]). On top of this broadband noise, a number of cohort studies have
    documented a **systematic weekly cycle**: weight tends to be highest on
    Sunday/Monday and lowest by Friday, driven by weekend eating and activity
    patterns. Orsama et al. (2014) [web:3] documented this rhythm in a large
    self-tracking cohort and explicitly used weekly-centered moving averages to
    remove it before estimating trend (Orsama et al. 2014, *Obesity Facts* [web:3],
    [pmc.ncbi.nlm.nih.gov/articles/PMC5644907](https://pmc.ncbi.nlm.nih.gov/articles/PMC5644907/)
    [web:3]).

    There is also evidence that daily weight fluctuations are not simple white
    noise but have their own short-range autocorrelation structure; Yatabe &
    Asubar (2021) [web:4] model daily body-weight fluctuations around a slowly
    drifting mean using an **Ornstein–Uhlenbeck (mean-reverting) process**
    (Yatabe & Asubar 2021, *Physica A* [web:4],
    [sciencedirect.com/science/article/abs/pii/S0378437121005598](https://www.sciencedirect.com/science/article/abs/pii/S0378437121005598)
    [web:4]). This matters practically: daily deviations are not independent
    from one day to the next — they tend to relax back toward the underlying
    trend over a few days — which is part of *why* short windows are so noisy: a
    single high or low day contaminates the read on neighboring days too.

    The goal is to recover \(w(t)\) and \(w'(t)\) (its slope) from noisy \(y_t\),
    using a method that:

    - Is **local** (uses nearby days, not the whole 3-month history, since the
      true rate of change can itself change over months).
    - **Weights nearby days more than distant ones** (tapering) rather than
      treating every day in the window as equally informative.
    - Can absorb **local curvature** in the trend (a diet change, a plateau) so
      an artificially short window isn't needed just to avoid bias.
    - Produces **honest edge estimates** at the start of the log and today,
      without waiting for a full window to accumulate.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. Mathematical Foundation of Savitzky–Golay Filtering

    A Savitzky–Golay (SG) filter fits a local polynomial of degree $m$ (default: $m=2$, quadratic) to a sliding window of $N = 2M+1$ points around each evaluation day $t_0$.

    ### (a) How the Filter Predicts Slope at the Center Point
    Within a window centered at day $t_0$, time is parameterized as relative offset $\tau = t - t_0 \in [-M, M]$. The local polynomial is:

    \[
    p(\tau) = c_0 + c_1 \tau + c_2 \tau^2 + \dots + c_m \tau^m
    \]

    By Taylor's theorem, evaluating $p(\tau)$ and its derivative at the window center $\tau = 0$ yields:
    - **Smoothed weight estimate:** $\hat{w}(t_0) = p(0) = c_0$
    - **Smoothed slope (rate of change):** $\hat{w}'(t_0) = p'(0) = c_1$

    Because Ordinary Least Squares (OLS) fitting is a linear operation, the slope coefficient $c_1$ is a linear combination of the window points: $\hat{w}'(t_0) = \sum_{k=-M}^{M} g_k y_{t_0+k}$.

    ---

    ### (b) Are Filter Coefficients Recomputed for Each Point Estimate?
    - **No, for all interior points on a uniform time grid, the filter coefficients ARE NOT recomputed per point.**
    - Because the relative window grid $\tau \in \{-M, \dots, +M\}$ is identical for every interior position, the Vandermonde design matrix $V$ and its pseudoinverse $(V^T V)^{-1} V^T$ are constant.
    - The filter coefficients $h_k$ (for smoothing) and $g_k$ (for slope) are precomputed **once**, reducing the entire operation across the interior to a fast $\mathcal{O}(N)$ **discrete convolution**:

    \[
    \hat{w}(t_0) = \sum_{k=-M}^{M} h_k y_{t_0+k}, \qquad \hat{w}'(t_0) = \sum_{k=-M}^{M} g_k y_{t_0+k}
    \]

    - **When coefficients ARE recomputed:** Coefficients are re-evaluated *only at boundary/edge points* where asymmetric windows are used, or if the time spacing $\Delta t_i$ is non-uniform.

    ---

    ### (c) Why SG Filtering Results in a Tapered, Symmetric Kernel
    - **Implicit Tapering:** Although local OLS weights all $N$ points in a window equally in $L_2$ norm, evaluating the fitted polynomial *at the center point $\tau = 0$* projects the data onto orthogonal Gram/Legendre polynomials. For a quadratic fit ($m=2$), the effective smoothing kernel weights follow a parabolic profile:

    \[
    h_k = \frac{3(3M^2 + 3M - 1 - 5k^2)}{(2M-1)(2M+1)(2M+3)}
    \]

    Points at the outer edges $k = \pm M$ receive significantly lower weight than the center point $k = 0$, producing a **tapered kernel** that naturally de-emphasizes distant noise.

    - **Symmetry vs. Asymmetry:**
      - **Interior Points:** The filter kernel is **strictly symmetric** ($h_{-k} = h_k$ for smoothing, anti-symmetric $g_{-k} = -g_k$ for slope), resulting in **zero phase lag**.
      - **Edge Points (e.g., "Today"):** Near the boundaries, the window cannot be centered and becomes one-sided ($\tau \in [-N+1, 0]$). The resulting edge kernel is **asymmetric**, giving higher weight to the most recent day.
    """)

    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. Choosing the Window Length: Generalized Cross-Validation (GCV)

    For a *linear* smoother \(\hat{y} = Hy\) (which SG filtering is, for a fixed
    window length and polynomial order — \(H\) is a fixed matrix that does not
    depend on \(y\)), Generalized Cross-Validation estimates out-of-sample
    prediction error without actually holding out data, using

    \[
    \mathrm{GCV}(N) = \frac{\frac{1}{n}\sum_t (y_t - \hat{y}_t)^2}{\left(1 -
    \mathrm{tr}(H)/n\right)^2}
    \]

    \(\mathrm{tr}(H)/n\) is the effective fraction of "degrees of freedom" the
    smoother uses per point. A short, flexible window has a high
    \(\mathrm{tr}(H)\) — it can fit the noise, so its raw residual looks
    deceptively small — while GCV's denominator penalizes that flexibility so
    short, overfitting windows are correctly scored as *worse*, not better. GCV
    is a standard, well-established model-selection criterion for exactly this
    kind of local-polynomial/kernel smoothing problem. This notebook computes
    \(H\) **exactly** (not approximately) by applying the SG filter to each unit
    basis vector, which correctly captures the one-sided fits used at the edges
    (Section 4), then scores every candidate window length on your actual data
    and picks the minimum. This directly answers "how do I choose the right
    window length" using your own 3 months of data rather than a rule of thumb.

    Windows are evaluated for the **smoothing task** (0th derivative, used for
    the weight estimate); the identical criterion with `deriv=1` could instead
    be scored directly on the derivative if you want the slope and the
    smoothed-weight curve tuned independently. By default this notebook uses one
    GCV-selected window for both, since the slope is just the derivative of the
    same local fit that produces the smoothed value — this keeps the two outputs
    mutually consistent (the plotted slope curve is the exact derivative of the
    plotted smoothed curve).
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 4. Edge Handling: One-Sided Fits at the Start and at "Today"

    Requiring a full symmetric window means the most recent
    \(\lfloor N/2 \rfloor\) days could never be scored, which defeats the point
    of a same-day rate estimate. SciPy's `savgol_filter` with `mode='interp'`
    solves this the way SG filters have always handled edges: for any point
    where a full centered window would run off the end of the data, it instead
    fits the *same order polynomial* to the nearest full-length window that
    *does* fit inside the available data, then evaluates that polynomial (or its
    derivative) **at the edge point itself** — an extrapolation *within* an
    already-fit local polynomial, not a naive line drawn through only two
    points. Concretely:

    - Near **day 1** of your log, the filter fits its order-\(n\) polynomial to
      the first \(N\) days and evaluates the fit (and its derivative) at day 1,
      2, 3, … rather than at the window's center.
    - Near **today** (the most recent day), it fits the same order polynomial to
      the last \(N\) days and evaluates moving forward through the most recent
      days.

    This is the standard, documented edge-extension behavior of SciPy's
    implementation (SciPy `savgol_filter` documentation [web:8],
    [docs.scipy.org/doc/scipy/reference/generated/scipy.signal.savgol_filter.html](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.savgol_filter.html)
    [web:8]) and is the most defensible one-sided estimate available: it is
    exactly what the interior filter would produce if you kept the same local
    polynomial model but simply had no more data past the edge, rather than
    assuming the trend flattens, mirrors, or repeats (the alternative `mode`
    options — `'nearest'`, `'mirror'`, `'wrap'`, `'constant'` — all impose an
    assumption about data beyond the edge that we have no evidence for, so this
    notebook deliberately avoids them).

    **Caveat:** edge estimates necessarily use *less independent information*
    than interior estimates (an edge fit near day 1 with a 21-day window still
    uses 21 points, but they are all on one side, so the estimate is more
    sensitive to whatever is happening in that specific stretch). Practically,
    your **most recent half-window days of slope estimate should be treated as
    provisional** and expected to shift as new days arrive and enter the window
    symmetrically. This is the same phenomenon as revisions in seasonally
    adjusted economic statistics, and is not a defect specific to this method.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 5. Assumptions

    This method, and the interpretation of its output, rests on assumptions
    stated explicitly here so you can judge when to distrust it:

    - **Local smoothness.** The true trend \(w(t)\) is well-approximated by a
      low-degree polynomial (default: quadratic) within any given window. This
      fails sharply at a genuine step change (a multi-day fast, a
      measurement-scale change, a sudden water-weight shift from an injury or
      medication change) — the filter will smear such a jump over roughly half a
      window's width rather than reproducing it instantly.
    - **Noise is roughly stationary in variance** over the 3-month period. If
      your measurement noise changed substantially partway through (e.g., you
      started weighing at a more consistent time of day), the single
      GCV-selected window is a compromise across the whole series rather than
      optimal for each part.
    - **The weekly cycle, if present, is not explicitly modeled.** SG smoothing
      with a window that is a multiple of 7 days will average over a full weekly
      cycle and largely cancel it, similar to Orsama et al.'s approach [web:3],
      but the filter does not separately estimate a day-of-week effect the way a
      regression with weekday dummies would. Treat a large weekly cycle as a
      contributor to \(\sigma^2\) (noise) rather than to \(w(t)\) (trend).
    - **Missing days are not imputed.** The notebook assumes one row per
      calendar day. If you have missing days, fill them (e.g., linear
      interpolation) before use.
    - **GCV window selection assumes the tradeoff is uniform across the series.**
      It picks one window length that minimizes *average* error across all days,
      not necessarily the best window for any single day.

    ## References

    1. Cleveland Clinic (2024). *Why Does My Weight Fluctuate So Much?*
       [health.clevelandclinic.org/weight-fluctuations](https://health.clevelandclinic.org/weight-fluctuations)
    2. Healthline (2018). *Weight Fluctuation: Daily Range, Causes, and How to
       Weigh.* [healthline.com/health/weight-fluctuation](https://www.healthline.com/health/weight-fluctuation)
    3. Orsama, A.L. et al. (2014). *Weight Rhythms: Weight Increases during
       Weekends and Decreases during Weekdays.* Obesity Facts.
       [pmc.ncbi.nlm.nih.gov/articles/PMC5644907](https://pmc.ncbi.nlm.nih.gov/articles/PMC5644907/)
    4. Yatabe, Z. & Asubar, J.T. (2021). *Ornstein–Uhlenbeck process in a human
       body weight fluctuation.* Physica A: Statistical Mechanics and its
       Applications.
       [sciencedirect.com/science/article/abs/pii/S0378437121005598](https://www.sciencedirect.com/science/article/abs/pii/S0378437121005598)
    5. Savitzky, A. & Golay, M.J.E. (1964). *Smoothing and Differentiation of
       Data by Simplified Least Squares Procedures.* Analytical Chemistry, 36(8),
       1627–1639. [pubs.acs.org/doi/10.1021/ac60214a047](https://pubs.acs.org/doi/10.1021/ac60214a047)
    6. Sadeghi, M. & Behnia, F. (2018). *Optimum Window Length of
       Savitzky–Golay Filters with Arbitrary Order.* arXiv:1808.10489 / IEEE
       Transactions on Signal Processing.
       [arxiv.org/abs/1808.10489](https://arxiv.org/abs/1808.10489)
    7. AltaiPlot. *How to Choose Savitzky-Golay Filter Parameters (Window Size,
       Polynomial Order).*
       [altaiplot.com/blog/how-to-choose-savitzky-golay-parameters](https://altaiplot.com/blog/how-to-choose-savitzky-golay-parameters/)
    8. SciPy Developers. *scipy.signal.savgol_filter* documentation.
       [docs.scipy.org/doc/scipy/reference/generated/scipy.signal.savgol_filter.html](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.savgol_filter.html)
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 6. Setup
    """)
    return


@app.cell
def _():
    import numpy as np
    import pandas as pd
    import altair as alt
    from scipy.signal import savgol_filter
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import marimo as mo


    return alt, go, make_subplots, mo, np, pd, savgol_filter


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 7. Load Your Data

    Upload a CSV with at least two columns: a date column and a weight column.
    If no file is uploaded, the notebook falls back to a synthetic example
    series so every cell below still runs and can be inspected.

    Expected format (column names are auto-detected via the fields below):

    ```
    date,weight
    2026-06-01,181.2
    2026-06-02,180.6
    ```
    """)
    return


@app.cell
def _():
    inFNm = "260904 Weight.csv"
    return (inFNm,)


@app.cell(hide_code=True)
def _(inFNm):
    import numpy as _np
    import pandas as _pd

    try:
        def _strip_lbs(x):
            if isinstance(x, str):
                val = x.split()[0]
                try:
                    return float(val)
                except ValueError:
                    return _np.nan
            return x

        df_raw_file = _pd.read_csv(inFNm)
        cols_lower = {col: str(col).strip().lower() for col in df_raw_file.columns}
        df_raw_file = df_raw_file.rename(columns=cols_lower)

        if "date" in df_raw_file.columns and "weight" in df_raw_file.columns:
            df_raw_file["date"] = _pd.to_datetime(df_raw_file["date"], errors="coerce")
            df_raw_file["weight"] = df_raw_file["weight"].apply(_strip_lbs)
            df_raw_file["weight"] = _pd.to_numeric(df_raw_file["weight"], errors="coerce")

        if not df_raw_file.empty:
            df_raw_file = df_raw_file.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
            _full_dates = _pd.date_range(start=df_raw_file["date"].min(), end=df_raw_file["date"].max(), freq="D")
            df_raw_file = df_raw_file.set_index("date").reindex(_full_dates).rename_axis("date").reset_index().sort_values("date", ascending=True).reset_index(drop=True)

            _missing_mask = df_raw_file["weight"].isna()
            _num_missing = int(_missing_mask.sum())
            _total_points = len(df_raw_file)
            _pct_missing = (_num_missing / _total_points * 100) if _total_points > 0 else 0.0

            _gap_lengths = []
            _curr_gap = 0
            for _is_m in _missing_mask:
                if _is_m:
                    _curr_gap += 1
                elif _curr_gap > 0:
                    _gap_lengths.append(_curr_gap)
                    _curr_gap = 0
            if _curr_gap > 0:
                _gap_lengths.append(_curr_gap)

            df_raw_file["weight"] = df_raw_file["weight"].interpolate(method="linear").bfill().ffill()

            print("Missing Points Interpolation Summary:")
            print(f"Number of missing points interpolated: {_num_missing} / {_total_points} ({_pct_missing:.2f}%)")
            print("Histogram of missing gap lengths:")
            if _gap_lengths:
                _counts = _pd.Series(_gap_lengths).value_counts().sort_index()
                for _length, _cnt in _counts.items():
                    print(f"  Gap of {_length} day(s): {_cnt} time(s)")
            else:
                print("  No missing points found.")
    except Exception:
        df_raw_file = []

    df_raw_file
    return (df_raw_file,)


@app.cell(hide_code=True)
def _(mo, results_df):
    _d_start = results_df["date"].iloc[0].strftime("%b %d, %Y")
    _d_end = results_df["date"].iloc[-1].strftime("%b %d, %Y")

    time_slider = mo.ui.slider(
        start=0,
        stop=len(results_df) - 1,
        step=1,
        value=len(results_df) - 1,
        label=f"Time Slider ({_d_start} — {_d_end})",
        full_width=True,
    )
    return (time_slider,)


@app.cell(hide_code=True)
def _(mo):
    poly_order = mo.ui.dropdown(options=["1", "2", "3"], value="2", label="SG polynomial order")

    min_window = mo.ui.number(start=5, stop=61, step=2, value=7, label="Smallest window to test (days)")
    max_window = mo.ui.number(start=9, stop=91, step=2, value=45, label="Largest window to test (days)")

    mo.hstack([poly_order, min_window, max_window])
    return max_window, min_window, poly_order


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    A quadratic (order 2) default is recommended: it absorbs local curvature
    (a slope that itself changes) while remaining simple enough that even short
    windows have a stable fit. Order 1 reduces to plain OLS with tapering only,
    which is the sliding-window approach mentioned in the original question;
    order 3 allows more curvature but needs a longer window to avoid overfitting
    and is rarely necessary for body-weight trends. The candidate window range
    should span from about one week (7) up to roughly one third to one half of
    your total data length, since SG needs the window length to not exceed the
    series length and the GCV criterion below becomes unreliable if the window
    starts to approach the full series.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 9. Select the Optimal Window via Generalized Cross-Validation
    """)
    return


@app.cell(hide_code=True)
def _(np, savgol_filter):
    def sg_smoother_matrix(n, window_length, polyorder, deriv=0):
        """Exact n x n linear-smoother matrix H such that y_hat = H @ y,
        including SciPy's one-sided edge fits (mode='interp'). Built by applying
        the filter to each unit basis vector; O(n^2 log n), trivial for n ~ 90-1000."""

        H = np.zeros((n, n))
        for j in range(n):
            e = np.zeros(n)
            e[j] = 1.0
            H[:, j] = savgol_filter(
                e, window_length=window_length, polyorder=polyorder, deriv=deriv, mode="interp"
            )

        return H

    def gcv_score(y, window_length, polyorder):
        """Generalized Cross-Validation score for SG smoothing (deriv=0).
        Lower is better. Penalizes short/flexible windows that overfit noise."""

        n = len(y)
        H = sg_smoother_matrix(n, window_length, polyorder, deriv=0)
        yhat = H @ y
        resid = y - yhat

        trH = np.trace(H)
        denom = (1 - trH / n) ** 2

        if denom <= 1e-8:
            return np.inf

        return float(np.mean(resid ** 2) / denom)

    def select_best_window(y, polyorder, candidate_windows):
        scores = []
        for w in candidate_windows:
            if w <= polyorder or w > len(y):
                continue

            scores.append((w, gcv_score(y, w, polyorder)))

        best_w, best_score = min(scores, key=lambda r: r[1])
        return best_w, best_score, scores

    return (select_best_window,)


@app.cell(hide_code=True)
def _(df_raw, max_window, min_window, poly_order, select_best_window):
    _polyorder = int(poly_order.value)
    _candidate_windows = list(range(int(min_window.value), int(max_window.value) + 1, 2))

    best_window, best_gcv_score, all_scores = select_best_window(
        df_raw["weight"].to_numpy(), _polyorder, _candidate_windows)
    return all_scores, best_window


@app.cell(hide_code=True)
def _(all_scores, alt, best_window, mo, pd):
    _scores_df = pd.DataFrame(all_scores, columns=["window", "gcv_score"])

    _chart = (
        alt.Chart(_scores_df)
        .mark_line(point=True)
        .encode(
            x=alt.X("window:Q", title="Window length (days)"),
            y=alt.Y("gcv_score:Q", title="GCV score (lower = better)"),
        )

        .properties(title=f"GCV score vs. window length — selected: {best_window} days", width=600, height=300)
    )

    _rule = alt.Chart(_scores_df[_scores_df["window"] == best_window]).mark_rule(color="red").encode(x="window:Q")

    mo.vstack(
        [
            mo.md(
                f"**Selected window length: {best_window} days** "
                f"(minimizes GCV score across the candidate range tested)."
            ),
            mo.ui.altair_chart(_chart + _rule),
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 10. Compute Smoothed Weight and Slope (with Edge Estimates)
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 11. Plots
    """)
    return


@app.cell(hide_code=True)
def weight_and_rate_cell(go, make_subplots, mo, results_df, time_slider):
    _idx = int(time_slider.value)
    _sel_row = results_df.iloc[_idx]
    _sel_date = _sel_row["date"]

    _edge_df = results_df[results_df["is_edge_estimate"]]

    _fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.10,
        subplot_titles=(
            "1. Raw Weight vs. SG-Smoothed Weight Trend",
            "2. Estimated Weekly Rate of Weight Change (Negative = Losing Weight)",
        ),
    )

    # --- Subplot 1: Raw & Smoothed Weight ---
    _fig.add_trace(
        go.Scatter(
            x=results_df["date"],
            y=results_df["weight"],
            mode="lines+markers",
            name="Raw Weight",
            line=dict(color="rgba(70, 130, 180, 0.4)", width=1.5),
            marker=dict(color="rgba(70, 130, 180, 0.6)", size=4),
            hovertemplate="Date: %{x|%Y-%m-%d}<br>Raw Weight: %{y:.1f} lbs<extra></extra>",
        ),
        row=1,
        col=1,
    )

    _fig.add_trace(
        go.Scatter(
            x=results_df["date"],
            y=results_df["smoothed_weight"],
            mode="lines",
            name="Smoothed Weight",
            line=dict(color="rgba(220, 20, 60, 0.85)", width=2.5),
            hovertemplate="Date: %{x|%Y-%m-%d}<br>Smoothed Weight: %{y:.2f} lbs<extra></extra>",
        ),
        row=1,
        col=1,
    )

    _fig.add_trace(
        go.Scatter(
            x=_edge_df["date"],
            y=_edge_df["smoothed_weight"],
            mode="markers",
            name="Edge Estimate (Weight)",
            marker=dict(color="orange", size=5, opacity=0.8),
            hovertemplate="Date: %{x|%Y-%m-%d}<br>Edge Smoothed: %{y:.2f} lbs<extra></extra>",
        ),
        row=1,
        col=1,
    )

    # Highlight selected point on Plot 1
    _fig.add_trace(
        go.Scatter(
            x=[_sel_date],
            y=[_sel_row["smoothed_weight"]],
            mode="markers",
            name="Selected Time",
            marker=dict(color="#2563eb", size=10, symbol="diamond", line=dict(color="white", width=1.5)),
            showlegend=False,
            hovertemplate="Selected Date: %{x|%Y-%m-%d}<br>Smoothed: %{y:.2f} lbs<extra></extra>",
        ),
        row=1,
        col=1,
    )

    # Vertical Reference Line on Plot 1 at time selected by slider
    _fig.add_vline(x=_sel_date, line_dash="dot", line_color="#2563eb", line_width=1.5, row=1, col=1)

    # --- Subplot 2: Rate of Change ---
    _fig.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1.0, row=2, col=1)

    _fig.add_trace(
        go.Scatter(
            x=results_df["date"],
            y=results_df["weekly_rate"],
            mode="lines",
            name="Weekly Rate",
            line=dict(color="steelblue", width=2.2),
            hovertemplate="Date: %{x|%Y-%m-%d}<br>Weekly Rate: %{y:.2f} lbs/wk<extra></extra>",
        ),
        row=2,
        col=1,
    )

    _fig.add_trace(
        go.Scatter(
            x=_edge_df["date"],
            y=_edge_df["weekly_rate"],
            mode="markers",
            name="Edge Estimate (Rate)",
            marker=dict(color="orange", size=5, opacity=0.8),
            hovertemplate="Date: %{x|%Y-%m-%d}<br>Edge Rate: %{y:.2f} lbs/wk<extra></extra>",
        ),
        row=2,
        col=1,
    )

    # Highlight selected point on Plot 2
    _fig.add_trace(
        go.Scatter(
            x=[_sel_date],
            y=[_sel_row["weekly_rate"]],
            mode="markers",
            name="Selected Time Rate",
            marker=dict(color="#2563eb", size=10, symbol="diamond", line=dict(color="white", width=1.5)),
            showlegend=False,
            hovertemplate="Selected Date: %{x|%Y-%m-%d}<br>Weekly Rate: %{y:.2f} lbs/wk<extra></extra>",
        ),
        row=2,
        col=1,
    )

    # Vertical Reference Line on Plot 2 at time selected by slider
    _fig.add_vline(x=_sel_date, line_dash="dot", line_color="#2563eb", line_width=1.5, row=2, col=1)

    # Compact Plotly height (450px total) with top margin 65px so legend (y=1.12) sits cleanly above title
    _fig.update_layout(
        template="plotly_white",
        width=800,
        height=450,
        margin=dict(t=65, b=25, l=55, r=25),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.12,
            xanchor="center",
            x=0.5,
            font=dict(size=12),
        ),
    )

    _fig.update_yaxes(title_text="Weight (lbs)", row=1, col=1)
    _fig.update_yaxes(title_text="Rate (lbs/week)", row=2, col=1)
    _fig.update_xaxes(title_text="Date", row=2, col=1)

    # Compact, space-efficient readout banner
    _rate_color = "#dc2626" if _sel_row["weekly_rate"] > 0 else "#16a34a"
    _edge_badge = (
        '<span style="color: #d97706; font-size: 11px; font-weight: 600;">(Edge Estimate)</span>'
        if _sel_row["is_edge_estimate"]
        else ""
    )

    _readout_ui = mo.md(f"""
    <div style="display: flex; flex-wrap: wrap; gap: 14px; align-items: center; justify-content: space-around; background: #f8f9fa; padding: 6px 12px; border-radius: 6px; border: 1px solid #e2e8f0; font-family: system-ui, -apple-system, sans-serif; font-size: 13px; color: #1e293b; margin-top: 4px;">
      <div>📅 <strong>Date:</strong> {_sel_date.strftime('%b %d, %Y')} {_edge_badge}</div>
      <div>⚖️ <strong>Raw Weight:</strong> {_sel_row['weight']:.1f} lbs</div>
      <div>📈 <strong>Smoothed Weight:</strong> {_sel_row['smoothed_weight']:.2f} lbs</div>
      <div>⚡ <strong>Weekly Rate:</strong> <span style="color: {_rate_color}; font-weight: bold;">{_sel_row['weekly_rate']:+.2f} lbs/wk</span></div>
      <div>⏱️ <strong>Daily Slope:</strong> {_sel_row['daily_slope']:+.3f} lbs/day</div>
    </div>
    """)

    charts_display = mo.vstack([
        mo.ui.plotly(_fig),
        time_slider,
        _readout_ui,
    ], gap=0.5).style({"max-height": "none", "overflow": "visible"})

    charts_display

    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 12. Today's Estimate and Recent History
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 13. Sanity Check Against Ground Truth (Synthetic Data Only)

    This section only produces output when you are viewing the synthetic
    fallback series (no file uploaded); it compares the recovered smoothed
    trend and slope against the **known true values** used to generate the
    synthetic data, confirming the pipeline behaves as expected — including at
    the edges — before you trust it on your real log.
    """)
    return


@app.cell(hide_code=True)
def _(best_window, df_raw, poly_order, savgol_filter):
    _polyorder = int(poly_order.value)
    _w = best_window

    # df_raw is already chronologically sorted (oldest first, 1-day spacing)
    weight_arr = df_raw["weight"].to_numpy()

    smoothed_weight = savgol_filter(weight_arr, window_length=_w, polyorder=_polyorder, deriv=0, mode="interp")
    daily_slope = savgol_filter(weight_arr, window_length=_w, polyorder=_polyorder, deriv=1, mode="interp")
    weekly_slope = daily_slope * 7.0

    results_df = df_raw.copy()
    results_df["smoothed_weight"] = smoothed_weight
    results_df["daily_slope"] = daily_slope
    results_df["weekly_rate"] = weekly_slope

    half_window = _w // 2

    results_df["is_edge_estimate"] = (results_df.index < half_window) | (
        results_df.index >= len(results_df) - half_window
    )
    return (results_df,)


@app.cell(hide_code=True)
def _(df_raw_file, inFNm, mo, np, pd):
    def _make_synthetic(n_days=90, seed=0):
        rng = np.random.default_rng(seed)
        t = np.arange(n_days)
        true_slope = np.where(t < 45, -0.20, -0.05)
        trend_vals = [182.0]
        for i in range(1, n_days):
            trend_vals.append(trend_vals[-1] + true_slope[i - 1])
        trend_vals = np.array(trend_vals)
        iid_noise = rng.normal(0, 1.0, n_days)
        weekly_cycle = 0.5 * np.sin(2 * np.pi * (t % 7) / 7)
        dates = pd.date_range("2026-06-06", periods=n_days, freq="D")
        return (
            pd.DataFrame({"date": dates, "weight": trend_vals + iid_noise + weekly_cycle}),
            trend_vals,
            true_slope,
        )

    _using_synthetic = len(df_raw_file) == 0

    if _using_synthetic:
        df_raw, synthetic_trend, synthetic_slope = _make_synthetic()
        data_source_note = (
            "No file uploaded — using a **synthetic 90-day example** "
            "(true slope of -0.20 lb/day for the first 45 days, then -0.05 lb/day, "
            "plus daily noise and a weekly cycle) so the notebook runs end to end. "
            "Upload your own CSV above to replace this."
        )
    else:
        df_raw = df_raw_file.copy()
        synthetic_trend, synthetic_slope = None, None
        data_source_note = f"Loaded **{len(df_raw)}** rows from `{inFNm}`."

    # Convert date/weight types and sort strictly ASCENDING by date (chronological order)
    df_raw["date"] = pd.to_datetime(df_raw["date"])
    df_raw["weight"] = pd.to_numeric(df_raw["weight"], errors="coerce")
    df_raw = df_raw.dropna(subset=["date", "weight"]).sort_values("date", ascending=True).reset_index(drop=True)

    mo.md(data_source_note)
    return (df_raw,)


if __name__ == "__main__":
    app.run()
