"""GX suite for the raw USGS events CSV (pre-clean schema).

Target: ``data/raw/usgs_events/usgs_events.csv`` — column names are
the raw USGS FDSN schema (``id``, ``time``, ``mag``, ``depth``).
"""

import great_expectations as gx
import great_expectations.expectations as gxe

SUITE_NAME = "events_suite"

# ``mag`` and ``time`` may be null on low-quality detections; the post-clean
# dropna in transform/clean_events.py handles those, so we don't gate them here.
REQUIRED_COLUMNS: tuple[str, ...] = ("id", "latitude", "longitude")


def build() -> gx.ExpectationSuite:
    suite = gx.ExpectationSuite(name=SUITE_NAME)

    for col in REQUIRED_COLUMNS:
        suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column=col))

    # Range guards mirror transform/clean_events.py.
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeBetween(column="mag", min_value=-2.0, max_value=10.0)
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeBetween(column="latitude", min_value=-90, max_value=90)
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeBetween(column="longitude", min_value=-180, max_value=180)
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeBetween(column="depth", min_value=-10, max_value=700)
    )

    suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column="id"))

    # Watermark sanity: USGS sets `updated >= time` on every record; if this ever
    # fails, the per-year `updatedafter` watermark in ingestion/usgs_events.py
    # would silently miss revisions.
    suite.add_expectation(
        gxe.ExpectColumnPairValuesAToBeGreaterThanB(
            column_A="updated",
            column_B="time",
            or_equal=True,
        )
    )

    return suite
