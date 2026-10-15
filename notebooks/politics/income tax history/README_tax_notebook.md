# US top-income-tax history: marimo notebook

Run with an existing environment:

    python -m pip install "marimo>=0.14,<1" "pandas>=2.2,<3" "matplotlib>=3.8,<4" "requests>=2.32,<3"
    marimo edit top_income_tax_history.py

Alternatively, marimo's sandbox mode reads the inline dependency metadata:

    uvx marimo edit --sandbox top_income_tax_history.py

The notebook embeds the CSV, so initial graphs require no source-file downloads.
Click the source-download button to fetch PDF/HTML documents to sources/ beside
the notebook. A manifest records hashes, byte sizes, timestamps and failures.
Existing files are cached; remove one to refresh it. Linked spreadsheets are not
crawled. HTML blocking/challenge pages may need manual inspection.

This is a PARTIAL, manually transcribed starting dataset, not a validated extraction
pipeline. The earlier Civil War income tax is excluded. Population and group-tax /
federal-outlay shares are unknown, not zero. The one 1963 return-share estimate
is not a population share. See notebook notes before interpretation.

Validation performed during generation: Python syntax parsing and embedded-data
shape checks. The marimo runtime and live downloads were not executed in the
file-generation environment (network access is unavailable there).

Dependencies are range-constrained, not fully locked. For publication-grade
reproduction, record the resolved environment/lockfile and downloaded hashes.
