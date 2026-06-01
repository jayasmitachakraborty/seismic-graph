"""MERGE seismic nodes into Neo4j. Re-runnable for incremental upserts."""

import logging

from neo4j import Session

from ingestion import global_cmt
from load._neo4j import driver, run_batched, to_records
from utils import dtypes

log = logging.getLogger(__name__)


MERGE_EARTHQUAKE = """
UNWIND $rows AS row
MERGE (e:Earthquake {event_id: row.event_id})
SET e.time      = row.occurred_at,
    e.latitude  = row.latitude,
    e.longitude = row.longitude,
    e.depth_km  = row.depth_km,
    e.magnitude = row.magnitude,
    e.place     = row.place,
    e.mag_type  = row.magType,
    e.network   = row.net,
    e.updated   = row.updated
"""

MERGE_FAULT = """
UNWIND $rows AS row
MERGE (f:Fault {fault_id: row.fault_id})
SET f.name            = row.fault_name,
    f.type            = row.fault_type,
    f.raw_type        = row.raw_type,
    f.slip_rate_mm_yr = row.slip_rate_mm_yr,
    f.dip_angle_deg   = row.dip_angle_deg,
    f.rake_deg        = row.rake_deg,
    f.country         = row.country,
    f.source          = row.source
"""

MERGE_FOCAL_MECHANISM = """
UNWIND $rows AS row
MERGE (m:FocalMechanism {cmt_id: row.cmt_id})
SET m.time              = row.occurred_at,
    m.magnitude         = row.magnitude,
    m.region            = row.region,
    m.hypo_lat          = row.hypo_lat,
    m.hypo_lon          = row.hypo_lon,
    m.hypo_depth_km     = row.hypo_depth_km,
    m.centroid_lat      = row.centroid_lat,
    m.centroid_lon      = row.centroid_lon,
    m.centroid_depth_km = row.centroid_depth_km,
    m.strike            = row.strike1,
    m.dip               = row.dip1,
    m.rake              = row.rake1,
    m.strike2           = row.strike2,
    m.dip2              = row.dip2,
    m.moment_exponent   = row.moment_exponent
"""

MERGE_REGION = """
UNWIND $rows AS row
MERGE (:GeologicalRegion {name: row.name})
"""


def load_earthquakes(session: Session) -> None:
    df = dtypes.read_events()
    run_batched(session, MERGE_EARTHQUAKE, to_records(df), "earthquakes")


def load_faults(session: Session) -> None:
    df = dtypes.read_faults()
    run_batched(session, MERGE_FAULT, to_records(df), "faults")


def load_focal_mechanisms(session: Session) -> None:
    df = global_cmt.read_combined().rename(columns={
        "event_id": "cmt_id",
        "datetime": "occurred_at",
    })
    run_batched(session, MERGE_FOCAL_MECHANISM, to_records(df), "focal_mechanisms")


def load_regions(session: Session) -> None:
    """Derive :GeologicalRegion nodes from distinct event.region values."""
    names = dtypes.read_events()["region"].dropna().drop_duplicates().sort_values()
    rows = [{"name": n} for n in names]
    run_batched(session, MERGE_REGION, rows, "regions")


def load_all() -> None:
    with driver() as drv, drv.session() as session:
        load_earthquakes(session)
        load_faults(session)
        load_focal_mechanisms(session)
        load_regions(session)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    load_all()
