import marimo
from wigglystuff import ColorPicker

app = marimo.App()

@app.cell
def _():
    import marimo as mo
    from wigglystuff import ColorPicker
    return ColorPicker, mo

@app.cell
def _(ColorPicker, mo):
    cp = mo.ui.anywidget(ColorPicker(color="#5e81ac"))
    return (cp,)

@app.cell
def _(cp, mo):
    color_val = cp.value.get("color", "#5e81ac") if isinstance(cp.value, dict) else cp.value
    mo.md(f"Selected: {color_val}")
    return (color_val,)

if __name__ == "__main__":
    app.run()