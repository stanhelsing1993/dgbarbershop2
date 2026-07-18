from typing import Optional

import pandas as pd
import streamlit as st

_TABLE_STYLES = [
    {
        "selector": "thead th",
        "props": [
            ("background-color", "#211d17"),
            ("color", "#d4af37"),
            ("text-align", "center"),
            ("border-bottom", "2px solid #b8860b"),
            ("letter-spacing", "0.03em"),
        ],
    },
    {"selector": "tbody tr:nth-child(even)", "props": [("background-color", "#1a1712")]},
    {"selector": "tbody tr:hover", "props": [("background-color", "#26211a")]},
    {
        "selector": "td",
        "props": [
            ("text-align", "center"),
            ("padding", "10px"),
            ("color", "#ebe4d8"),
            ("border-color", "rgba(255,255,255,0.06)"),
            ("font-variant-numeric", "tabular-nums"),
        ],
    },
]


def moeda(valor: float) -> str:
    """Formata em reais no padrão brasileiro: 1234.5 -> 'R$ 1.234,50'."""
    texto = f"{valor:,.2f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    return f"R$ {texto}"


def percentual(valor: float) -> str:
    """Formata fração como percentual brasileiro: 0.253 -> '25,3%'."""
    return f"{valor * 100:.1f}".replace(".", ",") + "%"


def render_styled_table(df: pd.DataFrame, format_map: Optional[dict] = None) -> None:
    """Renderiza um DataFrame com o estilo padrão do sistema. Substitui o bloco de CSS repetido em cada página."""
    if df.empty:
        st.info("Nenhum registro encontrado.")
        return
    styler = df.style.set_table_styles(_TABLE_STYLES)
    if format_map:
        styler = styler.format(format_map)
    st.table(styler)
