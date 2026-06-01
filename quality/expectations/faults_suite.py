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

# Canonical buckets produced by transform/clean_faults.py:FAULT_TYPE_MAP;
# pulled live so any new bucket is automatically allowed.
FAULT_TYPES: tuple[str, ...] = tuple(sorted(set(clean_faults.FAULT_TYPE_MAP.values())))


def build() -> gx.ExpectationSuite:
    suite = gx.ExpectationSuite(name=SUITE_NAME)

    for col in REQUIRED_COLUMNS:
        suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column=col))

    suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column="fault_id"))

    suite.add_expectation(
        gxe.ExpectColumnValuesToBeInSet(
            column="fault_type", value_set=list(FAULT_TYPES),
        )
    )

    # Physical-impossibility guards. GE skips nulls by default, which is what
    # we want — GEM leaves these blank for many segments.
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeBetween(
            column="dip_angle_deg", min_value=0, max_value=90,
        )
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeBetween(
            column="rake_deg", min_value=-180, max_value=180,
        )
    )
    # Cap at 200 mm/yr: fastest plate boundary (Pacific-Nazca) peaks ~160.
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeBetween(
            column="slip_rate_mm_yr", min_value=0, max_value=200,
        )
    )

    return suite
