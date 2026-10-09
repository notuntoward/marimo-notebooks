# WalletHub state tax burden replication

This note accompanies the [marimo notebook](wallethub_tax_burden_replication.py). It
explains the article-year notation, source choices, and how to run the Census API years.

## WalletHub edition and Census fiscal year

These are two different years. The WalletHub edition is the year named in its article;
the Census fiscal year identifies the source observations used in that calculation.

| WalletHub article edition | Census fiscal year used |
| --- | --- |
| 2024 | FY2021 |
| 2025 | FY2022 |
| 2026 | FY2023 |
| Latest available Census data | FY2024 |

The historical article years are informed mappings, not confirmed WalletHub input
vintages. WalletHub does not name the source fiscal year or publish an edition-frozen
calculation file. The assignments are supported by source-release timing and by
comparing the notebook's downloaded-data results with five published WalletHub state
examples per edition.

## Requested Census FY2025 analysis

The WalletHub **2025 article edition** maps to Census FY2022; that article year is not
the same thing as **Census fiscal year 2025**. Census's [current State and Local
Government Finances data/API page](https://www.census.gov/data/developers/data-sets/govslocalfin.html)
documents coverage through FY2024, and the [FY2024 data release](https://www.census.gov/data/datasets/2024/econ/local/public-use-datasets.html)
was published in July 2026. Census has not published FY2025 government-finance
observations yet.

Because the Census tax-revenue numerator for FY2025 is not available, the notebook
cannot honestly compute 2025 tax-to-income percentages or rankings. It includes FY2025
in the requested-year output and explicitly reports it as unavailable; it does not
substitute a BEA-only denominator or relabel another Census year as 2025. FY2024 remains
the latest calculation until Census releases FY2025 data.

The release dates make FY2022 a reasonable match for the 2025 article: Census released
the 2022 finance data on [October 31, 2024](https://www.census.gov/newsroom/press-releases/2024/census-of-governments.html),
before WalletHub's April 1, 2025 report. Census published its FY2023 data in
[July 2025](https://www.census.gov/data/datasets/2023/econ/local/public-use-datasets.html),
after that article. The 2024 article predates the FY2022 release, and the 2026 article
predates FY2024 data, released in July 2026.

## Sources and calculation

- **Tax receipts:** U.S. Census Bureau state-and-local government finance data. The
  notebook downloads the official summary workbooks for FY2021 and FY2022 and uses
  the Census API for FY2023 and FY2024.
- **Personal income:** U.S. Bureau of Economic Analysis (BEA), Regional table SAINC1,
  LineCode 1 (“Personal income”), in current dollars.
- **Categories:** Census property tax; individual income tax (excluding corporate
  income tax); and general sales plus selective sales taxes. This follows the
  [Tax Policy Center's series definitions](https://state-local-finance-data.taxpolicycenter.org/help/revenue.html),
  which correspond to WalletHub's described components.

For each state, the calculation divides each combined state-and-local tax-revenue
category by state personal income, then sums the three shares for the overall burden.
The raw Census and BEA values are downloaded and used in the calculations. WalletHub
figures appear only as validation examples in the notebook; they do not determine any
burden percentage or rank. The 2025 validation examples are transcribed from the
[published 2025 table](https://www.cpapracticeadvisor.com/2025/04/01/how-the-50-states-rank-by-tax-burden-updated-for-2025/158094/).

This is a replication of a tax-revenue-to-personal-income ratio, not a household tax
incidence estimate. Census records revenue by the location of state and local
governments; it does not allocate business-paid taxes to households. Census data use
government fiscal years while BEA personal income is annual calendar-year data, so
the numerator and denominator periods are close but not perfectly aligned. Revisions,
aggregation choices, and the unavailable frozen WalletHub extract can also produce
small differences from published values.

## Running the notebook

FY2021 and FY2022 use downloadable Census workbooks and BEA data; they do not require
an API key. FY2023 and FY2024 use the Census API and require a free
[Census API key](https://api.census.gov/data/key_signup.html). Set the key in the same
shell that launches marimo:

```powershell
$env:CENSUS_API_KEY = "paste-your-key"
uvx marimo edit "notebooks/politics/state tax comparison/wallethub_tax_burden_replication.py"
```

```bash
export CENSUS_API_KEY="paste-your-key"
uvx marimo edit "notebooks/politics/state tax comparison/wallethub_tax_burden_replication.py"
```

If marimo is already running, restart it after setting the variable. The notebook
reads the key from the environment and does not save it; raw downloads are cached
locally in `data_cache/`.

The notebook currently uses the Census API for FY2023 and FY2024. FY2025 is shown as
unavailable until the Census source above publishes that year; adding an API key cannot
provide unpublished data.

## Readable report

The [HTML export](exports/wallethub_tax_burden_replication.html) is a browser-readable
snapshot of the notebook with its code and rendered outputs. This snapshot was
generated without `CENSUS_API_KEY`: it shows the FY2021/FY2022 rankings, API-key
messages for FY2023/FY2024, and an explicit FY2025-not-yet-published status. With an
API key, rerun the export to include FY2023/FY2024 results; FY2025 cannot be computed
until Census publishes its data.

After setting the key, regenerate the report with:

```bash
uvx marimo export html --sandbox --force \
  "notebooks/politics/state tax comparison/wallethub_tax_burden_replication.py" \
  -o "notebooks/politics/state tax comparison/exports/wallethub_tax_burden_replication.html"
```
