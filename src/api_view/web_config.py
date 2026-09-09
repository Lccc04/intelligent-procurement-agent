"""Backward-compatible persistence entry point for the web layer."""

from api_view.persistence import FileDB, MongoDB, PersistentDB, build_db


# The default is a durable local JSON store.  Set PERSISTENCE_BACKEND=mongo to
# use the MongoDB adapter without changing any API or Agent code.
db = build_db()


def get_db() -> PersistentDB:
    return db
