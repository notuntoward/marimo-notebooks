import marimo

__generated_with = "0.17.7"
app = marimo.App()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Calculate emissions of old ICE car vs. new EV

    Numbers from [perplexity](https://www.perplexity.ai/search/people-with-old-ice-cars-say-t-GqnUoRrPSLy4reVZdGefOQ#3), in tons of CO2
    """)
    return


@app.cell
def _():
    EVmanufac = 8.8 # EV manufacturing
    ICEmanufac = 5.6 # ICE car manufacturing
    EVdriv = 0.00025  # EV driving, per mile
    ICEdriv = 0.00040 #  ICE car driving, per mile
    return EVdriv, EVmanufac, ICEdriv, ICEmanufac


@app.cell
def _():
    import pandas as pd
    import numpy as np
    from icecream import ic
    import matplotlib.pyplot as plt
    return ic, np, pd, plt


@app.cell
def _(EVdriv, EVmanufac, ICEdriv, ICEmanufac, ic, np, pd, plt):
    milesDrivMax = 200000
    milesCum = np.array(range(0,milesDrivMax, 10000))

    tonsCO2 = pd.DataFrame({'EV': EVmanufac + milesCum * EVdriv,
                            'ICE': ICEmanufac + milesCum * ICEdriv}, index=milesCum)
    tonsCO2.index.rename('Miles_', inplace=True)
    tonsCO2.plot(xlabel='Distance Driven (miles)', ylabel='Total Emissions (CO2 tons)')
    plt.title('Total Emissions of EV and ICE Cars vs. Driving Distance')         

    # CO2 breakeven point
    breakeven_miles = (ICEmanufac - EVmanufac) / (EVdriv -  ICEdriv)
    ic(breakeven_miles)
    plt.axvline(x=breakeven_miles,c='r');
    plt.gca()
    return milesCum, tonsCO2


@app.cell
def _(EVdriv, EVmanufac, ICEdriv, ICEmanufac, milesCum):
    {'EV': EVmanufac + milesCum * EVdriv,
                            'ICE': ICEmanufac + milesCum * ICEdriv}
    return


@app.cell
def _(tonsCO2):
    tonsCO2
    return


@app.cell
def _():
    import marimo as mo
    return (mo,)


if __name__ == "__main__":
    app.run()
