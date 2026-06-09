"""Global CMT moment-tensor catalog ingestion (https://www.globalcmt.org/).

NDK format reference: https://www.globalcmt.org/CMT/allorder.ndk_explained
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd
import requests

from ingestion import _storage
from utils import dtypes

BASE_URL = "https://www.ldeo.columbia.edu/~gcmt/projects/CMT/catalog"
SUBDIR = "global_cmt"
COMBINED_FILE = "cmt_all.csv"
TIMEOUT = 300
NDK_BLOCK_LINES = 5


def _current_year() -> int:
    return datetime.now(timezone.utc).year


# 1976–2020 ships as one bundle; 2021 onward only as monthly files. The upper
# bound tracks the current year so newly published months are always fetched
# (missing months 404 and are skipped via Slice.optional).
MONTHLY_START_YEAR = 2021
MONTHLY_YEARS = range(MONTHLY_START_YEAR, _current_year() + 1)
_MONTHS = (
    "jan", "feb", "mar", "apr", "may", "jun",
    "jul", "aug", "sep", "oct", "nov", "dec",
)

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Slice:
    source: str  # path relative to BASE_URL, e.g. "jan76_dec20.ndk"
    optional: bool = False  # monthly files lag; tolerate a 404 instead of failing

    @property
    def url(self) -> str:
        return f"{BASE_URL}/{self.source}"

    @property
    def csv(self) -> str:
        stem = self.source.rsplit("/", 1)[-1].removesuffix(".ndk")
        return f"cmt_{stem}.csv"


def _monthly_slices(years: range) -> tuple[Slice, ...]:
    return tuple(
        Slice(f"NEW_MONTHLY/{year}/{month}{year % 100:02d}.ndk", optional=True)
        for year in years
        for month in _MONTHS
    )


SLICES: tuple[Slice, ...] = (
    Slice("jan76_dec20.ndk"),
    *_monthly_slices(MONTHLY_YEARS),
)


def _parse_block(block: list[str]) -> dict | None:
    """Parse one 5-line NDK block; return None on malformed input."""
    try:
        # Line 1: hypocenter
        l1 = block[0].split()
        # Normalise "YYYY/MM/DD" → ISO so pd.to_datetime parses without help.
        date_str = l1[1].replace("/", "-") + "T" + l1[2]
        hypo_lat, hypo_lon, hypo_depth = float(l1[3]), float(l1[4]), float(l1[5])
        hypo_mag = float(l1[7])
        region = " ".join(l1[8:])

        # Line 2: event ID, e.g. "C202302060117A"
        event_id = block[1].split()[0]

        # Line 3: centroid (lat, lon, depth at fields 3, 5, 7)
        l3 = block[2].split()
        centroid_lat, centroid_lon, centroid_depth = (
            float(l3[3]), float(l3[5]), float(l3[7]),
        )

        # Line 4: scalar moment exponent (first field)
        exponent = int(block[3].split()[0])

        # Line 5: last 5 tokens are strike1 dip1 strike2 dip2 rake1
        # (rake2 sometimes appended as a 6th).
        l5 = block[4].split()
        strike1, dip1, strike2, dip2, rake1 = (
            int(l5[-5]), int(l5[-4]), int(l5[-3]), int(l5[-2]), int(l5[-1]),
        )
    except (IndexError, ValueError):
        return None

    return {
        "event_id": event_id,
        "datetime": date_str,
        "hypo_lat": hypo_lat,
        "hypo_lon": hypo_lon,
        "hypo_depth_km": hypo_depth,
        "magnitude": hypo_mag,
        "region": region,
        "centroid_lat": centroid_lat,
        "centroid_lon": centroid_lon,
        "centroid_depth_km": centroid_depth,
        "strike1": strike1, "dip1": dip1, "rake1": rake1,
        "strike2": strike2, "dip2": dip2,
        "moment_exponent": exponent,
    }


def parse_ndk_text(text: str) -> pd.DataFrame:
    records: list[dict] = []
    block: list[str] = []
    for line in text.splitlines():
        if line.strip() == "":
            continue
        block.append(line)
        if len(block) == NDK_BLOCK_LINES:
            parsed = _parse_block(block)
            if parsed is not None:
                records.append(parsed)
            block = []
    return pd.DataFrame(records)


def fetch_slice(slice_: Slice) -> pd.DataFrame:
    log.info("Downloading %s", slice_.url)
    r = requests.get(slice_.url, timeout=TIMEOUT)
    if slice_.optional and r.status_code == 404:
        log.warning("Optional slice %s not published yet (404); skipping", slice_.url)
        return pd.DataFrame()
    r.raise_for_status()
    r.encoding = "ascii"
    return parse_ndk_text(r.text)


def write_slice(slice_: Slice, df: pd.DataFrame) -> str:
    return _storage.write_csv(
        df, f"{_storage.dataset_prefix(SUBDIR)}/{slice_.csv}"
    )


def write_combined(frames: list[pd.DataFrame]) -> str | None:
    non_empty = [f for f in frames if not f.empty]
    if not non_empty:
        return None
    combined = pd.concat(non_empty, ignore_index=True).drop_duplicates(
        subset=["event_id"], keep="first"
    )
    return _storage.write_csv(
        combined, f"{_storage.dataset_prefix(SUBDIR)}/{COMBINED_FILE}"
    )


def read_combined() -> pd.DataFrame:
    return dtypes.read_raw_global_cmt(
        _storage.DATA_DIR / _storage.dataset_prefix(SUBDIR) / COMBINED_FILE
    )
