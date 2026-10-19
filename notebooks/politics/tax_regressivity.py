# /// script
# dependencies = [
#     "basedpyright>=1.40.2",
#     "icecream==2.2.0",
#     "jinja2>=3.1.6",
#     "marimo[lsp]>=0.23.3",
#     "pandas==3.0.6",
#     "python-lsp-ruff==2.3.4",
#     "python-lsp-server==1.15.0",
#     "websockets==17.2",
# ]
# requires-python = ">=3.12"
# ///

import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import pandas as pd

    # Low income bin data
    df = pd.DataFrame({
        "person": list("ABCDE"),
        "income": [3000, 8000, 14000, 22000, 23000],
        #"income": [3000, 8000, 14000, 22000, 24000],    
        "tax":    [1500,2240,2520,3190,3010],    
    }).set_index('person')
    df["rate"] = df["tax"] / df["income"]

    mo.vstack([mo.md("### Low-income bin: income, tax, and effective rate"),
               mo.Html(df.to_html())])
    return df, mo, pd


@app.cell
def _(df):
    # True summary stats
    tax_sum_true  = df["tax"].sum()
    inc_sum_true  = df["income"].sum()
    inc_max_true  = df["income"].max()
    inc_mean_true = df["income"].mean()
    rate_mean_true   = df["rate"].mean() 

    # Correct method: burden rate is ratio of sums, applied to the bar mean
    rate_burden = tax_sum_true / inc_sum_true  # standard tax burden (on OP's graph)
    tax_mean_burden = rate_burden * inc_mean_true # mean tax per person
    num_people = len(df)
    tax_sum_burden = tax_mean_burden * num_people

    # Confused method: multiply tax burden bay max income in bar
    tax_mean_claim      = rate_burden * inc_max_true         # wrong: != true mean
    tax_sum_claim       = tax_mean_claim * num_people   # wrong: != true sum
    tax_sum_claim_error_pct = (tax_sum_claim / tax_sum_true - 1) * 100  # how wrong
    return (
        inc_sum_true,
        rate_burden,
        rate_mean_true,
        tax_mean_burden,
        tax_mean_claim,
        tax_sum_burden,
        tax_sum_claim,
        tax_sum_claim_error_pct,
        tax_sum_true,
    )


@app.cell
def _():
    return


@app.cell
def _(
    df,
    mo,
    pd,
    rate_burden,
    rate_mean_true,
    tax_mean_burden,
    tax_mean_claim,
    tax_sum_burden,
    tax_sum_claim,
    tax_sum_claim_error_pct,
    tax_sum_true,
):
    actual_tax_at_max = f"${df['tax'].iloc[-1]:,.0f}"
    matches_total     = abs(tax_sum_burden - tax_sum_true) < 1e-9

    # (Metric, Value, Note)
    rows = [
        ("Bar chart rate (ratio of sums)", f"{rate_burden:.1%}",                   "The correct answer"),
        ("Individual rate mean",    f"{rate_mean_true:.1%}",           ""),
        ("True total tax",                     f"${tax_sum_true:,.0f}",         "What the gov't collects"),
        ("R × max income, per unit",           f"${tax_mean_claim:,.0f}",    f"True tax at max inc: {actual_tax_at_max}"),
        ("Implied total (R × max × n)",        f"${tax_sum_claim:,.0f}",       f"{tax_sum_claim_error_pct:.0f}% too high"),
        ("R × mean income, per unit",          f"${tax_mean_burden:,.0f}", ""),
        ("Implied total (R × mean × n)",       f"${tax_sum_burden:,.0f}",       f"matches true total: {matches_total}"),
    ]

    summary = pd.DataFrame(rows, columns=["Metric", "Value", "Note"]).set_index("Metric")
    mo.Html(summary.to_html())
    return


@app.cell
def _(
    inc_sum_true,
    mo,
    pd,
    rate_burden,
    rate_mean_true,
    tax_sum_burden,
    tax_sum_claim,
    tax_sum_claim_error_pct,
    tax_sum_true,
):
    summary2 = pd.DataFrame(
        {
            "True":    [tax_sum_true,   rate_mean_true],
            "Burden":  [tax_sum_burden, rate_burden],
            "Claimed": [tax_sum_claim,  tax_sum_claim / inc_sum_true],
        },
        index=["Tax sum", "Rate"],
    )

    summary_fmt = summary2.astype(object)
    summary_fmt.loc["Tax sum"] = summary2.loc["Tax sum"].map("{:,.0f}".format)
    summary_fmt.loc["Rate"]    = summary2.loc["Rate"].map("{:.1%}".format)

    mo.vstack([
        mo.md(f"### True vs. burden vs. claimed tax  \n"
              f"Claimed sum overstates the true sum by **{tax_sum_claim_error_pct:.1f}%**"),
        mo.ui.table(summary_fmt, selection=None, pagination=False),
    ])
    return


if __name__ == "__main__":
    app.run()
