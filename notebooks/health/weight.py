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
    ## 2. Mathematical Design: Retrospective vs. Real-Time Rate Estimation

    This section derives the mathematical formulas for both **weight level** and **rate-of-change (slope)** estimates, documents their noise variances, and provides principled derivations for all default slider parameters.

    ---

    ### 1. How the Centered Savitzky–Golay Filter Estimates Slope ($\hat{w}'(t_0)$)

    At each evaluation day $t_0$, time inside a symmetric window of $N_{\text{SG}} = 2M+1$ points is parameterized as relative offset $\tau = t - t_0 \in [-M, M]$. We fit a local polynomial of degree $m_{\text{poly}}$:

    \[
    p(\tau) = c_0 + c_1 \tau + c_2 \tau^2 + \dots + c_{m_{\text{poly}}} \tau^{m_{\text{poly}}}
    \]

    by Ordinary Least Squares (OLS). Differentiating $p(\tau)$ with respect to time $\tau$ and evaluating at $\tau = 0$ yields $p'(0) = c_1$. Thus, the retrospective slope $\hat{w}'(t_0)$ is the linear coefficient $c_1$ of the local fitted polynomial. In matrix form with Vandermonde matrix $V$ ($\text{row } i: [1, \tau_i, \tau_i^2, \dots]$):

    \[
    \begin{bmatrix} \hat{w}(t_0) \\ \hat{w}'(t_0) \\ \vdots \end{bmatrix} = \begin{bmatrix} c_0 \\ c_1 \\ \vdots \end{bmatrix} = (V^T V)^{-1} V^T Y_{t_0}
    \]

    ---

    ### 2. How Rolling Trailing WLS Estimates Causal Slope ($\hat{\beta}_t$)

    To estimate the current rate today ($t$) using past observations $y_{t-j}$ ($j \ge 0$ days back) without using future data, we fit the local linear model $y_{t-j} = \alpha_t - \beta_t \cdot j + \varepsilon_{t-j}$ with exponential recency weights $w_j = 2^{-j/h}$.

    Minimizing $S(\alpha_t, \beta_t) = \sum_{j=0}^{m-1} w_j \left[ y_{t-j} - (\alpha_t - \beta_t j) \right]^2$ yields the $2 \times 2$ normal equations:

    \[
    \begin{bmatrix} \sum_{j=0}^{m-1} w_j & -\sum_{j=0}^{m-1} w_j j \\ -\sum_{j=0}^{m-1} w_j j & \sum_{j=0}^{m-1} w_j j^2 \end{bmatrix} \begin{bmatrix} \hat{\alpha}_t \\ \hat{\beta}_t \end{bmatrix} = \begin{bmatrix} \sum_{j=0}^{m-1} w_j y_{t-j} \\ -\sum_{j=0}^{m-1} w_j j y_{t-j} \end{bmatrix}
    \]

    Solving this $2 \times 2$ system yields the explicit closed-form causal daily slope $\hat{\beta}_t$:

    \[
    \hat{\beta}_t = \frac{\left(\sum w_j\right) \left(-\sum w_j j y_{t-j}\right) - \left(-\sum w_j j\right) \left(\sum w_j y_{t-j}\right)}{\left(\sum w_j\right) \left(\sum w_j j^2\right) - \left(\sum w_j j\right)^2}
    \]

    Multiplying $\hat{\beta}_t$ by 7 yields the **Trailing Weekly Rate Nowcast** ($7 \hat{\beta}_t$).

    ---

    ### 3. Principled Selection of Default Values for All UI Sliders

    Every default slider parameter in this notebook is selected through an explicit mathematical principle:

    #### (a) SG Polynomial Order ($m = 2$, Quadratic)
    - **Equation:** $p(\tau) = c_0 + c_1 \tau + c_2 \tau^2$.
    - **Principle:** By Taylor expansion, body weight around $t_0$ is $w(t_0 + \tau) = w(t_0) + w'(t_0)\tau + \frac{1}{2} w''(t_0) \tau^2 + \mathcal{O}(\tau^3)$.
      - $m=1$ (linear) assumes constant slope ($w''=0$), causing severe curvature bias during diet shifts or plateaus.
      - $m=2$ (quadratic) absorbs local acceleration ($w'' \neq 0$) without overfitting noise.
      - $m=3$ (cubic) increases noise variance by a factor of $\frac{2m+1}{2m-1} = 1.67$ without improving short-window trends.
      - **Default Choice:** $m=2$.

    #### (b) Minimum & Maximum Candidate SG Window ($N_{\text{min}} = 7\text{ days}, N_{\text{max}} = \lfloor N_{\text{total}}/2 \rfloor$)
    - **Principle for $N_{\text{min}} = 7\text{ days}$:** Smallest window that spans one full 7-day weekly lifestyle cycle (weekend vs. weekday water/food rhythm), averaging out weekly oscillations (Orsama et al. 2014).
    - **Principle for $N_{\text{max}} = \lfloor N_{\text{total}}/2 \rfloor$:** Upper-bounded at half the total dataset length so the GCV degree-of-freedom denominator $(1 - \mathrm{tr}(H)/n)^2$ remains statistically stable.

    #### (c) Recency Half-Life ($h^* = 0.3466 \cdot N_{\text{SG}}^*$)
    - **Equation:** Equating the weight-level noise variance of the GCV-selected centered SG filter ($\frac{\sigma^2}{N_{\text{SG}}^*}$) to the trailing WLS filter ($\frac{\sigma^2 \ln 2}{2h}$) yields:

    \[
    \frac{\sigma^2}{N_{\text{SG}}^*} = \frac{\sigma^2 \ln 2}{2 h} \implies h^* = \frac{\ln 2}{2} N_{\text{SG}}^* \approx 0.3466 \cdot N_{\text{SG}}^*
    \]

    - **Principle:** Dynamically sets the trailing nowcast half-life $h^*$ to match the exact noise reduction achieved by the GCV-selected centered SG window. For $N_{\text{SG}}^* = 21\text{ days}$, $h^* \approx 7.3 \approx 7 \text{ to } 8\text{ days}$; for $N_{\text{SG}}^* = 28\text{ days}$, $h^* \approx 9.7 \approx 10\text{ days}$.

    #### (d) Trailing Lookback Window Cutoff ($W_{\text{trail}}^* = \lceil 3.32 \cdot h^* \rceil$)
    - **Equation:** For exponential weights $w_j = 2^{-j/h}$, the fraction of total weight mass captured within $W_{\text{trail}}$ days is $\eta = 1 - 2^{-W_{\text{trail}}/h}$. For $\eta = 0.90$ (90% weight mass coverage):

    \[
    W_{\text{trail}}^* = -h^* \cdot \log_2(1 - 0.90) = -\log_2(0.10) \cdot h^* \approx 3.32 \cdot h^*
    \]

    - **Principle:** Captures $90\%$ of the total exponential weight mass while truncating negligible weights ($w_j < 0.10$) from months ago. For $h^* = 8\text{ days}$, $W_{\text{trail}}^* \approx 27 \text{ to } 28\text{ days}$.

    #### (e) WLS Confidence Interval ($1.96 \cdot SE$)
    - **Equation:** $\text{CI}_{95\%} = \hat{\beta}_t \pm z_{0.975} \cdot SE(\hat{\beta}_t)$ where $z_{0.975} = 1.96$.
    - **Principle:** Standard two-sided 95% Gaussian coverage interval for local WLS slope estimates.

    ---

    ### Summary Table: Parameter Derivation Rules

    | UI Parameter | Default Value Rule | Governing Equation / Principle |
    | :--- | :--- | :--- |
    | **SG Polynomial Order ($m$)** | $2$ (Quadratic) | Taylor expansion order balancing local acceleration ($w''$) & noise variance |
    | **Min SG Window ($N_{\text{min}}$)** | $7\text{ days}$ | One full 7-day weekly lifestyle cycle |
    | **Max SG Window ($N_{\text{max}}$)** | $\min(45, \lfloor N_{\text{total}}/2 \rfloor)$ | GCV degree-of-freedom denominator stability |
    | **Recency Half-Life ($h^*$)** | $\mathrm{round}(0.3466 \cdot N_{\text{SG}}^*)$ | Level noise variance equivalence to GCV-selected $N_{\text{SG}}^*$ |
    | **Trailing Window ($W_{\text{trail}}^*$)** | $\mathrm{round}(3.32 \cdot h^*)$ | $90\%$ exponential weight mass coverage horizon ($\eta = 0.90$) |
    | **Uncertainty Interval** | $95\%$ Confidence ($1.96 \cdot SE$) | Standard two-sided Gaussian coverage factor $z_{0.975}$ |
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
    ## 4. Edge Handling & Citations

    - **Centered SG Historical Rate:** Available only for interior days with a full symmetric window ($\ge M$ days from either end). Set to `NaN` near edges because future observations are required.
    - **SG Boundary Derivative (Diagnostic Only):** SciPy's `mode="interp"` evaluates a single boundary polynomial $p(t) = a + bt + ct^2$ at the edges, making its derivative $p'(t) = b + 2ct$ a linear segment across the boundary. This is a structural property of evaluating a fixed boundary polynomial, not evidence of a linearly changing weight loss rate.
    - **Trailing Causal Nowcast:** Uses exponential recency weighting ($w_j = 2^{-j/h}$) over past observations through date $t$ only, providing a real-time nowcast that extends through today with a 95% model-based WLS confidence band.

    ### References & Citations

    1. **Walker, John** (1990). *The Hacker's Diet: How to lose weight and hair through stress and poor eating*.
       URL: [https://www.fourmilab.ch/hackdiet/](https://www.fourmilab.ch/hackdiet/)
       *(Pioneered exponentially weighted moving averages $w_j = 2^{-j/h}$ with $h \approx 7\text{--}10$ days for daily body-weight tracking to filter out water fluctuations without lag).*
    2. **Cleveland, W. S.** (1979). *Robust Locally Weighted Regression and Smoothing Scatterplots*. Journal of the American Statistical Association, 74(368), 829–836.
       DOI: [10.1080/01621459.1979.10481038](https://doi.org/10.1080/01621459.1979.10481038)
    3. **Wang, Y. et al.** (2015). *Derivative Estimation Based on Difference Sequence via Locally Weighted Least Squares Regression*. Journal of Machine Learning Research, 16, 2617–2641.
       URL: [https://jmlr.org/papers/v16/wang15a.html](https://jmlr.org/papers/v16/wang15a.html)
    4. **Orsama, A. L. et al.** (2014). *Weight Rhythms: Weight Increases during Weekends and Decreases during Weekdays*. Obesity Facts, 7(1), 36–47.
       DOI: [10.1159/000358801](https://doi.org/10.1159/000358801) | [PMC5644907](https://pmc.ncbi.nlm.nih.gov/articles/PMC5644907/)
    5. **Durbin, J., & Koopman, S. J.** (2012). *Time Series Analysis by State Space Methods*. Oxford University Press.
       DOI: [10.1093/acprof:oso/9780199641178.001.0001](https://doi.org/10.1093/acprof:oso/9780199641178.001.0001)
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


@app.cell(hide_code=True)
def _():
    import numpy as np
    import pandas as pd
    import altair as alt
    from scipy.signal import savgol_filter
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import marimo as mo

    def compute_trailing_wls(df, weight_col="weight", window_days=28, half_life_days=10):
        """
        Computes rolling trailing weighted local-linear regression for each row in df.
        For day t, uses only observations at or before t (causal nowcast).
        Model: y_{t-j} = alpha - beta * j + eps_{t-j}, where j >= 0 is days back.
        Weight: w_j = 2^(-j / half_life).
        """
        n = len(df)
        weights = df[weight_col].to_numpy()

        trailing_level = np.full(n, np.nan)
        trailing_daily_rate = np.full(n, np.nan)
        trailing_weekly_rate = np.full(n, np.nan)
        trailing_daily_se = np.full(n, np.nan)
        trailing_weekly_se = np.full(n, np.nan)
        trailing_rate_lower = np.full(n, np.nan)
        trailing_rate_upper = np.full(n, np.nan)

        for i in range(n):
            start_idx = max(0, i - window_days + 1)
            sub_weights = weights[start_idx : i + 1]
            m = len(sub_weights)
            if m < 3:
                continue

            j_vec = np.arange(m - 1, -1, -1, dtype=float)
            w_vec = 2.0 ** (-j_vec / float(half_life_days))

            X = np.column_stack([np.ones(m), -j_vec])
            W = np.diag(w_vec)

            XTW = X.T @ W
            XTWX = XTW @ X

            try:
                inv_XTWX = np.linalg.inv(XTWX)
                beta_vec = inv_XTWX @ XTW @ sub_weights

                alpha_hat = beta_vec[0]
                daily_beta = beta_vec[1]

                preds = X @ beta_vec
                resids = sub_weights - preds
                sigma2 = np.sum(w_vec * (resids ** 2)) / np.sum(w_vec)

                cov_beta = inv_XTWX * sigma2
                daily_se = np.sqrt(max(0.0, cov_beta[1, 1]))

                weekly_beta = daily_beta * 7.0
                weekly_se = daily_se * 7.0

                trailing_level[i] = alpha_hat
                trailing_daily_rate[i] = daily_beta
                trailing_weekly_rate[i] = weekly_beta
                trailing_daily_se[i] = daily_se
                trailing_weekly_se[i] = weekly_se
                trailing_rate_lower[i] = weekly_beta - 1.96 * weekly_se
                trailing_rate_upper[i] = weekly_beta + 1.96 * weekly_se
            except np.linalg.LinAlgError:
                pass

        return pd.DataFrame({
            "trailing_level": trailing_level,
            "trailing_daily_rate": trailing_daily_rate,
            "trailing_weekly_rate": trailing_weekly_rate,
            "trailing_daily_se": trailing_daily_se,
            "trailing_weekly_se": trailing_weekly_se,
            "trailing_rate_lower_95": trailing_rate_lower,
            "trailing_rate_upper_95": trailing_rate_upper,
        })


    return (
        alt,
        compute_trailing_wls,
        go,
        make_subplots,
        mo,
        np,
        pd,
        savgol_filter,
    )


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
        label=f"Inspection Date Slider ({_d_start} — {_d_end})",
        full_width=True,
    )
    return (time_slider,)


@app.cell(hide_code=True)
def _(mo):
    poly_order = mo.ui.dropdown(options=["1", "2", "3"], value="2", label="SG polynomial order")

    min_window = mo.ui.number(start=5, stop=61, step=2, value=7, label="Smallest SG window (days)")
    max_window = mo.ui.number(start=9, stop=91, step=2, value=45, label="Largest SG window (days)")

    rate_window_days = mo.ui.slider(start=7, stop=60, step=1, value=28, label="Trailing Rate Window (days)")
    rate_half_life_days = mo.ui.slider(start=3, stop=30, step=1, value=10, label="Recency Half-Life (days)")

    mo.vstack([
        mo.hstack([poly_order, min_window, max_window], gap=2),
        mo.hstack([rate_window_days, rate_half_life_days], gap=2),
    ])
    return (
        max_window,
        min_window,
        poly_order,
        rate_half_life_days,
        rate_window_days,
    )


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
def weight_and_rate_cell(go, make_subplots, mo, np, results_df, time_slider):
    _idx = int(time_slider.value)
    _sel_row = results_df.iloc[_idx]
    _sel_date = _sel_row["date"]

    # Unified color palette for traces, markers, and readout text
    _raw_color = "#4682b4"  # Steel blue matching Raw Weight
    _sg_weight_color = "crimson"  # Crimson matching SG Smoothed Weight
    _sg_rate_color = "#1d4ed8"  # Royal blue matching Centered SG Retrospective Rate
    _trailing_rate_color = "#059669"  # Emerald green matching Trailing WLS Causal Nowcast
    _sg_edge_rate_color = "#f97316"  # Orange matching SG Boundary Derivative Diagnostic

    _fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.10,
        subplot_titles=(
            "1. Raw Weight vs. SG-Smoothed Weight Trend",
            "2. Weekly Rate of Weight Change: Centered SG Retrospective vs. Trailing Causal Nowcast",
        ),
    )

    # --- Subplot 1: Weight ---
    _fig.add_trace(
        go.Scatter(
            x=results_df["date"],
            y=results_df["weight"],
            mode="lines+markers",
            name="Raw Weight",
            line=dict(color="rgba(70, 130, 180, 0.4)", width=1.5),
            marker=dict(color=_raw_color, size=4),
            hovertemplate="Date: %{x|%Y-%m-%d}<br>Raw Weight: %{y:.1f} lbs<extra></extra>",
        ),
        row=1,
        col=1,
    )

    # Main Centered SG Smoothed Weight (Solid Crimson)
    _fig.add_trace(
        go.Scatter(
            x=results_df["date"],
            y=results_df["sg_weight_centered"],
            mode="lines",
            name="Centered SG Weight",
            line=dict(color=_sg_weight_color, width=2.5),
            hovertemplate="Date: %{x|%Y-%m-%d}<br>Centered SG Weight: %{y:.2f} lbs<extra></extra>",
        ),
        row=1,
        col=1,
    )

    # Boundary SG Smoothed Weight (Dashed Crimson, diagnostic)
    _fig.add_trace(
        go.Scatter(
            x=results_df["date"],
            y=results_df["sg_weight_full"],
            mode="lines",
            name="Provisional SG Edge Weight",
            line=dict(color=_sg_weight_color, width=1.5, dash="dash"),
            opacity=0.6,
            hovertemplate="Date: %{x|%Y-%m-%d}<br>Edge SG Weight: %{y:.2f} lbs<extra></extra>",
        ),
        row=1,
        col=1,
    )

    # Selected Date Marker on Subplot 1
    _fig.add_trace(
        go.Scatter(
            x=[_sel_date],
            y=[_sel_row["smoothed_weight"]],
            mode="markers",
            name="Selected Date Weight",
            marker=dict(
                color=_sg_weight_color,
                size=10,
                symbol="diamond",
                line=dict(color="white", width=1.5),
            ),
            showlegend=False,
            hovertemplate="Selected Date: %{x|%Y-%m-%d}<br>Smoothed: %{y:.2f} lbs<extra></extra>",
        ),
        row=1,
        col=1,
    )
    _fig.add_vline(
        x=_sel_date, line_dash="dot", line_color="#64748b", line_width=1.5, row=1, col=1
    )

    # --- Subplot 2: Rate of Change ---
    _fig.add_hline(
        y=0, line_dash="dash", line_color="gray", line_width=1.0, row=2, col=1
    )

    # 1. Primary Centered SG Historical Rate (Solid Blue)
    _fig.add_trace(
        go.Scatter(
            x=results_df["date"],
            y=results_df["sg_weekly_rate_centered"],
            mode="lines",
            name="Centered SG Historical Rate (Retrospective)",
            line=dict(color=_sg_rate_color, width=2.5),
            hovertemplate="Date: %{x|%Y-%m-%d}<br>Centered SG Rate: %{y:.2f} lbs/wk<extra></extra>",
        ),
        row=2,
        col=1,
    )

    # 2. Trailing Causal WLS Nowcast Rate (Solid Emerald Green)
    _fig.add_trace(
        go.Scatter(
            x=results_df["date"],
            y=results_df["trailing_weekly_rate"],
            mode="lines",
            name="Trailing WLS Current Rate (Causal Nowcast)",
            line=dict(color=_trailing_rate_color, width=2.5),
            hovertemplate="Date: %{x|%Y-%m-%d}<br>Trailing Rate: %{y:.2f} lbs/wk<extra></extra>",
        ),
        row=2,
        col=1,
    )

    # 3. Trailing WLS 95% Confidence Band
    _fig.add_trace(
        go.Scatter(
            x=results_df["date"].tolist() + results_df["date"].tolist()[::-1],
            y=results_df["trailing_rate_upper_95"].tolist()
            + results_df["trailing_rate_lower_95"].tolist()[::-1],
            fill="toself",
            fillcolor="rgba(16, 185, 129, 0.15)",
            line=dict(color="rgba(255,255,255,0)"),
            name="Trailing Rate 95% CI Band",
            hoverinfo="skip",
        ),
        row=2,
        col=1,
    )

    # 4. Diagnostic SG Boundary Derivative
    _fig.add_trace(
        go.Scatter(
            x=results_df["date"],
            y=results_df["sg_weekly_rate_full"],
            mode="lines",
            name="SG Boundary Derivative (Diagnostic Only)",
            line=dict(color=_sg_edge_rate_color, width=1.2, dash="dash"),
            opacity=0.5,
            hovertemplate="Date: %{x|%Y-%m-%d}<br>SG Edge Derivative: %{y:.2f} lbs/wk (linear diagnostic)<extra></extra>",
        ),
        row=2,
        col=1,
    )

    # Determine active rate value and marker color on Subplot 2
    _has_centered = not np.isnan(_sel_row["sg_weekly_rate_centered"])
    _sel_rate_val = (
        _sel_row["sg_weekly_rate_centered"]
        if _has_centered
        else _sel_row["trailing_weekly_rate"]
    )
    _sel_rate_marker_color = _sg_rate_color if _has_centered else _trailing_rate_color

    # Selected Date Marker on Subplot 2
    _fig.add_trace(
        go.Scatter(
            x=[_sel_date],
            y=[_sel_rate_val],
            mode="markers",
            name="Selected Date Rate",
            marker=dict(
                color=_sel_rate_marker_color,
                size=10,
                symbol="diamond",
                line=dict(color="white", width=1.5),
            ),
            showlegend=False,
        ),
        row=2,
        col=1,
    )
    _fig.add_vline(
        x=_sel_date, line_dash="dot", line_color="#64748b", line_width=1.5, row=2, col=1
    )

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
            font=dict(size=11),
        ),
    )

    _fig.update_yaxes(title_text="Weight (lbs)", row=1, col=1)
    _fig.update_yaxes(title_text="Rate (lbs/week)", row=2, col=1)
    _fig.update_xaxes(title_text="Date", row=2, col=1)

    # Status & Readout Banner using line indicators matching plot trace styles
    _is_edge = _sel_row["is_sg_edge"]

    _sg_status_str = (
        f'<span style="color:{_sg_rate_color}; font-weight:bold;">{_sel_row["sg_weekly_rate_centered"]:+.2f} lbs/wk</span> (Centered Retrospective)'
        if _has_centered
        else f'<span style="color:{_sg_edge_rate_color}; font-weight:bold;">{_sel_row["sg_weekly_rate_full"]:+.2f} lbs/wk</span> (SG Edge Diagnostic — linear boundary fit)'
    )

    _line_date = '<svg width="20" height="12" style="vertical-align: middle; display: inline-block; margin-right: 4px;"><line x1="0" y1="6" x2="20" y2="6" stroke="#64748b" stroke-width="2" stroke-dasharray="2,2"/></svg>'
    _line_raw = f'<svg width="20" height="12" style="vertical-align: middle; display: inline-block; margin-right: 4px;"><line x1="0" y1="6" x2="20" y2="6" stroke="{_raw_color}" stroke-width="2.5"/></svg>'
    _line_sg_weight = f'<svg width="20" height="12" style="vertical-align: middle; display: inline-block; margin-right: 4px;"><line x1="0" y1="6" x2="20" y2="6" stroke="{_sg_weight_color}" stroke-width="2.5"/></svg>'
    _line_trailing = f'<svg width="20" height="12" style="vertical-align: middle; display: inline-block; margin-right: 4px;"><line x1="0" y1="6" x2="20" y2="6" stroke="{_trailing_rate_color}" stroke-width="2.5"/></svg>'

    _curr_dash_attr = 'stroke-dasharray="4,3"' if not _has_centered else ''
    _curr_sg_color = _sg_rate_color if _has_centered else _sg_edge_rate_color
    _line_sg_rate = f'<svg width="20" height="12" style="vertical-align: middle; display: inline-block; margin-right: 4px;"><line x1="0" y1="6" x2="20" y2="6" stroke="{_curr_sg_color}" stroke-width="2.5" {_curr_dash_attr}/></svg>'

    _readout_ui = mo.md(f"""
    <div style="background: #f8fafc; padding: 10px 14px; border-radius: 8px; border: 1px solid #cbd5e1; font-family: system-ui, sans-serif; font-size: 13px; color: #0f172a; margin-top: 4px;">
      <div style="display: flex; flex-wrap: wrap; gap: 16px; justify-content: space-between; font-weight: 600; margin-bottom: 6px;">
        <div>{_line_date}Date: {_sel_date.strftime('%b %d, %Y')}</div>
        <div>{_line_raw}Raw Weight: <span style="color:{_raw_color}; font-weight:bold;">{_sel_row['weight']:.1f} lbs</span></div>
        <div>{_line_sg_weight}SG Smoothed Weight: <span style="color:{_sg_weight_color}; font-weight:bold;">{_sel_row['smoothed_weight']:.2f} lbs</span></div>
      </div>
      <div style="display: flex; flex-wrap: wrap; gap: 16px; justify-content: space-between; border-top: 1px solid #e2e8f0; padding-top: 6px;">
        <div>{_line_trailing}<strong>Trailing WLS Causal Nowcast:</strong> <span style="color:{_trailing_rate_color}; font-weight:bold;">{_sel_row['trailing_weekly_rate']:+.2f} lbs/wk</span> (95% CI: [{_sel_row['trailing_rate_lower_95']:+.2f}, {_sel_row['trailing_rate_upper_95']:+.2f}])</div>
        <div>{_line_sg_rate}<strong>SG Retrospective Rate:</strong> {_sg_status_str}</div>
      </div>
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
def _(
    best_window,
    compute_trailing_wls,
    df_raw,
    np,
    poly_order,
    rate_half_life_days,
    rate_window_days,
    savgol_filter,
):
    _polyorder = int(poly_order.value)
    _w = best_window

    weight_arr = df_raw["weight"].to_numpy()

    # Full SG estimates (mode="interp")
    sg_weight_full = savgol_filter(weight_arr, window_length=_w, polyorder=_polyorder, deriv=0, mode="interp")
    sg_daily_rate_full = savgol_filter(weight_arr, window_length=_w, polyorder=_polyorder, deriv=1, mode="interp")
    sg_weekly_rate_full = sg_daily_rate_full * 7.0

    half_window = _w // 2

    # Define symmetric interior vs edge boolean masks
    is_centered_sg = (df_raw.index >= half_window) & (df_raw.index < len(df_raw) - half_window)
    is_sg_edge = ~is_centered_sg

    results_df = df_raw.copy()
    results_df["sg_weight_full"] = sg_weight_full
    results_df["sg_daily_rate_full"] = sg_daily_rate_full
    results_df["sg_weekly_rate_full"] = sg_weekly_rate_full

    # Centered-only series (NaN outside symmetric interior)
    results_df["sg_weight_centered"] = np.where(is_centered_sg, sg_weight_full, np.nan)
    results_df["sg_weekly_rate_centered"] = np.where(is_centered_sg, sg_weekly_rate_full, np.nan)
    results_df["is_centered_sg"] = is_centered_sg
    results_df["is_sg_edge"] = is_sg_edge

    # Backward compatibility aliases
    results_df["smoothed_weight"] = sg_weight_full
    results_df["daily_slope"] = sg_daily_rate_full
    results_df["weekly_rate"] = sg_weekly_rate_full
    results_df["is_edge_estimate"] = is_sg_edge

    # Compute trailing causal WLS nowcast
    _wls_df = compute_trailing_wls(
        df_raw,
        weight_col="weight",
        window_days=int(rate_window_days.value),
        half_life_days=float(rate_half_life_days.value),
    )

    for _col in _wls_df.columns:
        results_df[_col] = _wls_df[_col]
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


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
