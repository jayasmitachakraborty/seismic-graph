"""Prefect ingestion flows.

``ingest-all`` runs all four dataset ingestions in parallel. ``ingest-events``
and ``ingest-cmt`` are focused pathways for the two fast-moving sources so each
can be run/scheduled on its own cadence (events ~daily, CMT ~monthly).

USGS events output is gated by a Great Expectations quality check.
"""

import argparse
import logging
from datetime import datetime, timezone

from prefect import flow, get_run_logger, task

from ingestion import gem_faults, global_cmt, tectonic_plates, usgs_events
from quality import run_checks


def _current_year() -> int:
    return datetime.now(timezone.utc).year


@task(name="ingest-gem-faults", retries=3, retry_delay_seconds=5, tags=["gem-faults"])
def ingest_gem_faults() -> str:
    log = get_run_logger()
    gdf = gem_faults.fetch()
    log.info("Fetched %s fault features", len(gdf))
    uri = gem_faults.write(gdf)
    log.info("Wrote %s", uri)
    return uri


@task(name="ingest-global-cmt", retries=3, retry_delay_seconds=5, tags=["global-cmt"])
def ingest_global_cmt() -> str | None:
    log = get_run_logger()
    frames = []
    for slice_ in global_cmt.SLICES:
        df = global_cmt.fetch_slice(slice_)
        log.info("Wrote %s (%s rows)", global_cmt.write_slice(slice_, df), len(df))
        frames.append(df)
    uri = global_cmt.write_combined(frames)
    log.info("Wrote combined %s", uri)
    return uri


@task(name="ingest-tectonic-plates", tags=["tectonic-plates"])
def ingest_tectonic_plates() -> dict[str, str]:
    log = get_run_logger()
    plates = tectonic_plates.load_plates(
        tectonic_plates.DATASETS_DIR / tectonic_plates.PLATES_FILE
    )
    boundaries = tectonic_plates.load_plate_boundaries(
        tectonic_plates.DATASETS_DIR / tectonic_plates.BOUNDARIES_FILE
    )
    plates_uri = tectonic_plates.write_plates(plates)
    boundaries_uri = tectonic_plates.write_plate_boundaries(boundaries)
    log.info("Wrote %s and %s", plates_uri, boundaries_uri)
    return {"plates": plates_uri, "boundaries": boundaries_uri}


@task(name="ingest-usgs-events", retries=3, retry_delay_seconds=5, tags=["usgs"])
def ingest_usgs_events(start_year: int = 2015, end_year: int | None = None) -> str | None:
    log = get_run_logger()
    if end_year is None:
        end_year = _current_year()
    # end_year is inclusive so the current year is always ingested.
    years = range(start_year, end_year + 1)
    for year in years:
        watermark = usgs_events.year_watermark(year)
        df = usgs_events.fetch_year(year, updated_after=watermark)
        log.info("Fetched %s events for %s (since %s)", len(df), year, watermark)
        usgs_events.upsert_year(year, df)
    uri = usgs_events.write_combined(years)
    log.info("Wrote combined %s", uri)
    return uri


@task(name="check-events", retries=0, tags=["quality"])
def check_events_quality() -> str:
    if not run_checks.check_events():
        raise RuntimeError("events_suite failed; see quality/reports/events_suite.html")
    return "events_suite"


@flow(name="ingest-events")
def ingest_events(start_year: int = 2015, end_year: int | None = None) -> dict:
    usgs_future = ingest_usgs_events.submit(start_year, end_year)
    quality_future = check_events_quality.submit(wait_for=[usgs_future])
    return {
        "usgs_events": usgs_future.result(),
        "events_quality": quality_future.result(),
    }


@flow(name="ingest-cmt")
def ingest_cmt() -> dict:
    cmt_future = ingest_global_cmt.submit()
    return {"global_cmt": cmt_future.result()}


@flow(name="ingest-all")
def ingest_all(start_year: int = 2015, end_year: int | None = None) -> dict:
    usgs_future = ingest_usgs_events.submit(start_year, end_year)
    futures = {
        "gem_faults": ingest_gem_faults.submit(),
        "global_cmt": ingest_global_cmt.submit(),
        "tectonic_plates": ingest_tectonic_plates.submit(),
        "usgs_events": usgs_future,
        "events_quality": check_events_quality.submit(wait_for=[usgs_future]),
    }
    return {name: f.result() for name, f in futures.items()}


def _add_year_args(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--start-year", type=int, default=2015)
    sp.add_argument(
        "--end-year",
        type=int,
        default=_current_year(),
        help="Last year to ingest, inclusive (defaults to the current year).",
    )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="target")

    _add_year_args(sub.add_parser("all", help="Ingest every dataset."))
    _add_year_args(sub.add_parser("events", help="Ingest USGS events only."))
    sub.add_parser("cmt", help="Ingest the Global CMT catalog only.")

    args = p.parse_args()
    start_year = getattr(args, "start_year", 2015)
    end_year = getattr(args, "end_year", _current_year())

    if args.target == "events":
        ingest_events(start_year=start_year, end_year=end_year)
    elif args.target == "cmt":
        ingest_cmt()
    else:  # "all" or no subcommand
        ingest_all(start_year=start_year, end_year=end_year)


if __name__ == "__main__":
    main()
