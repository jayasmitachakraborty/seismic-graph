"""Run Great Expectations suites; write HTML reports to quality/reports/.

Usage: ``python -m quality.run_checks``
"""

import logging
import sys
from collections.abc import Callable

import great_expectations as gx
import pandas as pd

from ingestion import usgs_events
from quality._html_report import write_html_report
from quality.expectations import aftershock_edges_suite, events_suite, faults_suite
from transform import build_aftershock_edges
from utils import dtypes

log = logging.getLogger(__name__)


def _ephemeral_batch(df: pd.DataFrame, *, asset: str):
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name=f"{asset}_source")
    data_asset = data_source.add_dataframe_asset(name=asset)
    batch_def = data_asset.add_batch_definition_whole_dataframe(name=f"{asset}_whole")
    return batch_def.get_batch(batch_parameters={"dataframe": df})


def _validate(df: pd.DataFrame, *, asset: str, suite: gx.ExpectationSuite) -> bool:
    result = _ephemeral_batch(df, asset=asset).validate(suite)
    s = result.statistics
    log.info(
        "%s: %s/%s passed (%s rows)",
        suite.name,
        s["successful_expectations"],
        s["evaluated_expectations"],
        f"{len(df):,}",
    )
    for r in result.results:
        if not r.success:
            log.error("FAIL %s %s %s", r.expectation_config.type, r.expectation_config.kwargs, r.result)

    path = write_html_report(result, suite_name=suite.name, asset=asset, row_count=len(df))
    log.info("%s: report -> %s", suite.name, path)
    return result.success


def check_events() -> bool:
    df = usgs_events.read_combined()
    return _validate(df, asset="events", suite=events_suite.build())


def check_faults() -> bool:
    df = dtypes.read_faults()
    return _validate(df, asset="faults", suite=faults_suite.build())


def check_aftershock_edges() -> bool:
    df = build_aftershock_edges.read()
    return _validate(df, asset="aftershock_edges", suite=aftershock_edges_suite.build())


CHECKS: tuple[Callable[[], bool], ...] = (
    check_events,
    check_faults,
    check_aftershock_edges,
)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # Run all checks even if one fails so the operator sees every problem at once.
    return 0 if all([check() for check in CHECKS]) else 1


if __name__ == "__main__":
    sys.exit(main())
