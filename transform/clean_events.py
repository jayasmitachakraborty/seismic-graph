"""Clean & normalise USGS events into ``data/processed/events.csv``."""

import logging

import pandas as pd

from ingestion import usgs_events
from transform import _storage as processed_storage

OUTPUT_BLOB = processed_storage.processed_path("events.csv")

log = logging.getLogger(__name__)


def clean_events() -> pd.DataFrame:
    df = usgs_events.read_combined()

    df["magType"] = df["magType"].str.lower().str.strip()
    df["net"]     = df["net"].str.lower().str.strip().fillna("unknown")
    df["type"]    = df["type"].str.lower().str.strip()

    # Drop quarry blasts, explosions, etc.
    df = df[df["type"] == "earthquake"].copy()

    # "14km NNE of Ridgecrest, CA" → "CA"; fall back to the full place string.
    df["region"] = (
        df["place"].str.extract(r",\s*(.+)$")[0]
        .fillna(df["place"])
        .str.strip()
        .replace("", pd.NA)
    )

    df = df.dropna(subset=["id", "latitude", "longitude", "mag", "time"])
    df = df.drop_duplicates(subset=["id"], keep="last")

    # Physical-impossibility guards.
    df = df[df["mag"].between(-2, 10)]
    df = df[df["latitude"].between(-90, 90)]
    df = df[df["longitude"].between(-180, 180)]
    df = df[df["depth"].between(-10, 700)]

    # Rename to match Neo4j property names.
    df = df.rename(columns={
        "id":    "event_id",
        "mag":   "magnitude",
        "depth": "depth_km",
        "time":  "occurred_at",
    })

    out_cols = [
        "event_id", "occurred_at", "latitude", "longitude",
        "depth_km", "magnitude", "magType", "net",
        "place", "region", "updated",
    ]
    uri = processed_storage.write_csv(df[out_cols], OUTPUT_BLOB)
    log.info("clean_events: %s rows → %s", f"{len(df):,}", uri)
    return df


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    clean_events()
