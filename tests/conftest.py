"""Test-session storage isolation.

pytest imports this module before any test module (and therefore before any
nexa code), so setting these env vars here guarantees that every test run
writes to throwaway storage instead of the developer's real nexa.db /
chroma_data. Without this, e2e fixtures persist mocked exchanges into the
user's actual persistent memory.
"""
import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="nexa-test-data-")

os.environ.setdefault("NEXA_DB_PATH", os.path.join(_TMP, "nexa.db"))
os.environ.setdefault("NEXA_CHROMA_PATH", ":memory:")
