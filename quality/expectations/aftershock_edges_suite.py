"""GX suite for ``data/processed/aftershock_edges.csv``.

Enforces edge semantics: aftershock happens after the mainshock, is
smaller, and falls within the spatial window the builder uses.
"""

import great_expectations as gx
import great_expectations.expectations as gxe

from transform import build_aftershock_edges as builder

SUITE_NAME = "aftershock_edges_suite"


def build() -> gx.ExpectationSuite:
    expectations = [
        # Aftershock smaller than mainshock. The builder's stricter
        # ``mag_diff >= MAG_DIFF_MIN`` is a tuning choice; here we only assert
        # the contract (mag_diff > 0) so the suite stays semantic.
        gxe.ExpectColumnValuesToBeBetween(
            column="mag_diff", min_value=0, strict_min=True
        ),
        gxe.ExpectColumnValuesToBeBetween(
            column="time_delta_days",
            min_value=0,
            max_value=builder.TIME_WINDOW_DAYS,
        ),
        gxe.ExpectColumnValuesToBeBetween(
            column="dist_km",
            min_value=0,
            max_value=builder.DIST_THRESHOLD_KM,
        ),
    ]
    return gx.ExpectationSuite(name=SUITE_NAME, expectations=expectations)
