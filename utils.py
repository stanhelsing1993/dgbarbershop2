from pathlib import Path

import streamlit as st

STATIC_DIR = Path(__file__).resolve().parent / "static"


def load_static_files() -> None:
    """Injeta o CSS customizado do projeto em cada página."""
    for css_file in ("style.css",):
        file_path = STATIC_DIR / css_file
        if file_path.exists():
            css = file_path.read_text(encoding="utf-8")
            st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
