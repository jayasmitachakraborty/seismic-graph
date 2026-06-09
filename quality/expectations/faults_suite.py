"""GX suite for ``data/processed/faults.csv``.

Gates the cleaned fault table that feeds Neo4j and the event-fault join.
"""

import great_expectations as gx
import great_expectations.expectations as gxe

from transform import clean_faults

SUITE_NAME = "faults_suite"

# Many GEM fields are sparsely populated; only the columns the loader and
# joins actually depend on are gated as not-null.
REQUIRED_COLUMNS: tuple[str, ...] = ("fault_id", "fault_type", "source")

# Canonical buckets produced by transform/clean_faults.py; pulled live so any
# new bucket is automatically allowed.
FAULT_TYPES: tuple[str, ...] = tuple(sorted(clean_faults.CANONICAL_FAULT_TYPES))


def build() -> gx.ExpectationSuite:
    expectations = [
        *(gxe.ExpectColumnValuesToNotBeNull(column=col) for col in REQUIRED_COLUMNS),
        gxe.ExpectColumnValuesToBeUnique(column="fault_id"),
        gxe.ExpectColumnValuesToBeInSet(
            column="fault_type", value_set=list(FAULT_TYPES),
        ),
        # Physical-impossibility guards. GE skips nulls by default, which is
        # what we want — GEM leaves these blank for many segments.
        gxe.ExpectColumnValuesToBeBetween(
            column="dip_angle_deg", min_value=0, max_value=90,
        ),
        gxe.ExpectColumnValuesToBeBetween(
            column="rake_deg", min_value=-180, max_value=180,
        ),
        # Cap at 300 mm/yr: GEM's net_slip_rate reaches ~263 on the fastest
        # convergent/back-arc margins (Tonga-Kermadec); 300 leaves headroom
        # while still flagging physically impossible rates.
        gxe.ExpectColumnValuesToBeBetween(
            column="slip_rate_mm_yr", min_value=0, max_value=300,
        ),
    ]
    return gx.ExpectationSuite(name=SUITE_NAME, expectations=expectations)
