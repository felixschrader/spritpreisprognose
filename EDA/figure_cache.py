import streamlit as st


def get_cached_figure(page_id: str, chart_id: str, build_fn):
    # Keep figure cache intentionally small on Community Cloud memory limits.
    max_entries = 6
    signature = st.session_state.get("filter_signature", "default")
    cache = st.session_state.setdefault("figure_cache", {})
    key = (signature, page_id, chart_id)
    if key not in cache:
        if len(cache) >= max_entries:
            cache.pop(next(iter(cache)))
        cache[key] = build_fn()
    return cache[key]
