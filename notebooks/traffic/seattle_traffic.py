# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "marimo>=0.14",
#   "pandas>=2.2",
#   "altair>=5.0",
# ]
# ///

import marimo

__generated_with = "0.24.0"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import altair as alt

    return alt, mo, pd


@app.cell
def _(mo):
    mo.md("""
    # Seattle traffic analysis

    A reproducible workspace for examining public transportation data. Before analyzing
    a real source, record its URL, retrieval timestamp, relevant geography, time range,
    and known collection limitations. Keep downloaded records in `data/raw/` (ignored);
    commit only synthetic or safely redistributable fixtures.

    This starter visualization uses synthetic data and makes no claim about actual traffic
    conditions, crashes, safety, or policy effects.
    """)
    return


@app.cell
def _(pd):
    demo = pd.DataFrame(
        {
            "month": pd.to_datetime(["2025-01-01", "2025-02-01", "2025-03-01"]),
            "sample_count": [100, 118, 109],
        }
    )
    return (demo,)


@app.cell
def _(alt, demo):
    chart = (
        alt.Chart(demo)
        .mark_line(point=True)
        .encode(
            x=alt.X("month:T", title="Month"),
            y=alt.Y("sample_count:Q", title="Synthetic sample count"),
            tooltip=["month:T", "sample_count:Q"],
        )
        .properties(title="Starter chart — replace with documented public data")
    )
    chart
    return


if __name__ == "__main__":
    app.run()
