"""Render GX validation results to ``quality/reports/<suite_name>.html``."""

from __future__ import annotations

import datetime as dt
import html
import json
from pathlib import Path

import great_expectations as gx

REPORTS_DIR = Path(__file__).resolve().parent / "reports"

_CSS = """
body { font-family: sans-serif; max-width: 960px; margin: 2rem auto; padding: 0 1rem; }
.banner { padding: .75rem; border-radius: 4px; font-weight: bold; margin: 1rem 0; }
.pass { background: #dafbe1; color: #1a7f37; }
.fail { background: #ffebe9; color: #cf222e; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: .5rem; border-bottom: 1px solid #ddd; vertical-align: top; }
th { background: #f6f8fa; }
tr.fail td { background: #fff5f5; }
pre { background: #f6f8fa; padding: .5rem; overflow-x: auto; font-size: .85rem; margin: 0; }
"""


def _row(r) -> str:
    cfg = r.expectation_config
    cls = "pass" if r.success else "fail"
    column = cfg.kwargs.get("column", "")
    kwargs = {k: v for k, v in cfg.kwargs.items() if k != "column"}
    details = ""
    if not r.success and r.result:
        details = f"<pre>{html.escape(json.dumps(r.result, indent=2, default=str))}</pre>"
    return (
        f'<tr class="{cls}">'
        f"<td>{cls.upper()}</td>"
        f"<td>{html.escape(cfg.type)}</td>"
        f"<td>{html.escape(str(column))}</td>"
        f"<td>{html.escape(json.dumps(kwargs, default=str))}</td>"
        f"<td>{details}</td></tr>"
    )


def write_html_report(
    result: gx.ExpectationSuiteValidationResult,
    *,
    suite_name: str,
    asset: str,
    row_count: int,
) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"{suite_name}.html"

    s = result.statistics
    total = s["evaluated_expectations"]
    passed = s["successful_expectations"]
    cls = "pass" if result.success else "fail"
    msg = "All expectations passed" if result.success else f"{total - passed} failed"
    rows = "\n".join(_row(r) for r in result.results)
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    path.write_text(
        f"""<!doctype html>
<meta charset="utf-8">
<title>{html.escape(suite_name)}</title>
<style>{_CSS}</style>
<h1>{html.escape(suite_name)}</h1>
<p>asset: {html.escape(asset)} &middot; {row_count:,} rows &middot; {ts}</p>
<div class="banner {cls}">{msg} ({passed}/{total} passed)</div>
<table>
<tr><th>Status</th><th>Expectation</th><th>Column</th><th>Kwargs</th><th>Details</th></tr>
{rows}
</table>
""",
        encoding="utf-8",
    )
    return path
