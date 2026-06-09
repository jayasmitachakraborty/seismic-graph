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
    expectations = [
        *(gxe.ExpectColumnValuesToNotBeNull(column=col) for col in REQUIRED_COLUMNS),
        # Range guards mirror transform/clean_events.py.
        gxe.ExpectColumnValuesToBeBetween(column="mag", min_value=-2.0, max_value=10.0),
        gxe.ExpectColumnValuesToBeBetween(column="latitude", min_value=-90, max_value=90),
        gxe.ExpectColumnValuesToBeBetween(column="longitude", min_value=-180, max_value=180),
        gxe.ExpectColumnValuesToBeBetween(column="depth", min_value=-10, max_value=700),
        gxe.ExpectColumnValuesToBeUnique(column="id"),
        # Watermark sanity: USGS sets `updated >= time` on every record; if this
        # ever fails, the per-year `updatedafter` watermark in
        # ingestion/usgs_events.py would silently miss revisions.
        gxe.ExpectColumnPairValuesAToBeGreaterThanB(
            column_A="updated",
            column_B="time",
            or_equal=True,
            # ``time``/``updated`` are null on some low-quality detections (see
            # note above); only assert the invariant where both are present.
            ignore_row_if="either_value_is_missing",
        ),
    ]
    return gx.ExpectationSuite(name=SUITE_NAME, expectations=expectations)
