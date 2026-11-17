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

## Running on Windows without a console window

Launching a notebook from a GUI application (an agent host, a file manager, a
desktop shortcut) makes a large black console window appear over the screen
and stay there for the life of the server. `uvx` and `uv` are console
subsystem programs, and on Windows a console program started from a process
with no console of its own is handed a brand-new console. When Windows
Terminal is the registered default terminal, the OS hosts that console in a
visible `WindowsTerminal.exe` window.

Two ways to avoid it:

**Run it from a terminal.** A terminal already owns a console, so the whole
`uvx -> marimo -> python` tree inherits it and nothing new appears.

**Use the launcher.** It runs as a `.pyw` file, so Windows starts it with
`pythonw.exe` (GUI subsystem, never claims a console), and every child is
started with `CREATE_NO_WINDOW`, so the tree inherits a hidden console:

```bash
pythonw scripts/launch_notebook.pyw notebooks/health/weight.py --port 27180 --watch
pythonw scripts/launch_notebook.pyw notebooks/health/weight.py --port 27180 -- --update-latest true
```

The server log goes to `data/logs/<notebook>.log` and the URL to
`data/logs/<notebook>.url`. Pass `--token-file <path>` to have the launcher
generate a token, write it to that path, and hand it to marimo. Use
`--detach` to return immediately instead of waiting for the server.

If a stray window is already open from an earlier launch, hide it without
stopping the server:

```powershell
Get-Process WindowsTerminal | ForEach-Object { $_.MainWindowHandle } |
  Where-Object { $_ -ne 0 } | ForEach-Object {
    Add-Type -Name W -Namespace N -MemberDefinition '[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);'
    [N.W]::ShowWindow($_, 0)
  }
```

## Layout

```text
notebooks/
  plugin_lab.py              # Portable fixture/inspection workspace
  traffic/
    seattle_traffic.py        # Seed notebook for public traffic analysis
data/
  raw/                       # Ignored downloaded/source data
  derived/                   # Ignored generated analysis artifacts
  logs/                      # Ignored notebook server logs (Windows launcher)
  fixtures/                  # Small, committed synthetic data only
scripts/
  launch_notebook.pyw        # Starts a notebook with no console window (Windows)
src/                         # Shared pure-Python utilities when needed
.agents/skills/              # Repository-level agent skills or symlinks
.github/workflows/           # Notebook validation, intentionally no Dependabot
```

## Line endings

Text files in this repository use LF line endings on Windows, macOS, and Linux. Git enforces this in `.gitattributes`, and `.editorconfig` asks supported editors to write LF as well. This avoids platform-dependent file changes when contributors exchange commits.

Set Git's conversion behavior locally in each clone:

```bash
git config --local core.autocrlf input
```

This repository-level setting does not change your global Git configuration. If your global `core.autocrlf` is `true`, the explicit LF policy in `.gitattributes` still controls this repository's text files.

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
