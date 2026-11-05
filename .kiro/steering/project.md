# AWS End-of-Support Tool

CLI and tkinter GUI that reads an AWS resource inventory CSV and reports
support status (Supported, Approaching EOS, Extended Support Y1/Y2/Y3, Out of
Support) as text, CSV, JSON, Excel (with real PivotTables), or HTML. Optional
AI recommendations via Amazon Bedrock.

## Layout

- `src/` – application package (`main.py` CLI, `gui.py` GUI, `classifier.py`,
  `parser.py`, `formatters.py`, `html_formatter.py`, `generator.py`,
  `models.py`, `ai_summary.py`, `eks_insights.py`, `extended_support_lookup.py`)
- `src/templates/pivot_template.xlsx` – the only tracked binary; keep it
- `tests/` – pytest + hypothesis property tests
- `scripts/` – data-refresh helpers (extended support lookup, AWS fetch)
- `docs/` – design notes and HTML user guide
- `EndOfSupportTool.spec`, `EndOfSupportTool_mac.spec` – PyInstaller specs used
  by `.github/workflows/build.yml` on `v*` tags

## Environment

- Python >= 3.9 (CI uses 3.11). Create a venv and `pip install -e ".[dev]"`
  (or `uv venv; uv pip install -e ".[dev]"`).
- Run: `python -m src.main inventory.csv [--output-format excel|html|json|csv]`
  or `python -m src.gui`.
- Test: `pytest` (config in `pyproject.toml`, `testpaths = ["tests"]`).
- AI features need AWS credentials with Bedrock access; the tool reads the
  default boto3 credential chain. On Amazon machines use `mwinit` + `ada` with
  a `credential_process` entry in `~/.aws/config`.

## Rules

- Never commit CSV/XLSX inputs or generated reports: they may contain customer
  data. `.gitignore` already excludes `*.csv`, `*.xlsx`, `*_report.html`,
  `aws_inventory.*`, `test_output.*`; keep those patterns intact.
- `ai_summary.py` sends only aggregated statistics to Bedrock, never account
  IDs, ARNs, or resource names. Preserve that boundary when changing it.
- Bump `version` in `pyproject.toml` and add a `RELEASE_NOTES.md` entry for
  user-visible changes; releases are cut by pushing a `v*` tag.
- The public GitHub remote is `savelyvas/EndOfSupport`. Treat the repo as
  public: no internal URLs, account IDs, or credentials in code or docs.
