"""Create unique-key constraints in Neo4j. Run once per fresh Aura instance."""

import logging

from load._neo4j import driver

NODE_KEYS: tuple[tuple[str, str], ...] = (
    ("Earthquake",       "event_id"),
    ("Fault",            "fault_id"),
    ("FocalMechanism",   "cmt_id"),
    ("GeologicalRegion", "name"),
    ("TectonicPlate",    "plate_code"),
    ("SeismicStation",   "code"),
)

log = logging.getLogger(__name__)


def create_indexes() -> None:
    with driver() as drv, drv.session() as session:
        for label, key in NODE_KEYS:
            session.run(
                f"CREATE CONSTRAINT {label.lower()}_{key} IF NOT EXISTS "
                f"FOR (n:{label}) REQUIRE n.{key} IS UNIQUE"
            ).consume()
            log.info("%s(%s) unique", label, key)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    create_indexes()
