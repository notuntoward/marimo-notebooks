import marimo

__generated_with = "0.17.7"
app = marimo.App()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Compute total US Mileage driven vs. Trip Len
    Data for May 2023 from [US Bureau of Transportation Studies](https://www.bts.gov/browse-statistical-products-and-data/covid-related/distribution-trips-distance-national-state-and)

    **Conclusion**
    * About 70% ot total miles driven are on trips under 50 miles long
    * So a 50 mile battery would improve a car's average gas mileage by about 70%
    * Approximately...
      * missing bin in data between 100-25 miles and 500+ miles
      * Long trips are probably highway speeds, so worse MPG
      * But short trips are probably city driving, where hybrids are most efficient
    """)
    return


@app.cell
def _():
    import numpy as np
    import pandas as pd
    return (pd,)


@app.cell
def _(pd):
    df = pd.DataFrame(dict(milesMin=[0, 1, 3, 5, 10, 25, 50, 100, 500],
                           milesMax=[1, 3, 5, 10, 25, 50, 100, 250, 1000],
                           num = [420.7, 350.3, 178.7, 229.0, 217.9, 68.1, 
                                  21.7, 9.3, 1.3]))


    df['milesMn'] = df.milesMin + (df.milesMax-df.milesMin)/2
    df['milesMnTot'] = df.milesMn * df.num
    df['milesMnTotCum'] = df.milesMnTot.cumsum()
    df['milesMnTotCumPct'] = 100* (df.milesMnTotCum / df.milesMnTotCum.iloc[-1])
    df
    return


@app.cell
def _():
    import marimo as mo
    return (mo,)


if __name__ == "__main__":
    app.run()

