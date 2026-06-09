"""MERGE seismic relationships into Neo4j. Run after ``load_nodes``."""

import logging

from neo4j import Session

from load._neo4j import driver, run_batched, to_records
from utils import dtypes

log = logging.getLogger(__name__)


# (:Fault)-[:TRIGGERED {dist_to_fault_km}]->(:Earthquake)
MERGE_TRIGGERED = """
UNWIND $rows AS row
MATCH (f:Fault      {fault_id: row.fault_id})
MATCH (e:Earthquake {event_id: row.event_id})
MERGE (f)-[r:TRIGGERED]->(e)
SET r.dist_to_fault_km = row.dist_to_fault_km
"""

# (:Earthquake)-[:OCCURRED_IN]->(:GeologicalRegion)
MERGE_OCCURRED_IN = """
UNWIND $rows AS row
MATCH (e:Earthquake       {event_id: row.event_id})
MATCH (r:GeologicalRegion {name:     row.region})
MERGE (e)-[:OCCURRED_IN]->(r)
"""

# (:Earthquake)-[:HAS_MECHANISM {dist_km, dt_sec}]->(:FocalMechanism)
MERGE_HAS_MECHANISM = """
UNWIND $rows AS row
MATCH (e:Earthquake     {event_id: row.event_id})
MATCH (m:FocalMechanism {cmt_id:   row.cmt_id})
MERGE (e)-[r:HAS_MECHANISM]->(m)
SET r.dist_km = row.dist_km,
    r.dt_sec  = row.dt_sec
"""

# (:Earthquake aftershock)-[:AFTERSHOCK_OF {dist_km, time_delta_days, mag_diff}]->(:Earthquake mainshock)
MERGE_AFTERSHOCK_OF = """
UNWIND $rows AS row
MATCH (after:Earthquake {event_id: row.aftershock_id})
MATCH (main:Earthquake  {event_id: row.mainshock_id})
MERGE (after)-[r:AFTERSHOCK_OF]->(main)
SET r.dist_km         = row.dist_km,
    r.time_delta_days = row.time_delta_days,
    r.mag_diff        = row.mag_diff
"""


def load_triggered(session: Session) -> None:
    df = dtypes.read_event_fault_edges()
    run_batched(session, MERGE_TRIGGERED, to_records(df), "triggered")


def load_occurred_in(session: Session) -> None:
    rows = dtypes.read_events()[["event_id", "region"]].dropna(subset=["region"])
    run_batched(session, MERGE_OCCURRED_IN, to_records(rows), "occurred_in")


def load_has_mechanism(session: Session) -> None:
    df = dtypes.read_event_cmt_edges()
    run_batched(session, MERGE_HAS_MECHANISM, to_records(df), "has_mechanism")


def load_aftershock_of(session: Session) -> None:
    df = dtypes.read_aftershock_edges()
    run_batched(session, MERGE_AFTERSHOCK_OF, to_records(df), "aftershock_of")


def load_all() -> None:
    with driver() as drv, drv.session() as session:
        load_triggered(session)
        load_occurred_in(session)
        load_has_mechanism(session)
        load_aftershock_of(session)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    load_all()
