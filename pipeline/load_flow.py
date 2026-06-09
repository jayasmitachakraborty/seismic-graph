"""Prefect flow that loads the transformed datasets into Neo4j Aura.

Stage 1: MERGE node labels in parallel
         (Earthquake, Fault, FocalMechanism, GeologicalRegion).
Stage 2: MERGE relationships in parallel, each waiting only on the node
         tasks it MATCHes against:
           - TRIGGERED      needs Fault + Earthquake
           - OCCURRED_IN    needs Earthquake + GeologicalRegion
           - HAS_MECHANISM  needs Earthquake + FocalMechanism
           - AFTERSHOCK_OF  needs Earthquake

Each task opens its own driver+session via ``load._neo4j.driver`` so
Prefect workers don't share a connection. Run ``make neo4j-indexes``
once after creating a fresh Aura instance before invoking this flow.
"""

import argparse
import logging

from prefect import flow, get_run_logger, task

from load import load_nodes, load_relationships
from load._neo4j import driver


@task(name="load-earthquakes", retries=2, retry_delay_seconds=5, tags=["nodes"])
def task_load_earthquakes() -> str:
    with driver() as drv, drv.session() as session:
        load_nodes.load_earthquakes(session)
    return "Earthquake"


@task(name="load-faults", retries=2, retry_delay_seconds=5, tags=["nodes"])
def task_load_faults() -> str:
    with driver() as drv, drv.session() as session:
        load_nodes.load_faults(session)
    return "Fault"


@task(name="load-focal-mechanisms", retries=2, retry_delay_seconds=5, tags=["nodes"])
def task_load_focal_mechanisms() -> str:
    with driver() as drv, drv.session() as session:
        load_nodes.load_focal_mechanisms(session)
    return "FocalMechanism"


@task(name="load-regions", retries=2, retry_delay_seconds=5, tags=["nodes"])
def task_load_regions() -> str:
    with driver() as drv, drv.session() as session:
        load_nodes.load_regions(session)
    return "GeologicalRegion"


@task(name="load-triggered", retries=2, retry_delay_seconds=5, tags=["edges"])
def task_load_triggered() -> str:
    with driver() as drv, drv.session() as session:
        load_relationships.load_triggered(session)
    return "TRIGGERED"


@task(name="load-occurred-in", retries=2, retry_delay_seconds=5, tags=["edges"])
def task_load_occurred_in() -> str:
    with driver() as drv, drv.session() as session:
        load_relationships.load_occurred_in(session)
    return "OCCURRED_IN"


@task(name="load-has-mechanism", retries=2, retry_delay_seconds=5, tags=["edges"])
def task_load_has_mechanism() -> str:
    with driver() as drv, drv.session() as session:
        load_relationships.load_has_mechanism(session)
    return "HAS_MECHANISM"


@task(name="load-aftershock-of", retries=2, retry_delay_seconds=5, tags=["edges"])
def task_load_aftershock_of() -> str:
    with driver() as drv, drv.session() as session:
        load_relationships.load_aftershock_of(session)
    return "AFTERSHOCK_OF"


@flow(name="load-all")
def load_all() -> dict[str, str]:
    log = get_run_logger()

    log.info("Stage 1: MERGE nodes")
    earthquakes_future = task_load_earthquakes.submit()
    faults_future      = task_load_faults.submit()
    mechanisms_future  = task_load_focal_mechanisms.submit()
    regions_future     = task_load_regions.submit()

    log.info("Stage 2: MERGE relationships")
    triggered_future = task_load_triggered.submit(
        wait_for=[faults_future, earthquakes_future],
    )
    occurred_in_future = task_load_occurred_in.submit(
        wait_for=[earthquakes_future, regions_future],
    )
    has_mechanism_future = task_load_has_mechanism.submit(
        wait_for=[earthquakes_future, mechanisms_future],
    )
    aftershock_of_future = task_load_aftershock_of.submit(
        wait_for=[earthquakes_future],
    )

    return {
        "earthquakes":      earthquakes_future.result(),
        "faults":           faults_future.result(),
        "focal_mechanisms": mechanisms_future.result(),
        "regions":          regions_future.result(),
        "triggered":        triggered_future.result(),
        "occurred_in":      occurred_in_future.result(),
        "has_mechanism":    has_mechanism_future.result(),
        "aftershock_of":    aftershock_of_future.result(),
    }


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    argparse.ArgumentParser(description=__doc__).parse_args()
    load_all()


if __name__ == "__main__":
    main()
