# marimo-notebooks

Portable, Git-friendly [marimo](https://marimo.io) notebooks for two kinds of work:

- **Plugin lab** — local diagnostics, fixtures, and analyses for Obsidian plugin development.
- **Seattle traffic** — reproducible public-data analysis and shareable civic visualizations.

Each notebook is a Python file and should carry its own PEP 723 dependency metadata. The repository deliberately has no shared Python lockfile: unrelated notebooks remain independently runnable and avoid dependency coupling.

## Quick start

Install [uv](https://docs.astral.sh/uv/), then open a notebook locally:

```bash
uvx marimo edit --sandbox notebooks/plugin_lab.py
uvx marimo edit --sandbox notebooks/traffic/seattle_traffic.py
```

Or run a notebook as a script:

```bash
uv run notebooks/plugin_lab.py
```

`--sandbox` makes marimo use isolated environments based on each notebook's inline metadata. The only machine-level prerequisite is `uv`; marimo itself is obtained transiently by `uvx`.

## Layout

```text
notebooks/
  plugin_lab.py              # Portable fixture/inspection workspace
  traffic/
    seattle_traffic.py        # Seed notebook for public traffic analysis
data/
  raw/                       # Ignored downloaded/source data
  derived/                   # Ignored generated analysis artifacts
  fixtures/                  # Small, committed synthetic data only
src/                         # Shared pure-Python utilities when needed
.agents/skills/              # Repository-level agent skills or symlinks
.github/workflows/           # Notebook validation, intentionally no Dependabot
```

## Notebook conventions

- Keep inputs configurable through environment variables or marimo UI controls; do not commit personal vault paths or tokens.
- Put reusable, non-interactive logic in `src/`, with ordinary tests under `tests/`; notebooks should compose and visualize it.
- Cache downloaded public data outside Git or into ignored `data/raw/`; commit a source URL, retrieval date, schema assumptions, and a small fixture when useful.
- Use `marimo check` before committing notebook changes.
- Keep browser/WASM-compatible notebooks lightweight; guard native-only dependencies using PEP 508 platform markers when necessary.

## Obsidian-plugin work

Set `OBSIDIAN_VAULT_PATH` only on machines where a notebook needs a local test vault:

```bash
export OBSIDIAN_VAULT_PATH=/path/to/Test
uvx marimo edit --sandbox notebooks/plugin_lab.py
```

The starter notebook never writes to the vault. Make any fixture-generation or mutation step explicit and opt-in.

- [obsidian_color_optimizer.py](https://molab.marimo.io/github/notuntoward/marimo-notebooks/blob/main/notebooks/color-picking/obsidian_color_optimizer.py)


## Seattle traffic work

The traffic notebooks are designed to use public data, with raw inputs excluded from version control. Start by documenting dataset URLs and retrieval dates in the notebook and save small synthetic examples in `data/fixtures/` for tests.

## molab

Keep notebooks self-contained and push them to GitHub. You can then open a notebook in molab from GitHub for hosted, ephemeral execution. Do not expect a molab session to access local vault paths, local credentials, or ignored raw data.

- [obsidian_color_optimizer.py](https://molab.marimo.io/github/notuntoward/marimo-notebooks/blob/main/notebooks/color-picking/obsidian_color_optimizer.py)

## Agents

Install the `marimo pair` skill with your preferred agent tooling. Put repository-specific instructions or skill wrappers in `.agents/skills/`; keep personal, cross-project skills outside the repository. Agent configuration is development tooling, not a runtime dependency of a notebook.

## CI policy

CI runs on pushes and pull requests, and is deliberately narrow:

- syntax-compiles Python source and notebooks
- runs `marimo check` on notebook files
- runs tests only when `tests/` exists

This repository does **not** enable Dependabot. That is intentional: marimo and notebook dependencies are isolated per notebook, and automated dependency PRs are not useful until a shared, locked project dependency surface exists. If you later enable Dependabot, begin with a monthly schedule, one open PR maximum, and grouped updates.
