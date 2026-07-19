from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from src.database.connection import get_session
from src.services import faturamento_service, relatorio_service
from src.ui.components import moeda, render_styled_table
from src.ui.theme import registrar_tema
from utils import load_static_files

load_static_files()
registrar_tema()

if "usuario_logado" not in st.session_state:
    st.warning("Você precisa estar logado para acessar esta página.")
    st.stop()
if st.session_state.get("role") != "admin":
    st.warning("Apenas administradores podem acessar os relatórios.")
    st.stop()

st.title("📈 Relatórios Gerenciais")

hoje = date.today()

# --- Seleção de período ---
PRESETS = {
    "Este mês": (hoje.replace(day=1), hoje),
    "Últimos 30 dias": (hoje - timedelta(days=29), hoje),
    "Últimos 90 dias": (hoje - timedelta(days=89), hoje),
    "Este ano": (hoje.replace(month=1, day=1), hoje),
    "Personalizado": None,
}
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    preset = st.radio("Período", options=list(PRESETS.keys()), horizontal=True, label_visibility="collapsed")
if PRESETS[preset] is None:
    with col2:
        inicio = st.date_input("De", value=hoje.replace(day=1), format="DD/MM/YYYY")
    with col3:
        fim = st.date_input("Até", value=hoje, format="DD/MM/YYYY")
else:
    inicio, fim = PRESETS[preset]
    st.caption(f"📆 {inicio.strftime('%d/%m/%Y')} até {fim.strftime('%d/%m/%Y')}")

with get_session() as session:
    dados = relatorio_service.comparativo(session, inicio, fim)
    serie_receita = relatorio_service.receita_por_dia(session, inicio, fim)
    por_dia_semana = relatorio_service.atendimentos_por_dia_semana(session, inicio, fim)
    por_horario = relatorio_service.atendimentos_por_horario(session, inicio, fim)
    servicos = relatorio_service.top_servicos(session, inicio, fim)
    desempenho = relatorio_service.desempenho_funcionarios(session, inicio, fim)
    por_forma = faturamento_service.receita_por_forma_pagamento(session, inicio, fim)
    metas = relatorio_service.progresso_metas(session, dados["atual"])

atual, anterior = dados["atual"], dados["anterior"]
ant_inicio, ant_fim = dados["periodo_anterior"]


def _delta(chave, formato=lambda v: f"{v:+.1f}"):
    return formato(atual[chave] - anterior[chave])


# --- KPIs ---
st.write("### 🎯 KPIs do Período")
st.caption(
    f"Variação em relação ao período anterior ({ant_inicio.strftime('%d/%m')} – {ant_fim.strftime('%d/%m/%Y')})."
)

col1, col2, col3, col4 = st.columns(4)
col1.metric(
    "Receita Bruta", moeda(atual["receita_bruta"]),
    delta=_delta("receita_bruta", lambda v: f"{'+' if v >= 0 else '−'}{moeda(abs(v))}"),
)
col2.metric(
    "Receita da Loja", moeda(atual["receita_loja"]),
    delta=_delta("receita_loja", lambda v: f"{'+' if v >= 0 else '−'}{moeda(abs(v))}"),
    help="Receita bruta menos comissões dos funcionários.",
)
col3.metric(
    "Atendimentos Concluídos", atual["atendimentos_concluidos"],
    delta=int(atual["atendimentos_concluidos"] - anterior["atendimentos_concluidos"]),
)
col4.metric(
    "Ticket Médio", moeda(atual["ticket_medio"]),
    delta=_delta("ticket_medio", lambda v: f"{'+' if v >= 0 else '−'}{moeda(abs(v))}"),
)

col5, col6, col7, col8 = st.columns(4)
col5.metric("Clientes Únicos", atual["clientes_unicos"],
            delta=int(atual["clientes_unicos"] - anterior["clientes_unicos"]))
col6.metric(
    "Taxa de Ocupação", f"{atual['taxa_ocupacao']:.1f}%".replace(".", ","),
    delta=_delta("taxa_ocupacao", lambda v: f"{v:+.1f} p.p.".replace(".", ",")),
    help="Horários concluídos/agendados sobre a capacidade total da grade no período.",
)
col7.metric(
    "Taxa de Cancelamento", f"{atual['taxa_cancelamento']:.1f}%".replace(".", ","),
    delta=_delta("taxa_cancelamento", lambda v: f"{v:+.1f} p.p.".replace(".", ",")),
    delta_color="inverse",
)
col8.metric(
    "Taxa de No-show", f"{atual['taxa_no_show']:.1f}%".replace(".", ","),
    delta=_delta("taxa_no_show", lambda v: f"{v:+.1f} p.p.".replace(".", ",")),
    delta_color="inverse",
)

st.markdown("---")

