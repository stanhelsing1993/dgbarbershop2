"""Tema dos gráficos Plotly.

OURO_SERIE (#b8860b) foi validado contra a superfície escura (#14120f):
luminosidade dentro da banda de séries e contraste >= 3:1. O dourado da
marca (#d4af37) é claro demais para marcas de gráfico — use-o só no chrome.
"""

import plotly.graph_objects as go
import plotly.io as pio

OURO = "#d4af37"
OURO_SERIE = "#b8860b"
TINTA = "#ebe4d8"
TINTA_SECUNDARIA = "#b6ac9c"
GRADE = "#2b2721"
EIXO = "#3a3428"

_template = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family='system-ui, "Segoe UI", sans-serif', size=13, color=TINTA_SECUNDARIA),
        title=dict(font=dict(color=TINTA)),
        colorway=[OURO_SERIE],
        xaxis=dict(gridcolor=GRADE, linecolor=EIXO, zerolinecolor=EIXO),
        yaxis=dict(gridcolor=GRADE, linecolor=EIXO, zerolinecolor=EIXO),
        hoverlabel=dict(bgcolor="#211d17", bordercolor="rgba(212,175,55,0.4)", font=dict(color=TINTA)),
        bargap=0.35,
        barcornerradius=4,
        margin=dict(l=40, r=20, t=30, b=40),
        showlegend=False,
    )
)


def registrar_tema() -> None:
    """Registra e ativa o template 'barbearia' como padrão do Plotly."""
    pio.templates["barbearia"] = _template
    pio.templates.default = "barbearia"
