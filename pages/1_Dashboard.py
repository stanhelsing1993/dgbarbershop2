from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder

from src.database.connection import get_session
from src.database.models import STATUS_CONCLUIDO
from src.repositories import cliente_repository
from src.services import dashboard_service
from src.services.agendamento_service import STATUS_LABELS
from src.ui.components import moeda, percentual
from src.ui.theme import registrar_tema
from utils import load_static_files

load_static_files()
registrar_tema()

if "usuario_logado" not in st.session_state:
    st.warning("Você precisa estar logado para acessar esta página.")
    st.stop()

st.title("📊 Dashboard")

with get_session() as session:
    linhas = dashboard_service.listar_agendamentos_detalhado(session)
    total_clientes = cliente_repository.contar(session)

df = pd.DataFrame(
    [
        {
            "Cliente": r.cliente,
            "Funcionario": r.funcionario,
            "Servico": r.servico,
            "Preco": r.preco,
            "Data": r.data,
            "Hora": r.hora,
            "Status": r.status,
        }
        for r in linhas
    ]
)

if df.empty:
    st.info("Nenhum agendamento cadastrado ainda. Comece pela página Agenda. 💈")
    st.stop()

# ---------------------------------------------------------------- filtros
hoje = date.today()
PRESETS = {
    "Hoje": (hoje, hoje),
    "Últimos 7 dias": (hoje - timedelta(days=6), hoje),
    "Últimos 30 dias": (hoje - timedelta(days=29), hoje),
    "Mês atual": (hoje.replace(day=1), hoje),
    "Todo o período": (None, None),
    "Personalizado": None,
}

col_periodo, col_func, col_custom = st.columns([1.1, 1, 1.6])
with col_periodo:
    periodo = st.selectbox("📆 Período", options=list(PRESETS.keys()), index=2)
with col_func:
    funcionario_sel = st.selectbox("🧑‍🔧 Funcionário", ["Todos"] + sorted(df["Funcionario"].unique()))

if periodo == "Personalizado":
    with col_custom:
        intervalo = st.date_input(
            "Intervalo", value=(hoje - timedelta(days=29), hoje), max_value=hoje, format="DD/MM/YYYY"
        )
    if not (isinstance(intervalo, tuple) and len(intervalo) == 2):
        st.info("Selecione a data final do intervalo para continuar.")
        st.stop()
    inicio, fim = intervalo
else:
    inicio, fim = PRESETS[periodo]


def _filtrar(base: pd.DataFrame, data_inicio, data_fim, funcionario: str) -> pd.DataFrame:
    filtrado = base
    if funcionario != "Todos":
        filtrado = filtrado[filtrado["Funcionario"] == funcionario]
    if data_inicio is not None:
        filtrado = filtrado[(filtrado["Data"] >= data_inicio) & (filtrado["Data"] <= data_fim)]
    return filtrado


df_atual = _filtrar(df, inicio, fim, funcionario_sel)
metricas = dashboard_service.calcular_metricas(df_atual)

# Comparativo com o período imediatamente anterior de mesma duração.
deltas: dict = {}
if inicio is not None:
    duracao = fim - inicio
    anterior_fim = inicio - timedelta(days=1)
    anterior_inicio = anterior_fim - duracao
    metricas_ant = dashboard_service.calcular_metricas(_filtrar(df, anterior_inicio, anterior_fim, funcionario_sel))

    def _variacao(atual: float, anterior: float):
        if not anterior:
            return None
        return f"{(atual - anterior) / anterior * 100:+.1f}%".replace(".", ",")

    def _pontos(atual: float, anterior: float):
        return f"{(atual - anterior) * 100:+.1f} p.p.".replace(".", ",")

    deltas = {
        "agendamentos": _variacao(metricas["total_agendamentos"], metricas_ant["total_agendamentos"]),
        "receita": _variacao(metricas["receita"], metricas_ant["receita"]),
        "ticket": _variacao(metricas["ticket_medio"], metricas_ant["ticket_medio"]),
        "cancelamento": _pontos(metricas["taxa_cancelamento"], metricas_ant["taxa_cancelamento"]),
        "no_show": _pontos(metricas["taxa_no_show"], metricas_ant["taxa_no_show"]),
    }

# ---------------------------------------------------------------- métricas
st.markdown("## 📈 Visão Geral")

