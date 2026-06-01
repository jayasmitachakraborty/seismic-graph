"""Prefect flows for the seismic-graph pipeline."""

import logging

# Cap third-party loggers forwarded via PREFECT_LOGGING_EXTRA_LOGGERS
# so they don't crowd the Cloud UI.
for _name in ("requests", "urllib3", "urllib3.connectionpool", "great_expectations"):
    logging.getLogger(_name).setLevel(logging.WARNING)
