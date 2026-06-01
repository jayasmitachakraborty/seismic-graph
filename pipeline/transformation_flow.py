"""Prefect flow that runs the transform DAG.

Stage 1: clean events + faults in parallel.
Stage 2: link-events-to-faults, build-aftershock-edges, join-cmt-to-events
         fan out, each waiting only on the cleans it needs.
Stage 3: quality gates on faults and aftershock edges.

Tasks read inputs from disk via ``utils.dtypes`` typed readers rather than
passing DataFrames through Prefect.
"""

import argparse
import logging

from prefect import flow, get_run_logger, task

from quality import run_checks
from transform import (
    build_aftershock_edges,
    clean_events,
    clean_faults,
    join_cmt_to_events,
    link_events_to_faults,
)


@task(name="clean-events", retries=1, tags=["clean"])
def task_clean_events() -> str:
    clean_events.clean_events()
    return clean_events.OUTPUT_BLOB


@task(name="clean-faults", retries=1, tags=["clean"])
def task_clean_faults() -> str:
    clean_faults.clean_faults()
    return clean_faults.FLAT_BLOB


@task(name="link-events-to-faults", retries=1, tags=["join"])
def task_link_events_to_faults() -> str:
    link_events_to_faults.link_events_to_faults()
    return link_events_to_faults.OUTPUT_BLOB


@task(name="build-aftershock-edges", retries=1, tags=["join"])
def task_build_aftershock_edges() -> str:
    build_aftershock_edges.build_aftershock_edges()
    return build_aftershock_edges.OUTPUT_BLOB


@task(name="join-cmt-to-events", retries=1, tags=["join"])
def task_join_cmt_to_events() -> str:
    join_cmt_to_events.join_cmt_to_events()
    return join_cmt_to_events.OUTPUT_BLOB


@task(name="check-faults", retries=0, tags=["quality"])
def check_faults_quality() -> str:
    if not run_checks.check_faults():
        raise RuntimeError(
            "faults_suite failed; see quality/reports/faults_suite.html"
        )
    return "faults_suite"


@task(name="check-aftershock-edges", retries=0, tags=["quality"])
def check_aftershock_edges_quality() -> str:
    if not run_checks.check_aftershock_edges():
        raise RuntimeError(
            "aftershock_edges_suite failed; "
            "see quality/reports/aftershock_edges_suite.html"
        )
    return "aftershock_edges_suite"


@flow(name="transform-all")
def transform_all() -> dict[str, str]:
    log = get_run_logger()

    log.info("Stage 1: clean events + faults")
    events_future = task_clean_events.submit()
    faults_future = task_clean_faults.submit()

    log.info("Stage 2: downstream joins")
    link_future = task_link_events_to_faults.submit(
        wait_for=[events_future, faults_future],
    )
    aftershock_future = task_build_aftershock_edges.submit(
        wait_for=[events_future],
    )
    cmt_future = task_join_cmt_to_events.submit(
        wait_for=[events_future],
    )

    log.info("Stage 3: quality gates")
    faults_quality_future = check_faults_quality.submit(
        wait_for=[faults_future],
    )
    aftershock_quality_future = check_aftershock_edges_quality.submit(
        wait_for=[aftershock_future],
    )

    return {
        "events":                   events_future.result(),
        "faults":                   faults_future.result(),
        "event_fault_edges":        link_future.result(),
        "aftershock_edges":         aftershock_future.result(),
        "event_cmt_edges":          cmt_future.result(),
        "faults_quality":           faults_quality_future.result(),
        "aftershock_edges_quality": aftershock_quality_future.result(),
    }


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    argparse.ArgumentParser(description=__doc__).parse_args()
    transform_all()


if __name__ == "__main__":
    main()