col1, col2, col3, col4 = st.columns(4)
col1.metric("👥 Total de Clientes", total_clientes, help="Clientes cadastrados na base (não varia com o filtro).")
col2.metric("📋 Agendamentos", metricas["total_agendamentos"], delta=deltas.get("agendamentos"))
col3.metric("💵 Receita (Concluídos)", moeda(metricas["receita"]), delta=deltas.get("receita"))
col4.metric("🎯 Ticket Médio", moeda(metricas["ticket_medio"]), delta=deltas.get("ticket"))

col5, col6, col7, col8 = st.columns(4)
col5.metric(
    "❌ Taxa de Cancelamento",
    percentual(metricas["taxa_cancelamento"]),
    delta=deltas.get("cancelamento"),
    delta_color="inverse",
)
col6.metric(
    "🚪 Taxa de No-show",
    percentual(metricas["taxa_no_show"]),
    delta=deltas.get("no_show"),
    delta_color="inverse",
)
col7.metric("✂️ Serviço Mais Vendido", metricas["servico_mais_vendido"] or "—")
col8.metric("🏆 Barbeiro Destaque", metricas["barbeiro_top"] or "—")

if deltas:
    st.caption(
        f"Setas comparam com o período anterior de mesma duração "
        f"({anterior_inicio.strftime('%d/%m/%Y')} a {anterior_fim.strftime('%d/%m/%Y')})."
    )

# ---------------------------------------------------------------- gráficos
if df_atual.empty:
    st.info("Nenhum agendamento no período selecionado.")
    st.stop()

st.markdown("## 📊 Análises")
concluidos = df_atual[df_atual["Status"] == STATUS_CONCLUIDO]

g1, g2 = st.columns(2)
with g1:
    st.write("#### 💵 Receita por Dia")
    if concluidos.empty:
        st.info("Sem atendimentos concluídos no período.")
    else:
        receita_dia = concluidos.groupby("Data")["Preco"].sum().reset_index(name="Receita")
        fig = px.bar(receita_dia, x="Data", y="Receita", labels={"Receita": "Receita (R$)"})
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

with g2:
    st.write("#### 📅 Atendimentos por Dia")
    atendimentos_dia = df_atual.groupby("Data").size().reset_index(name="Atendimentos")
    fig = px.bar(atendimentos_dia, x="Data", y="Atendimentos")
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)

g3, g4 = st.columns(2)
with g3:
    st.write("#### ✂️ Serviços Mais Vendidos")
    if concluidos.empty:
        st.info("Sem atendimentos concluídos no período.")
    else:
        servicos_populares = concluidos["Servico"].value_counts().reset_index()
        servicos_populares.columns = ["Servico", "Quantidade"]
        fig = px.bar(
            servicos_populares.sort_values("Quantidade"),
            x="Quantidade",
            y="Servico",
            orientation="h",
            labels={"Servico": ""},
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

with g4:
    st.write("#### 🧑‍🔧 Faturamento por Funcionário")
    if concluidos.empty:
        st.info("Sem atendimentos concluídos no período.")
    else:
        faturamento_func = concluidos.groupby("Funcionario")["Preco"].sum().reset_index()
        fig = px.bar(faturamento_func, x="Funcionario", y="Preco", labels={"Preco": "Faturamento (R$)", "Funcionario": ""})
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------- detalhes
with st.expander("🗓️ Agenda detalhada do período"):
    colunas_grid = ["Cliente", "Funcionario", "Servico", "Data", "Hora", "Status"]
    df_grid = df_atual[colunas_grid].assign(
        Data=df_atual["Data"].map(lambda d: d.strftime("%d/%m/%Y")),
        Status=df_atual["Status"].map(lambda s: STATUS_LABELS.get(s, s)),
    )
    gb = GridOptionsBuilder.from_dataframe(df_grid)
    gb.configure_pagination(paginationAutoPageSize=True)
    gb.configure_side_bar()
    gb.configure_default_column(resizable=True, sortable=True, filterable=True)
    AgGrid(df_grid, gridOptions=gb.build(), height=400, fit_columns_on_grid_load=True)
    st.download_button(
        "📥 Exportar CSV",
        data=df_grid.to_csv(index=False).encode("utf-8-sig"),
        file_name="agendamentos_periodo.csv",
        mime="text/csv",
    )