# --- Metas / OKR ---
st.write("### 🏁 Metas do Período (OKR)")
for meta in metas:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.progress(meta["progresso"], text=meta["label"])
    with col2:
        if meta["chave"] in ("receita_mensal", "ticket_medio"):
            texto = f"{moeda(meta['atual'])} / {moeda(meta['alvo'])}"
        elif meta["chave"] == "taxa_no_show_max":
            texto = f"{meta['atual']:.1f}% (teto {meta['alvo']:.0f}%)".replace(".", ",")
        else:
            texto = f"{meta['atual']:.0f} / {meta['alvo']:.0f}"
        st.write(("✅ " if meta["atingida"] else "⏳ ") + texto)

with st.expander("⚙️ Ajustar metas"):
    with st.form("metas_form"):
        with get_session() as session:
            metas_atuais = relatorio_service.obter_metas(session)
        novos_valores = {}
        col1, col2 = st.columns(2)
        chaves = list(relatorio_service.METAS_PADRAO.keys())
        for i, chave in enumerate(chaves):
            alvo = (col1 if i % 2 == 0 else col2).number_input(
                relatorio_service.METAS_LABELS[chave],
                min_value=0.0,
                value=float(metas_atuais[chave]),
                step=10.0,
                key=f"meta_{chave}",
            )
            novos_valores[chave] = alvo
        salvar = st.form_submit_button("Salvar metas")
    if salvar:
        with get_session() as session:
            for chave, valor in novos_valores.items():
                relatorio_service.salvar_meta(session, chave, valor)
        st.success("✅ Metas atualizadas.")
        st.rerun()

st.markdown("---")

# --- Gráficos ---
st.write("### 📊 Receita ao longo do período")
df_receita = pd.DataFrame(serie_receita)
if not df_receita.empty:
    fig = px.line(df_receita, x="data", y="receita", markers=True,
                  labels={"data": "Data", "receita": "Receita (R$)"})
    fig.update_traces(line=dict(width=2), marker=dict(size=8))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Sem receita registrada no período.")

col1, col2 = st.columns(2)
with col1:
    st.write("#### 🗓️ Atendimentos por dia da semana")
    df_semana = pd.DataFrame(por_dia_semana)
    if df_semana["atendimentos"].sum() > 0:
        st.plotly_chart(
            px.bar(df_semana, x="dia", y="atendimentos",
                   labels={"dia": "", "atendimentos": "Atendimentos"}),
            use_container_width=True,
        )
    else:
        st.info("Sem atendimentos concluídos no período.")
with col2:
    st.write("#### ⏰ Horários de pico")
    df_horario = pd.DataFrame(por_horario)
    if not df_horario.empty:
        st.plotly_chart(
            px.bar(df_horario, x="hora", y="atendimentos",
                   labels={"hora": "", "atendimentos": "Atendimentos"}),
            use_container_width=True,
        )
    else:
        st.info("Sem atendimentos concluídos no período.")

st.write("#### 💳 Receita por forma de pagamento")
df_forma = pd.DataFrame(por_forma)
if not df_forma.empty:
    st.plotly_chart(
        px.bar(
            df_forma.sort_values("receita"), x="receita", y="forma", orientation="h",
            labels={"receita": "Receita (R$)", "forma": ""},
        ),
        use_container_width=True,
    )
    render_styled_table(
        df_forma.rename(
            columns={"forma": "Forma de Pagamento", "receita": "Receita", "atendimentos": "Atendimentos"}
        ),
        format_map={"Receita": moeda},
    )
else:
    st.info("Sem atendimentos concluídos no período.")

st.write("#### ✂️ Top serviços por receita")
df_servicos = pd.DataFrame(servicos)
if not df_servicos.empty:
    fig = px.bar(
        df_servicos.sort_values("receita"), x="receita", y="servico", orientation="h",
        labels={"receita": "Receita (R$)", "servico": ""},
    )
    st.plotly_chart(fig, use_container_width=True)
    render_styled_table(
        df_servicos.rename(columns={"servico": "Serviço", "quantidade": "Qtde", "receita": "Receita"}),
        format_map={"Receita": moeda},
    )
else:
    st.info("Sem serviços concluídos no período.")

st.write("#### 🧑‍🔧 Desempenho por funcionário")
df_desempenho = pd.DataFrame(desempenho)
if not df_desempenho.empty:
    st.plotly_chart(
        px.bar(df_desempenho, x="funcionario", y="receita",
               labels={"funcionario": "", "receita": "Receita (R$)"}),
        use_container_width=True,
    )
    render_styled_table(
        df_desempenho.rename(
            columns={
                "funcionario": "Funcionário",
                "atendimentos": "Atendimentos",
                "receita": "Receita",
                "comissao": "Comissão",
                "receita_loja": "Receita Loja",
                "ticket_medio": "Ticket Médio",
            }
        ),
        format_map={"Receita": moeda, "Comissão": moeda, "Receita Loja": moeda, "Ticket Médio": moeda},
    )
else:
    st.info("Sem dados de funcionários no período.")
