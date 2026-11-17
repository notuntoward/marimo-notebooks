# Notebook guidance

- For marimo notebook work, load the relevant skill in `.agents/skills/`,
  especially `marimo-notebook` for writing notebooks and `marimo-pair` for
  working with a live session. Use the other task-specific skills when relevant.
- Follow the notebook conventions and sandbox workflow in `README.md`, including
  self-contained PEP 723 dependencies and `marimo check` for notebook changes.
- Preserve marimo's reactive dependency graph: define each shared variable in
  only one cell, avoid cycles, and use underscore-prefixed names for cell-local
  variables. Access UI element values in downstream cells.
- When editing notebook files directly, keep cell parameters and return values
  consistent with the variables shared between cells. Update notebook metadata,
  imports, or app configuration when the task requires it.
- Prefer polars for data manipulation when appropriate; validate inputs and
  handle missing values. Use interactive, clearly labeled visualizations when
  useful, and prefer marimo SQL cells for DuckDB queries.
