"""USGS earthquake events ingestion (https://earthquake.usgs.gov/fdsnws/event/1/).

First run backfills each year; subsequent runs pull only records whose
``updated`` is newer than the per-year watermark stored in ``_watermarks.json``.
"""

import json
import logging
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

from ingestion import _storage
from utils import dtypes

URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
SUBDIR = "usgs_events"
COMBINED_FILE = "usgs_events.csv"
STATE_FILE = "_watermarks.json"
TIMEOUT = 120
PAGE_LIMIT = 20000

log = logging.getLogger(__name__)


def _year_rel(year: int) -> str:
    return f"{_storage.dataset_prefix(SUBDIR)}/usgs_events_{year}.csv"


def _combined_rel() -> str:
    return f"{_storage.dataset_prefix(SUBDIR)}/{COMBINED_FILE}"


def _year_path(year: int) -> Path:
    return _storage.DATA_DIR / _year_rel(year)


def _state_path() -> Path:
    return _storage.DATA_DIR / _storage.dataset_prefix(SUBDIR) / STATE_FILE


def _load_state() -> dict[str, str]:
    p = _state_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        log.warning("Corrupt watermark file at %s; ignoring.", p)
        return {}


def _save_state(state: dict[str, str]) -> None:
    p = _state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True))
    tmp.replace(p)


def load_year(year: int) -> pd.DataFrame:
    p = _year_path(year)
    if not p.exists():
        return pd.DataFrame()
    return dtypes.read_raw_usgs_events(p)


def read_combined() -> pd.DataFrame:
    return dtypes.read_raw_usgs_events(_storage.DATA_DIR / _combined_rel())


def year_watermark(year: int) -> pd.Timestamp | None:
    raw = _load_state().get(str(year))
    return pd.Timestamp(raw) if raw else None


def set_year_watermark(year: int, ts: pd.Timestamp) -> None:
    state = _load_state()
    state[str(year)] = ts.isoformat()
    _save_state(state)


def fetch_year(
    year: int,
    min_magnitude: float = 4.5,
    updated_after: pd.Timestamp | None = None,
) -> pd.DataFrame:
    params = {
        "format": "csv",
        "starttime": f"{year}-01-01",
        "endtime": f"{year + 1}-01-01",
        "minmagnitude": min_magnitude,
        "orderby": "time-asc",
        "limit": PAGE_LIMIT,
    }
    if updated_after is not None:
        params["updatedafter"] = updated_after.isoformat()

    r = requests.get(URL, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    df = pd.read_csv(StringIO(r.text))
    if len(df) >= PAGE_LIMIT:
        log.warning("Year %s hit the %s-row cap; narrow the window.", year, PAGE_LIMIT)
    return df


def upsert_year(year: int, new_df: pd.DataFrame) -> str | None:
    existing = load_year(year)
    if new_df.empty and existing.empty:
        return None
    if new_df.empty:
        return str(_year_path(year))
    combined = pd.concat([existing, new_df], ignore_index=True)
    if "id" in combined.columns:
        combined = (
            combined.sort_values("updated")
            .drop_duplicates(subset=["id"], keep="last")
            .reset_index(drop=True)
        )
    uri = _storage.write_csv(combined, _year_rel(year))
    if "updated" in combined.columns:
        ts = pd.to_datetime(combined["updated"], utc=True, errors="coerce").max()
        if pd.notna(ts):
            set_year_watermark(year, ts)
    return uri


def write_combined(years: range) -> str | None:
    frames = [load_year(y) for y in years]
    frames = [f for f in frames if not f.empty]
    if not frames:
        return None
    combined = pd.concat(frames, ignore_index=True)
    return _storage.write_csv(combined, _combined_rel())
