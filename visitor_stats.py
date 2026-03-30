"""
Anonyme Besucherstatistik (PostgreSQL).

Umgebungsvariable oder Streamlit-Secrets:
  DATABASE_URL = postgresql://...?sslmode=require

Ohne gültige URL: stiller No-Op (kein Absturz des Dashboards).
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_table_ok = False


def get_database_url() -> str | None:
    try:
        import streamlit as st

        s = st.secrets
        if "DATABASE_URL" in s:
            return str(s["DATABASE_URL"])
        pg = s.get("postgres")
        if isinstance(pg, dict) and pg.get("url"):
            return str(pg["url"])
    except Exception:
        pass
    return os.environ.get("DATABASE_URL")


def ensure_table() -> None:
    global _table_ok
    if _table_ok:
        return
    url = get_database_url()
    if not url:
        return
    try:
        import psycopg2

        conn = psycopg2.connect(url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS visitor_events (
                        id UUID PRIMARY KEY,
                        ts_utc TIMESTAMPTZ NOT NULL,
                        session_id TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        tab_name TEXT,
                        meta JSONB
                    );
                    CREATE INDEX IF NOT EXISTS idx_visitor_events_ts
                        ON visitor_events (ts_utc);
                    CREATE INDEX IF NOT EXISTS idx_visitor_events_session
                        ON visitor_events (session_id);
                    """
                )
            conn.commit()
            _table_ok = True
        finally:
            conn.close()
    except Exception as e:
        logger.debug("visitor_stats.ensure_table: %s", e)


def record_event(
    session_id: str,
    event_type: str,
    *,
    tab_name: str | None = None,
    meta: dict | None = None,
) -> None:
    url = get_database_url()
    if not url:
        return
    ensure_table()
    if not _table_ok:
        return
    try:
        import psycopg2

        conn = psycopg2.connect(url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO visitor_events (id, ts_utc, session_id, event_type, tab_name, meta)
                    VALUES (%s::uuid, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        str(uuid.uuid4()),
                        datetime.now(timezone.utc),
                        session_id,
                        event_type,
                        tab_name,
                        json.dumps(meta or {}),
                    ),
                )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        logger.debug("visitor_stats.record_event: %s", e)


def ensure_session_id() -> str:
    import streamlit as st

    if "visitor_session_id" not in st.session_state:
        st.session_state.visitor_session_id = str(uuid.uuid4())
    return st.session_state.visitor_session_id


def init_page_view() -> None:
    """Einmal pro Session: page_view (Tab-Wechsel bei st.tabs nicht zuverlässig serverseitig erfassbar)."""
    import streamlit as st

    sid = ensure_session_id()
    if st.session_state.get("visitor_page_logged"):
        return
    ensure_table()
    record_event(sid, "page_view")
    st.session_state.visitor_page_logged = True
