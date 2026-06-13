"""Neo4j Aura driver + batched UNWIND writer for the load layer."""

import logging
import os
from contextlib import contextmanager
from typing import Iterator

import pandas as pd
from neo4j import Driver, GraphDatabase, Session

BATCH_SIZE = 5_000

log = logging.getLogger(__name__)


@contextmanager
def driver() -> Iterator[Driver]:
    drv = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(
            os.environ.get("NEO4J_USER", "neo4j"),
            os.environ["NEO4J_PASSWORD"],
        ),
        max_connection_lifetime=300,   # recycle pooled connections before they go stale
        keep_alive=True,
        connection_timeout=30,         # timeout for new connections
    )
    try:
        drv.verify_connectivity()
        yield drv
    finally:
        drv.close()


def to_records(df: pd.DataFrame) -> list[dict]:
    """DataFrame → list[dict] with NaN / NaT → None (mapped to Cypher NULL)."""
    obj = df.astype(object)
    return obj.where(obj.notna(), None).to_dict("records")


def run_batched(session: Session, query: str, rows: list[dict], label: str) -> None:
    """Stream ``rows`` through ``query`` (which must take ``$rows``) in BATCH_SIZE chunks."""
    if not rows:
        log.info("%s: nothing to load", label)
        return
    for start in range(0, len(rows), BATCH_SIZE):
        chunk = rows[start:start + BATCH_SIZE]
        session.execute_write(
            lambda tx, c=chunk: tx.run(query, rows=c).consume()
        )
    log.info("%s: %s rows", label, f"{len(rows):,}")
