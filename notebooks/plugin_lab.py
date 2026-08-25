# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "marimo>=0.14",
# ]
# ///

import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import os
    from pathlib import Path

    import marimo as mo

    return Path, mo, os


@app.cell
def _(Path, mo, os):
    vault_path = os.environ.get("OBSIDIAN_VAULT_PATH")
    vault = Path(vault_path).expanduser() if vault_path else None
    status = (
        mo.md(f"Local vault configured: `{vault}`")
        if vault and vault.exists()
        else mo.md(
            "No accessible vault configured. Set `OBSIDIAN_VAULT_PATH` to inspect a local test vault."
        )
    )
    status
    return


@app.cell
def _(mo):
    mo.md("""
    # Plugin lab

    Use this notebook for read-only inspection, fixture design, and analyses that span
    multiple Obsidian plugins. Keep vault writes behind an explicit UI action and default
    to synthetic fixtures committed under `data/fixtures/`.

    Suggested additions:

    - Parse saved Markdown output and validate turn/source-footnote invariants.
    - Generate edge-case link/property fixtures for a test vault.
    - Compare plugin outputs against expected JSON or Markdown snapshots.
    """)
    return


if __name__ == "__main__":
    app.run()
