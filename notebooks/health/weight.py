# /// script
# dependencies = [
#     "altair==6.2.2",
#     "marimo>=0.23.3",
#     "matplotlib==3.11.1",
#     "numpy==2.5.2",
#     "pandas==3.0.5",
#     "plotly==7.0.0",
#     "pyarrow",
#     "playwright",
#     "scipy==1.18.1",
# ]
# requires-python = ">=3.12"
# ///

import marimo

__generated_with = "0.25.2"
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

    On startup, this notebook loads the most recently modified CSV in
    `notebooks/health/dat`. Click **Download latest Garmin weight CSV** to open
    Garmin Connect in a Chromium window and automate **Weight → 1 Year → Menu →
    Export CSV**. If Garmin requests sign-in or MFA, complete it in that window;
    the notebook waits and then continues. The downloaded CSV is saved in `dat`
    as `Weight_YYMMDD.csv` (with a numeric suffix for another export the same
    day) and plotted immediately.

    The first run installs Playwright's Chromium browser if needed. Its local
    sign-in session is kept outside the repository, under
    `%LOCALAPPDATA%\MarimoGarminWeight` on Windows or
    `~/MarimoGarminWeight` elsewhere; no password or MFA code is read by the
    notebook.

    By default, the download starts only when you click the button. To start
    automatically when launching the notebook, run:

    `marimo run notebooks/health/weight.py -- --update-latest true`

    Omit the option or pass `--update-latest false` to wait for the button.
    The CSV needs a date column and a weight column; Garmin's additional body
    composition columns are used when present.
    """)
    return


@app.cell
def _(mo):
    download_latest_button = mo.ui.run_button(
        label="Download latest Garmin weight CSV",
        tooltip="Open Garmin Connect and download the one-year weight export.",
    )
    download_latest_button
    return (download_latest_button,)


@app.cell(hide_code=True)
def _():
    import os as _os
    import re as _re
    import shutil as _shutil
    import subprocess as _subprocess
    import sys as _sys
    import time as _time
    import uuid as _uuid
    from datetime import date as _date
    from pathlib import Path as _Path

    from playwright.sync_api import sync_playwright

    def download_garmin_weight_csv(data_dir, progress):
        data_dir.mkdir(parents=True, exist_ok=True)
        profile_parent = _Path(
            _os.environ.get("LOCALAPPDATA", _Path.home())
        ) / "MarimoGarminWeight"
        profile_parent.mkdir(parents=True, exist_ok=True)
        profile_dir = profile_parent / "browser-profile"

        with sync_playwright() as playwright:
            _chrome_exe = _Path(
                _os.environ.get("PROGRAMFILES", r"C:\Program Files")
            ) / "Google/Chrome/Application/chrome.exe"
            _launch_options = {}
            if _chrome_exe.is_file():
                _launch_options["channel"] = "chrome"
            elif not _Path(playwright.chromium.executable_path).is_file():
                progress.update(
                    increment=0,
                    title="Installing Chromium",
                    subtitle="Playwright is downloading the browser needed for Garmin Connect.",
                )
                _subprocess.run(
                    [_sys.executable, "-m", "playwright", "install", "chromium"],
                    check=True,
                )

            progress.update(
                title="Opening Garmin Connect",
                subtitle="A separate browser window is opening with a local browser profile.",
            )
            browser_context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=False,
                accept_downloads=True,
                no_viewport=True,
                args=["--start-maximized", "--window-position=0,0"],
                ignore_default_args=["--disable-blink-features=AutomationControlled"],
                **_launch_options,
            )
            try:
                page = (
                    browser_context.pages[0]
                    if browser_context.pages
                    else browser_context.new_page()
                )
                page.bring_to_front()
                page.goto(
                    "https://connect.garmin.com/app/home",
                    wait_until="domcontentloaded",
                    timeout=60_000,
                )

                progress.update(
                    title="Waiting for Garmin Connect sign-in",
                    subtitle="If prompted, sign in and complete MFA in the Chromium window.",
                )
                login_deadline = _time.monotonic() + 900
                last_login_update = _time.monotonic()
                while _time.monotonic() < login_deadline:
                    page_url = page.url.lower()
                    password_field = page.locator('input[type="password"]')
                    if "/app/" in page_url and password_field.count() == 0:
                        break
                    if _time.monotonic() - last_login_update >= 5:
                        progress.update(
                            increment=0,
                            title="Waiting for Garmin sign-in",
                            subtitle=(
                                "Complete sign-in/MFA in the Chromium window; "
                                "the notebook will continue automatically."
                            ),
                        )
                        last_login_update = _time.monotonic()
                    page.wait_for_timeout(1000)
                else:
                    raise TimeoutError(
                        "Garmin sign-in was not completed within 15 minutes. "
                        "Click the download button to try again."
                    )

                def click_first_visible(
                    candidates,
                    description,
                    *,
                    timeout_ms=30_000,
                    required=True,
                ):
                    deadline = _time.monotonic() + timeout_ms / 1000
                    while _time.monotonic() < deadline:
                        for candidate in candidates:
                            for index in range(candidate.count()):
                                element = candidate.nth(index)
                                if not element.is_visible():
                                    continue
                                for _attempt in ("normal", "force", "dom"):
                                    try:
                                        if _attempt == "normal":
                                            element.click(timeout=3_000)
                                        elif _attempt == "force":
                                            element.click(timeout=3_000, force=True)
                                        else:
                                            element.dispatch_event("click")
                                        return True
                                    except Exception:
                                        continue
                        page.wait_for_timeout(250)
                    if required:
                        raise RuntimeError(
                            f"Could not find the Garmin {description} control. "
                            "Garmin may have changed its interface."
                        )
                    return False

                progress.update(
                    title="Opening the Weight page",
                    subtitle="Navigating through Garmin Connect's Health Stats.",
                )
                page.goto(
                    "https://connect.garmin.com/app/weight",
                    wait_until="domcontentloaded",
                    timeout=60_000,
                )

                progress.update(
                    title="Selecting the one-year range",
                    subtitle="Opening Weight history and selecting 1 Year.",
                )
                click_first_visible(
                    [
                        page.get_by_role("tab", name="1 Year", exact=True),
                        page.get_by_role("button", name="1 Year", exact=True),
                        page.get_by_text("1 Year", exact=True),
                    ],
                    "1 Year",
                )

                progress.update(
                    title="Starting the CSV export",
                    subtitle="Opening the Weight menu and selecting Export CSV.",
                )
                click_first_visible(
                    [
                        page.locator(
                            "button[class*='Button_small'][class*='Button_iconButton']"
                        ),
                    ],
                    "three-dot menu",
                )

                progress.update(
                    title="Downloading Garmin's CSV",
                    subtitle="Waiting for the browser download to finish.",
                )
                with page.expect_download(timeout=120_000) as download_event:
                    click_first_visible(
                        [
                            page.get_by_role("menuitem", name="Export CSV", exact=True),
                            page.get_by_text("Export CSV", exact=True),
                        ],
                        "Export CSV",
                    )
                download = download_event.value
                if not download.suggested_filename.lower().endswith(".csv"):
                    raise ValueError(
                        f"Garmin returned `{download.suggested_filename}` instead of a CSV file."
                    )

                temp_path = data_dir / f".garmin-download-{_uuid.uuid4().hex}.tmp"
                try:
                    download.save_as(str(temp_path))
                    if not temp_path.is_file() or temp_path.stat().st_size == 0:
                        raise ValueError("Garmin's downloaded CSV is empty.")

                    date_stamp = _date.today().strftime("%y%m%d")
                    sequence = 0
                    while True:
                        suffix = "" if sequence == 0 else f"_{sequence:02d}"
                        destination = data_dir / f"Weight_{date_stamp}{suffix}.csv"
                        file_created = False
                        try:
                            with destination.open("xb") as target_file:
                                file_created = True
                                with temp_path.open("rb") as source_file:
                                    _shutil.copyfileobj(source_file, target_file)
                            break
                        except FileExistsError:
                            sequence += 1
                        except Exception:
                            if file_created:
                                destination.unlink(missing_ok=True)
                            raise
                    return destination
                finally:
                    temp_path.unlink(missing_ok=True)
            finally:
                browser_context.close()

    return (download_garmin_weight_csv,)


@app.cell(hide_code=True)
def _(download_garmin_weight_csv, download_latest_button, mo):
    from pathlib import Path

    health_dir = Path(__file__).resolve().parent
    data_dir = health_dir / "dat"
    data_dir.mkdir(parents=True, exist_ok=True)
    inFNm = ""

    auto_update = str(mo.cli_args().get("update-latest", "false")).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if auto_update or download_latest_button.value:
        with mo.status.progress_bar(
            total=7,
            title="Starting Garmin Connect export",
            subtitle="The notebook will pause for sign-in or MFA if requested.",
            show_rate=False,
            show_eta=False,
        ) as progress:
            _outcome = {}

            def _run_download():
                try:
                    _outcome["file"] = download_garmin_weight_csv(data_dir, progress)
                except BaseException as _exc:
                    _outcome["error"] = _exc

            _worker = mo.Thread(target=_run_download)
            _worker.start()
            _worker.join()
            if "error" in _outcome:
                raise _outcome["error"]
            downloaded_file = _outcome["file"]
            progress.update(
                title="Garmin CSV downloaded",
                subtitle=f"Saved as dat/{downloaded_file.name}; refreshing the plots.",
            )
        inFNm = str(downloaded_file)
        import_status = f"Downloaded and saved `dat/{downloaded_file.name}`."
    else:
        csv_files = list(data_dir.glob("*.csv"))
        if csv_files:
            latest_file = max(
                csv_files,
                key=lambda candidate: (candidate.stat().st_mtime_ns, candidate.name),
            )
            inFNm = str(latest_file)
            import_status = f"Loading the most recently updated CSV: `dat/{latest_file.name}`."
        else:
            import_status = (
                "No CSV found in `dat`. Click **Download latest Garmin weight CSV** "
                "to start the automated Garmin Connect export."
            )

    mo.md(import_status)
    return (inFNm,)


@app.cell(hide_code=True)
def _(inFNm):
    import numpy as _np
    import pandas as _pd

    import io
    import re

    # A "fragment" is a line holding only the quoted date, e.g.  " Oct 15, 2026",
    _FRAGMENT = re.compile(r'^\s*"?\s*([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4}|\d{4}-\d{2}-\d{2})\s*"?\s*,?\s*$')

    def read_garmin_weight_csv(inFNm):
        with open(inFNm, "r", encoding="utf-8-sig", newline=None) as f:
            lines = [ln.rstrip("\r\n") for ln in f if ln.strip()]

        if not lines:
            return _pd.DataFrame(columns=["date", "weight"])

        has_fragments = any(_FRAGMENT.match(ln) for ln in lines[1:])

        if has_fragments:
            header = lines[0]
            if not re.match(r'^\s*"?date"?\b', header, re.IGNORECASE):
                header = "Date," + header

            fixed = [header]
            current_date = None
            repaired = 0
            for ln in lines[1:]:
                m = _FRAGMENT.match(ln)
                if m:
                    current_date = m.group(1).strip()
                elif current_date is not None:
                    fixed.append(f'"{current_date}",' + ln.lstrip())
                    repaired += 1
                else:
                    fixed.append(ln)

            if repaired:
                print(f"{inFNm}: repaired {repaired} split record(s)")

            df = _pd.read_csv(io.StringIO("\n".join(fixed) + "\n"))
        else:
            df = _pd.read_csv(inFNm)

        cols_lower = {col: str(col).strip().lower() for col in df.columns}
        df = df.rename(columns=cols_lower)
        return df

    df_raw_file = read_garmin_weight_csv(inFNm) if inFNm else _pd.DataFrame()

    try:
        def _strip_unit(x):
            if isinstance(x, str):
                val = x.strip().rstrip("%").strip().split()[0]
                try:
                    return float(val)
                except ValueError:
                    return _np.nan
            return x

        date_col = "date" if "date" in df_raw_file.columns else ("time" if "time" in df_raw_file.columns else None)
        weight_col = None
        body_fat_col = None
        muscle_col = None
        for col in df_raw_file.columns:
            _cl = str(col).lower()
            if "weight" in _cl and weight_col is None:
                weight_col = col
            elif ("body fat" in _cl or "fat" in _cl) and body_fat_col is None:
                body_fat_col = col
            elif ("muscle" in _cl or "smm" in _cl) and muscle_col is None:
                muscle_col = col

        if date_col is not None and weight_col is not None:
            df_raw_file["date"] = _pd.to_datetime(df_raw_file[date_col], errors="coerce")
            df_raw_file["weight"] = df_raw_file[weight_col].apply(_strip_unit)
            df_raw_file["weight"] = _pd.to_numeric(df_raw_file["weight"], errors="coerce")

            if body_fat_col is not None:
                df_raw_file["body_fat"] = df_raw_file[body_fat_col].apply(_strip_unit)
                df_raw_file["body_fat"] = _pd.to_numeric(df_raw_file["body_fat"], errors="coerce")
            if muscle_col is not None:
                df_raw_file["muscle_mass"] = df_raw_file[muscle_col].apply(_strip_unit)
                df_raw_file["muscle_mass"] = _pd.to_numeric(df_raw_file["muscle_mass"], errors="coerce")

        if not df_raw_file.empty:
            df_raw_file = df_raw_file.dropna(subset=["date", "weight"]).sort_values("date").reset_index(drop=True)
            df_raw_file["date"] = df_raw_file["date"].dt.normalize()

            _agg_dict = {"weight": "mean"}
            if "body_fat" in df_raw_file:
                _agg_dict["body_fat"] = "mean"
            if "muscle_mass" in df_raw_file:
                _agg_dict["muscle_mass"] = "mean"

            df_raw_file = df_raw_file.groupby("date", as_index=False).agg(_agg_dict).sort_values("date").reset_index(drop=True)

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

            for _c in _agg_dict.keys():
                df_raw_file[_c] = df_raw_file[_c].interpolate(method="linear").bfill().ffill()

            print("Missing Points Interpolation Summary:")
            print(f"Number of missing points interpolated: {_num_missing} / {_total_points} ({_pct_missing:.2f}%)")
            print("Histogram of missing gap lengths:")
            if _gap_lengths:
                _counts = _pd.Series(_gap_lengths).value_counts().sort_index()
                for _length, _cnt in _counts.items():
                    print(f"  Gap of {_length} day(s): {_cnt} time(s)")
            else:
                print("  No missing points found.")
    except Exception as _err:
        print(f"Error processing {inFNm}: {_err}")
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
    plot_layout_mode = mo.ui.radio(
        options=["Tabs", "Stacked"],
        value="Tabs",
        label="Plot View Layout:",
        inline=True,
    )
    return (plot_layout_mode,)


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

    metric_scores = {}
    for _label, _col in (("Weight", "weight"), ("Body Fat", "body_fat"), ("Skeletal Muscle Mass", "muscle_mass")):
        if _col not in df_raw or not df_raw[_col].notna().any():
            continue
        _own_best, _, _scores = select_best_window(df_raw[_col].to_numpy(), _polyorder, _candidate_windows)
        metric_scores[_label] = (_own_best, _scores)
    return best_window, metric_scores


@app.cell(hide_code=True)
def _(
    alt,
    best_window,
    metric_scores,
    mo,
    pd,
    rate_half_life_days,
    rate_window_days,
):
    _rows = []
    for _label, (_own_best, _scores) in metric_scores.items():
        _panel_df = pd.DataFrame(_scores, columns=["window", "gcv_score"])
        _panel_df["metric"] = _label
        _panel_df["gcv_normalized"] = _panel_df["gcv_score"] / _panel_df["gcv_score"].mean()
        _rows.append(_panel_df)
    _scores_df = pd.concat(_rows, ignore_index=True)
    _own_df = pd.DataFrame(
        [{"metric": _l, "window": _b} for _l, (_b, _) in metric_scores.items()]
    )

    _color = alt.Color(
        "metric:N",
        title="Metric",
        scale=alt.Scale(domain=list(metric_scores), range=["#4682b4", "#d97706", "#16a34a"][: len(metric_scores)]),
    )
    _line = (
        alt.Chart(_scores_df)
        .mark_line(point=True)
        .encode(
            x=alt.X("window:Q", title="Window length (days)"),
            y=alt.Y("gcv_normalized:Q", title="GCV score / metric mean (lower = better)", scale=alt.Scale(zero=False)),
            color=_color,
            tooltip=[
                "metric:N",
                "window:Q",
                alt.Tooltip("gcv_score:Q", title="GCV score (raw)", format=".5g"),
                alt.Tooltip("gcv_normalized:Q", title="GCV / mean", format=".3f"),
            ],
        )
    )
    _own_rule = (
        alt.Chart(_own_df)
        .mark_rule(strokeDash=[4, 3])
        .encode(
            x="window:Q",
            color=_color,
            tooltip=["metric:N", alt.Tooltip("window:Q", title="own GCV optimum (days)")],
        )
    )
    _used_rule = (
        alt.Chart(pd.DataFrame({"window": [best_window]}))
        .mark_rule(color="red", strokeWidth=2)
        .encode(x="window:Q", tooltip=[alt.Tooltip("window:Q", title="window applied (days)")])
    )
    _chart = alt.layer(_line, _own_rule, _used_rule).properties(
        title="GCV score vs. window length (each metric normalized to its mean)", width=650, height=350
    )

    _own_text = ", ".join(f"{_l}: {_b} d" for _l, (_b, _) in metric_scores.items())
    mo.vstack(
        [
            mo.md(
                f"**Savitzky–Golay window applied to every metric: {best_window} days** "
                f"(red line, the GCV minimum for Weight). Each metric's own GCV minimum is the "
                f"dashed line in its color ({_own_text}).\n\n"
                f"**Trailing causal WLS (all metrics):** lookback window {int(rate_window_days.value)} days, "
                f"recency half-life {int(rate_half_life_days.value)} days (set by the sliders, not by GCV)."
            ),
            _chart,
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
def weight_and_rate_cell(
    go,
    make_subplots,
    mo,
    np,
    plot_layout_mode,
    rate_window_days,
    results_df,
    time_slider,
):
    _idx = int(time_slider.value)
    _sel_row = results_df.iloc[_idx]
    _sel_date = _sel_row["date"]

    # Boundary connection mask (1 point overlap at each boundary)
    _is_edge_connected = np.array(results_df["is_sg_edge"], copy=True)
    _centered_indices = np.where(results_df["is_centered_sg"])[0]
    if len(_centered_indices) > 0:
        _is_edge_connected[_centered_indices[0]] = True
        _is_edge_connected[_centered_indices[-1]] = True

    def _build_metric_chart(
        title_metric,
        unit,
        rate_unit,
        raw_vals,
        smooth_centered_vals,
        smooth_full_vals,
        rate_centered_vals,
        rate_full_vals,
        trailing_rate_vals,
        trailing_lower_vals,
        trailing_upper_vals,
        color_raw,
        color_smooth,
        color_rate,
        color_trailing,
        color_edge,
    ):
        _edge_level = np.where(_is_edge_connected, smooth_full_vals, np.nan)
        _edge_rate = np.where(_is_edge_connected, rate_full_vals, np.nan)

        _fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.10,
            subplot_titles=(
                f"1. Raw {title_metric} vs. SG-Smoothed Trend",
                f"2. Weekly Rate of {title_metric} Change: Centered SG Retrospective vs. Trailing Causal Nowcast",
            ),
        )

        # --- Subplot 1: Level ---
        # 1. Raw Data Scatter/Line
        _fig.add_trace(
            go.Scatter(
                x=results_df["date"],
                y=raw_vals,
                mode="lines+markers",
                name=f"Raw {title_metric}",
                legendrank=100,
                line=dict(color=color_raw, width=1.5),
                opacity=0.6,
                marker=dict(color=color_raw, size=4),
                hovertemplate=f"Date: %{{x|%Y-%m-%d}}<br>Raw {title_metric}: %{{y:.1f}} {unit}<extra></extra>",
                hoverlabel=dict(bgcolor=color_raw, font=dict(color="white")),
            ),
            row=1,
            col=1,
        )

        # 2. Provisional Boundary SG Level (Dashed, edge intervals only)
        _fig.add_trace(
            go.Scatter(
                x=results_df["date"],
                y=_edge_level,
                mode="lines",
                name=f"Provisional SG Edge {title_metric}",
                legendrank=120,
                line=dict(color=color_smooth, width=1.5, dash="dash"),
                opacity=0.6,
                hovertemplate=f"Date: %{{x|%Y-%m-%d}}<br>Edge SG {title_metric}: %{{y:.2f}} {unit}<extra></extra>",
                hoverlabel=dict(
                    bgcolor=color_smooth, font=dict(color="white")
                ),
            ),
            row=1,
            col=1,
        )

        # 3. Main Centered SG Smoothed Level (Solid, rendered on top of edge line)
        _fig.add_trace(
            go.Scatter(
                x=results_df["date"],
                y=smooth_centered_vals,
                mode="lines",
                name=f"Centered SG {title_metric}",
                legendrank=110,
                line=dict(color=color_smooth, width=2.5),
                hovertemplate=f"Date: %{{x|%Y-%m-%d}}<br>Centered SG {title_metric}: %{{y:.2f}} {unit}<extra></extra>",
                hoverlabel=dict(
                    bgcolor=color_smooth, font=dict(color="white")
                ),
            ),
            row=1,
            col=1,
        )

        # Selected Date Marker on Subplot 1
        _sel_smooth_val = float(smooth_full_vals[_idx])
        _fig.add_trace(
            go.Scatter(
                x=[_sel_date],
                y=[_sel_smooth_val],
                mode="markers",
                name=f"Selected Date {title_metric}",
                marker=dict(
                    color=color_smooth,
                    size=10,
                    symbol="diamond",
                    line=dict(color="white", width=1.5),
                ),
                showlegend=False,
                hovertemplate=f"Selected Date: %{{x|%Y-%m-%d}}<br>Smoothed: %{{y:.2f}} {unit}<extra></extra>",
                hoverlabel=dict(
                    bgcolor=color_smooth, font=dict(color="white")
                ),
            ),
            row=1,
            col=1,
        )
        _fig.add_vline(
            x=_sel_date,
            line_dash="dot",
            line_color="#64748b",
            line_width=1.5,
            row=1,
            col=1,
        )

        # --- Subplot 2: Rate of Change ---
        _fig.add_hline(
            y=0,
            line_dash="dash",
            line_color="gray",
            line_width=1.0,
            row=2,
            col=1,
        )

        # 1. Diagnostic SG Boundary Derivative (Dashed, edge intervals only, added first)
        _fig.add_trace(
            go.Scatter(
                x=results_df["date"],
                y=_edge_rate,
                mode="lines",
                name="SG Boundary Derivative (Diagnostic Only)",
                legendrank=230,
                line=dict(color=color_edge, width=1.2, dash="dash"),
                opacity=0.6,
                hovertemplate=f"Date: %{{x|%Y-%m-%d}}<br>SG Edge Derivative: %{{y:.2f}} {rate_unit} (linear diagnostic)<extra></extra>",
                hoverlabel=dict(bgcolor=color_edge, font=dict(color="white")),
            ),
            row=2,
            col=1,
        )

        # 2. Trailing WLS 95% Confidence Band
        _ci_x = results_df["date"].tolist() + results_df["date"].tolist()[::-1]
        _ci_y = (
            trailing_upper_vals.tolist() + trailing_lower_vals.tolist()[::-1]
        )
        _fig.add_trace(
            go.Scatter(
                x=_ci_x,
                y=_ci_y,
                fill="toself",
                fillcolor="rgba(16, 185, 129, 0.15)",
                line=dict(color="rgba(255,255,255,0)"),
                name="Trailing Rate 95% CI Band",
                legendrank=220,
                hoverinfo="skip",
            ),
            row=2,
            col=1,
        )

        # 3. Trailing Causal WLS Nowcast Rate (Solid)
        _fig.add_trace(
            go.Scatter(
                x=results_df["date"],
                y=trailing_rate_vals,
                mode="lines",
                name="Trailing WLS Current Rate (Causal Nowcast)",
                legendrank=210,
                line=dict(color=color_trailing, width=2.5),
                hovertemplate=f"Date: %{{x|%Y-%m-%d}}<br>Trailing Rate: %{{y:.2f}} {rate_unit}<extra></extra>",
                hoverlabel=dict(
                    bgcolor=color_trailing, font=dict(color="white")
                ),
            ),
            row=2,
            col=1,
        )

        # 4. Primary Centered SG Historical Rate (Solid, on top)
        _fig.add_trace(
            go.Scatter(
                x=results_df["date"],
                y=rate_centered_vals,
                mode="lines",
                name="Centered SG Historical Rate (Retrospective)",
                legendrank=200,
                line=dict(color=color_rate, width=2.5),
                hovertemplate=f"Date: %{{x|%Y-%m-%d}}<br>Centered SG Rate: %{{y:.2f}} {rate_unit}<extra></extra>",
                hoverlabel=dict(bgcolor=color_rate, font=dict(color="white")),
            ),
            row=2,
            col=1,
        )

        # Selected Date Marker on Subplot 2
        _has_c_rate = not np.isnan(rate_centered_vals[_idx])
        _sel_rate_num = (
            float(rate_centered_vals[_idx])
            if _has_c_rate
            else float(trailing_rate_vals[_idx])
        )
        _sel_rate_marker_color = color_rate if _has_c_rate else color_trailing

        _fig.add_trace(
            go.Scatter(
                x=[_sel_date],
                y=[_sel_rate_num],
                mode="markers",
                name=f"Selected Date {title_metric} Rate",
                marker=dict(
                    color=_sel_rate_marker_color,
                    size=10,
                    symbol="diamond",
                    line=dict(color="white", width=1.5),
                ),
                showlegend=False,
                hovertemplate=(
                    f"Selected Date: %{{x|%Y-%m-%d}}<br>"
                    + (
                        f"Centered SG Rate: %{{y:.2f}} {rate_unit}"
                        if _has_c_rate
                        else f"Trailing Rate: %{{y:.2f}} {rate_unit}"
                    )
                    + "<extra></extra>"
                ),
                hoverlabel=dict(
                    bgcolor=_sel_rate_marker_color, font=dict(color="white")
                ),
            ),
            row=2,
            col=1,
        )
        _fig.add_vline(
            x=_sel_date,
            line_dash="dot",
            line_color="#64748b",
            line_width=1.5,
            row=2,
            col=1,
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
            hoverlabel=dict(
                font=dict(
                    family="system-ui, -apple-system, sans-serif",
                    size=12,
                    color="white",
                ),
                bordercolor="rgba(255, 255, 255, 0.4)",
            ),
        )

        _fig.update_yaxes(title_text=f"{title_metric} ({unit})", row=1, col=1)
        _fig.update_yaxes(title_text=f"Rate ({rate_unit})", row=2, col=1)
        _fig.update_xaxes(title_text="Date", row=2, col=1)

        # Summary calculations for this metric
        _start_val = float(smooth_full_vals[0])
        _end_val = float(smooth_full_vals[_idx])
        _diff_val = _end_val - _start_val
        _pct_val = (_diff_val / _start_val * 100.0) if _start_val != 0 else 0.0
        _rate_wk = (_diff_val / _weeks_elapsed) if _weeks_elapsed > 0 else 0.0

        # Readout UI
        _sel_raw_val = float(raw_vals[_idx])
        _sel_full_rate = float(rate_full_vals[_idx])
        _sel_trailing_rate = float(trailing_rate_vals[_idx])
        _sel_trailing_l = float(trailing_lower_vals[_idx])
        _sel_trailing_u = float(trailing_upper_vals[_idx])

        _sg_status = (
            f'<span style="color:{color_rate}; font-weight:bold;">{rate_centered_vals[_idx]:+.2f} {rate_unit}</span> (Centered Retrospective)'
            if _has_c_rate
            else f'<span style="color:{color_edge}; font-weight:bold;">{_sel_full_rate:+.2f} {rate_unit}</span> (SG Edge Diagnostic — linear boundary fit)'
        )

        _line_date = '<svg width="20" height="12" style="vertical-align: middle; display: inline-block; margin-right: 4px;"><line x1="0" y1="6" x2="20" y2="6" stroke="#64748b" stroke-width="2" stroke-dasharray="2,2"/></svg>'
        _line_raw_svg = f'<svg width="20" height="12" style="vertical-align: middle; display: inline-block; margin-right: 4px;"><line x1="0" y1="6" x2="20" y2="6" stroke="{color_raw}" stroke-width="2.5"/></svg>'
        _line_smooth_svg = f'<svg width="20" height="12" style="vertical-align: middle; display: inline-block; margin-right: 4px;"><line x1="0" y1="6" x2="20" y2="6" stroke="{color_smooth}" stroke-width="2.5"/></svg>'
        _line_trailing_svg = f'<svg width="20" height="12" style="vertical-align: middle; display: inline-block; margin-right: 4px;"><line x1="0" y1="6" x2="20" y2="6" stroke="{color_trailing}" stroke-width="2.5"/></svg>'

        _curr_dash = 'stroke-dasharray="4,3"' if not _has_c_rate else ""
        _curr_c = color_rate if _has_c_rate else color_edge
        _line_sg_rate_svg = f'<svg width="20" height="12" style="vertical-align: middle; display: inline-block; margin-right: 4px;"><line x1="0" y1="6" x2="20" y2="6" stroke="{_curr_c}" stroke-width="2.5" {_curr_dash}/></svg>'

        _readout = mo.md(f"""
        <div style="background: #f8fafc; padding: 10px 14px; border-radius: 8px; border: 1px solid #cbd5e1; font-family: system-ui, sans-serif; font-size: 13px; color: #0f172a; margin-top: 4px;">
          <div style="display: flex; flex-wrap: wrap; gap: 16px; justify-content: space-between; font-weight: 600; margin-bottom: 6px;">
            <div>{_line_date}Date: {_sel_date.strftime("%b %d, %Y")}</div>
            <div>{_line_raw_svg}Raw {title_metric}: <span style="color:{color_raw}; font-weight:bold;">{_sel_raw_val:.1f} {unit}</span></div>
            <div>{_line_smooth_svg}SG Smoothed {title_metric}: <span style="color:{color_smooth}; font-weight:bold;">{_sel_smooth_val:.2f} {unit}</span></div>
          </div>
          <div style="display: flex; flex-wrap: wrap; gap: 16px; justify-content: space-between; border-top: 1px solid #e2e8f0; padding-top: 6px; margin-bottom: 6px;">
            <div>{_line_trailing_svg}<strong>Trailing WLS Causal Nowcast:</strong> <span style="color:{color_trailing}; font-weight:bold;">{_sel_trailing_rate:+.2f} {rate_unit}</span> (95% CI: [{_sel_trailing_l:+.2f}, {_sel_trailing_u:+.2f}])</div>
            <div>{_line_sg_rate_svg}<strong>SG Retrospective Rate:</strong> {_sg_status}</div>
          </div>
          <div style="display: flex; flex-wrap: wrap; gap: 16px; justify-content: space-between; border-top: 1px dashed #cbd5e1; padding-top: 6px; font-size: 12px; color: #334155; background: #ffffff; margin: 0 -6px -2px -6px; padding: 6px 8px; border-radius: 4px;">
            <div><strong>Overall ({_start_date.strftime("%b %d")} → {_sel_date.strftime("%b %d")}):</strong> {_start_val:.2f} → {_end_val:.2f} {unit}</div>
            <div><strong>Total Change:</strong> <span style="color:{color_smooth}; font-weight:bold;">{_diff_val:+.2f} {unit} ({_pct_val:+.2f}%)</span></div>
            <div><strong>Avg Rate / Wk:</strong> <span style="font-weight:bold;">{_rate_wk:+.2f} {rate_unit}</span> ({_days_elapsed} days)</div>
          </div>
        </div>
        """)

        return _fig, _readout

    # Time span from first entry to currently selected date
    _start_date = results_df["date"].iloc[0]
    _days_elapsed = max(0, (_sel_date - _start_date).days)
    _weeks_elapsed = _days_elapsed / 7.0

    # (tab label, section heading, title, unit, rate unit, results_df columns, colors)
    # columns: raw, centered level, full level, centered rate, full rate, trailing rate, CI lower, CI upper
    _metric_specs = [
        (
            "🏋️ Weight",
            "Weight (lbs)",
            "Weight",
            "lbs",
            "lbs/wk",
            [
                "weight",
                "sg_weight_centered",
                "sg_weight_full",
                "sg_weekly_rate_centered",
                "sg_weekly_rate_full",
                "trailing_weekly_rate",
                "trailing_rate_lower_95",
                "trailing_rate_upper_95",
            ],
            ("#4682b4", "crimson", "#1d4ed8", "#059669", "#ea580c"),
        ),
        (
            "📊 Body Fat",
            "Body Fat (%)",
            "Body Fat",
            "%",
            "%/wk",
            [
                "body_fat",
                "sg_body_fat_centered",
                "sg_body_fat_full",
                "sg_body_fat_rate_centered",
                "sg_body_fat_rate_full",
                "trailing_body_fat_rate",
                "trailing_body_fat_lower_95",
                "trailing_body_fat_upper_95",
            ],
            ("#d97706", "#7c3aed", "#4338ca", "#0d9488", "#e11d48"),
        ),
        (
            "💪 Skeletal Muscle Mass",
            "Skeletal Muscle Mass (lbs)",
            "Skeletal Muscle Mass",
            "lbs",
            "lbs/wk",
            [
                "muscle_mass",
                "sg_muscle_centered",
                "sg_muscle_full",
                "sg_muscle_rate_centered",
                "sg_muscle_rate_full",
                "trailing_muscle_rate",
                "trailing_muscle_lower_95",
                "trailing_muscle_upper_95",
            ],
            ("#0284c7", "#d97706", "#2563eb", "#16a34a", "#dc2626"),
        ),
    ]

    # Each figure is built once and shown in exactly one place (never both in tabs and stacked)
    _views = {}
    _summary_metrics = []
    for (
        _tab,
        _heading,
        _title,
        _unit,
        _rate_unit,
        _cols,
        _colors,
    ) in _metric_specs:
        if not all(_c in results_df for _c in _cols):
            continue
        _smooth_arr = results_df[_cols[2]].to_numpy()
        _s_val = float(_smooth_arr[0])
        _e_val = float(_smooth_arr[_idx])
        _d_val = _e_val - _s_val
        _p_val = (_d_val / _s_val * 100.0) if _s_val != 0 else 0.0
        _r_wk = (_d_val / _weeks_elapsed) if _weeks_elapsed > 0 else 0.0

        _summary_metrics.append(
            {
                "tab": _tab,
                "title": _title,
                "unit": _unit,
                "rate_unit": _rate_unit,
                "color": _colors[1],
                "start_val": _s_val,
                "end_val": _e_val,
                "diff": _d_val,
                "pct": _p_val,
                "rate": _r_wk,
            }
        )

        _fig, _readout = _build_metric_chart(
            _title,
            _unit,
            _rate_unit,
            *[results_df[_c].to_numpy() for _c in _cols],
            *_colors,
        )
        _views[_tab] = (_heading, mo.vstack([_fig, _readout], gap=0.5))

    if "muscle_share_of_loss_pct" in results_df:
        _share = results_df["muscle_share_of_loss_pct"]
        _share_fig = go.Figure()
        _share_fig.add_trace(
            go.Scatter(
                x=results_df["date"],
                y=_share,
                mode="lines+markers",
                name="Muscle share of weight loss",
                line=dict(color="#7c3aed", width=2.5),
                marker=dict(size=4),
                connectgaps=False,
                hovertemplate="Date: %{x|%Y-%m-%d}<br>Muscle share of loss: %{y:.0f}%<extra></extra>",
            )
        )
        _share_fig.add_hline(
            y=0, line_dash="dash", line_color="gray", line_width=1.0
        )
        _share_fig.add_vline(
            x=_sel_date, line_dash="dot", line_color="#64748b", line_width=1.5
        )
        _share_fig.update_layout(
            template="plotly_white",
            width=800,
            height=320,
            margin=dict(t=40, b=25, l=55, r=25),
            title=f"Percent of weight loss that is muscle (trailing {int(rate_window_days.value)} days)",
        )
        _share_fig.update_yaxes(title_text="% of weight lost")
        _share_fig.update_xaxes(title_text="Date")
        _sel_share = _share.iloc[_idx]
        _share_text = (
            f"**{_sel_date.strftime('%b %d, %Y')}:** {_sel_share:.0f}% of the weight lost over the preceding "
            f"{int(rate_window_days.value)} days was muscle."
            if not np.isnan(_sel_share)
            else f"**{_sel_date.strftime('%b %d, %Y')}:** undefined (smoothed weight did not drop by at least 2 lb "
            f"over the preceding {int(rate_window_days.value)} days)."
        )
        _views["🧬 Muscle % of Loss"] = (
            "Muscle Share of Weight Loss (%)",
            mo.vstack([_share_fig, mo.md(_share_text)], gap=0.5),
        )

    _stacked_elements = []
    for _i, (_heading, _view) in enumerate(_views.values(), start=1):
        if _i > 1:
            _stacked_elements.append(mo.md("---"))
        _stacked_elements.extend([mo.md(f"### {_i}. {_heading}"), _view])

    _active_content = (
        mo.ui.tabs({_tab: _v for _tab, (_h, _v) in _views.items()})
        if plot_layout_mode.value == "Tabs"
        else mo.vstack(_stacked_elements, gap=0.5)
    )

    # --- Summary Scorecard Cards & Compact Table ---
    _cards_html_parts = []
    _table_rows_html = []
    for _m in _summary_metrics:
        _card = f"""
        <div style="flex: 1 1 230px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
            <div style="font-weight: 700; font-size: 14px; color: #1e293b;">{_m["tab"]}</div>
            <span style="font-size: 11px; font-weight: 600; padding: 2px 7px; border-radius: 9999px; background: #f1f5f9; color: {_m["color"]};">Smoothed</span>
          </div>
          <div style="display: flex; align-items: center; justify-content: space-between; background: #f8fafc; border-radius: 6px; padding: 6px 10px; margin-bottom: 10px; font-size: 12px;">
            <div>
              <div style="color: #64748b; font-size: 10px;">Start ({_start_date.strftime("%b %d")})</div>
              <div style="font-weight: 700; color: #0f172a;">{_m["start_val"]:.2f} <span style="font-size: 10px; font-weight: normal; color: #64748b;">{_m["unit"]}</span></div>
            </div>
            <div style="color: #94a3b8; font-size: 14px; padding: 0 4px;">→</div>
            <div style="text-align: right;">
              <div style="color: #64748b; font-size: 10px;">End ({_sel_date.strftime("%b %d")})</div>
              <div style="font-weight: 700; color: #0f172a;">{_m["end_val"]:.2f} <span style="font-size: 10px; font-weight: normal; color: #64748b;">{_m["unit"]}</span></div>
            </div>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr 1.1fr; gap: 6px; text-align: center; border-top: 1px solid #f1f5f9; padding-top: 8px;">
            <div>
              <div style="font-size: 10px; color: #64748b;">Total Change</div>
              <div style="font-size: 13px; font-weight: 700; color: {_m["color"]};">{_m["diff"]:+.2f} {_m["unit"]}</div>
            </div>
            <div>
              <div style="font-size: 10px; color: #64748b;">% Change</div>
              <div style="font-size: 13px; font-weight: 700; color: {_m["color"]};">{_m["pct"]:+.2f}%</div>
            </div>
            <div>
              <div style="font-size: 10px; color: #64748b;">Avg / Wk</div>
              <div style="font-size: 13px; font-weight: 700; color: #334155;">{_m["rate"]:+.2f} <span style="font-size: 9px; font-weight: normal; color: #64748b;">{_m["rate_unit"]}</span></div>
            </div>
          </div>
        </div>
        """
        _cards_html_parts.append(_card)

        _row = f"""
        <tr style="border-bottom: 1px solid #f1f5f9;">
          <td style="padding: 7px 10px; font-weight: 600; color: #1e293b;">{_m["tab"]}</td>
          <td style="padding: 7px 10px; color: #475569;">{_m["start_val"]:.2f} {_m["unit"]} <span style="color:#94a3b8; font-size: 11px;">({_start_date.strftime("%b %d, %Y")})</span></td>
          <td style="padding: 7px 10px; color: #475569;">{_m["end_val"]:.2f} {_m["unit"]} <span style="color:#94a3b8; font-size: 11px;">({_sel_date.strftime("%b %d, %Y")})</span></td>
          <td style="padding: 7px 10px; text-align: right; font-weight: 700; color: {_m["color"]};">{_m["diff"]:+.2f} {_m["unit"]}</td>
          <td style="padding: 7px 10px; text-align: right; font-weight: 700; color: {_m["color"]};">{_m["pct"]:+.2f}%</td>
          <td style="padding: 7px 10px; text-align: right; font-weight: 600; color: #334155;">{_m["rate"]:+.2f} {_m["rate_unit"]}</td>
        </tr>
        """
        _table_rows_html.append(_row)

    _summary_html = f"""
    <div style="margin-top: 14px; font-family: system-ui, sans-serif;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <span style="font-weight: 700; font-size: 14px; color: #0f172a;">📊 Trajectory Summary ({_start_date.strftime("%b %d, %Y")} → {_sel_date.strftime("%b %d, %Y")} · {_days_elapsed} days / {_weeks_elapsed:.1f} wks)</span>
        <span style="font-size: 11px; color: #64748b; font-style: italic;">Smoothed (ŵ) start/end values</span>
      </div>
      <div style="display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 10px;">
        {"".join(_cards_html_parts)}
      </div>
      <table style="width: 100%; border-collapse: collapse; font-size: 12px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 2px rgba(0,0,0,0.03);">
        <thead>
          <tr style="background: #f8fafc; border-bottom: 1px solid #e2e8f0; text-align: left; color: #475569; font-weight: 600;">
            <th style="padding: 8px 10px;">Metric</th>
            <th style="padding: 8px 10px;">Start Value</th>
            <th style="padding: 8px 10px;">Selected Value</th>
            <th style="padding: 8px 10px; text-align: right;">Total Change</th>
            <th style="padding: 8px 10px; text-align: right;">% Change</th>
            <th style="padding: 8px 10px; text-align: right;">Avg Rate / Wk</th>
          </tr>
        </thead>
        <tbody>
          {"".join(_table_rows_html)}
        </tbody>
      </table>
    </div>
    """

    charts_display = mo.vstack(
        [
            mo.hstack(
                [
                    plot_layout_mode,
                    mo.md(
                        "*Tip: Choose **Tabs** to focus on one metric at a time, or **Stacked** to view all three.*"
                    ).style(
                        {
                            "font-size": "12px",
                            "color": "#64748b",
                            "margin-top": "6px",
                        }
                    ),
                ],
                justify="space-between",
            ),
            _active_content,
            time_slider,
            mo.md(_summary_html),
        ],
        gap=0.5,
    ).style({"max-height": "none", "overflow": "visible"})

    charts_display
    return


@app.cell(hide_code=True)
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

    # Full SG estimates (mode="interp") for weight
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

    # Compute trailing causal WLS nowcast for weight
    _wls_df = compute_trailing_wls(
        df_raw,
        weight_col="weight",
        window_days=int(rate_window_days.value),
        half_life_days=float(rate_half_life_days.value),
    )

    for _col in _wls_df.columns:
        results_df[_col] = _wls_df[_col]

    # Body Fat and Skeletal Muscle Mass: same SG + trailing WLS as weight
    for _src_col, _prefix in (("body_fat", "body_fat"), ("muscle_mass", "muscle")):
        if _src_col not in df_raw or not df_raw[_src_col].notna().any():
            continue
        _arr = df_raw[_src_col].to_numpy()
        _sg_full = savgol_filter(_arr, window_length=_w, polyorder=_polyorder, deriv=0, mode="interp")
        _sg_rate_full = savgol_filter(_arr, window_length=_w, polyorder=_polyorder, deriv=1, mode="interp") * 7.0

        results_df[f"sg_{_prefix}_full"] = _sg_full
        results_df[f"sg_{_prefix}_rate_full"] = _sg_rate_full
        results_df[f"sg_{_prefix}_centered"] = np.where(is_centered_sg, _sg_full, np.nan)
        results_df[f"sg_{_prefix}_rate_centered"] = np.where(is_centered_sg, _sg_rate_full, np.nan)

        _wls = compute_trailing_wls(
            df_raw,
            weight_col=_src_col,
            window_days=int(rate_window_days.value),
            half_life_days=float(rate_half_life_days.value),
        )
        results_df[f"trailing_{_prefix}_rate"] = _wls["trailing_weekly_rate"]
        results_df[f"trailing_{_prefix}_lower_95"] = _wls["trailing_rate_lower_95"]
        results_df[f"trailing_{_prefix}_upper_95"] = _wls["trailing_rate_upper_95"]

    # Share of weight loss that is skeletal muscle over the trailing rate window: the least-squares
    # slope of smoothed muscle vs. smoothed weight (muscle lbs lost per lb of weight lost) x 100.
    # Uses every point in the window rather than two endpoints; only shown when smoothed weight
    # fell by >= 2 lb across the window.
    if "sg_muscle_full" in results_df:
        _lag = int(rate_window_days.value)
        _d_weight = results_df["sg_weight_full"].diff(_lag)
        _slope = (
            results_df["sg_weight_full"].rolling(_lag + 1).cov(results_df["sg_muscle_full"])
            / results_df["sg_weight_full"].rolling(_lag + 1).var()
        )
        results_df["muscle_share_of_loss_pct"] = (_slope * 100.0).where(_d_weight <= -2.0)
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

        # Synthetic body fat: baseline ~22%, trending downward with body mass
        bf_trend = 22.0 + (trend_vals - 182.0) * 0.15 + rng.normal(0, 0.3, n_days)
        # Synthetic skeletal muscle mass: baseline ~72 lbs
        muscle_trend = 72.0 + (trend_vals - 182.0) * 0.25 + rng.normal(0, 0.4, n_days)

        return (
            pd.DataFrame({
                "date": dates,
                "weight": trend_vals + iid_noise + weekly_cycle,
                "body_fat": bf_trend,
                "muscle_mass": muscle_trend,
            }),
            trend_vals,
            true_slope,
        )

    _using_synthetic = len(df_raw_file) == 0

    if _using_synthetic:
        df_raw, synthetic_trend, synthetic_slope = _make_synthetic()
        data_source_note = (
            "No CSV found in `dat` — using a **synthetic 90-day example** "
            "(true slope of -0.20 lb/day for the first 45 days, then -0.05 lb/day, "
            "plus daily noise and a weekly cycle) so the notebook runs end to end. "
            "Start the Garmin export above and upload a CSV to replace this."
        )
    else:
        df_raw = df_raw_file.copy()
        synthetic_trend, synthetic_slope = None, None
        data_source_note = f"Loaded **{len(df_raw)}** rows from `{inFNm}`."

    # Convert date/weight/composition types and sort strictly ASCENDING by date (chronological order)
    df_raw["date"] = pd.to_datetime(df_raw["date"])
    df_raw["weight"] = pd.to_numeric(df_raw["weight"], errors="coerce")
    if "body_fat" in df_raw:
        df_raw["body_fat"] = pd.to_numeric(df_raw["body_fat"], errors="coerce")
    if "muscle_mass" in df_raw:
        df_raw["muscle_mass"] = pd.to_numeric(df_raw["muscle_mass"], errors="coerce")
    df_raw = df_raw.dropna(subset=["date", "weight"]).sort_values("date", ascending=True).reset_index(drop=True)

    mo.md(data_source_note)
    return (df_raw,)


if __name__ == "__main__":
    app.run()
