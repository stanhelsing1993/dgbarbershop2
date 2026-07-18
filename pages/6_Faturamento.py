from datetime import date
from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st

from src.database.connection import get_session
from src.repositories import funcionario_repository
from src.services import faturamento_service
from src.ui.components import moeda, render_styled_table
from src.ui.theme import registrar_tema
from utils import load_static_files

load_static_files()
registrar_tema()

if "usuario_logado" not in st.session_state:
    st.warning("Você precisa estar logado para acessar esta página.")
    st.stop()
if st.session_state.get("role") != "admin":
    st.warning("Apenas administradores podem acessar o faturamento.")
    st.stop()

st.title("💵 Faturamento e Repasse")

with get_session() as session:
    total = faturamento_service.faturamento_total(session)
    por_funcionario = faturamento_service.faturamento_por_funcionario(session)
    por_mes = faturamento_service.faturamento_por_mes(session)
    por_ano = faturamento_service.faturamento_por_ano(session)
    funcionarios = funcionario_repository.listar(session)

st.metric("💰 Faturamento da Loja (Concluídos)", moeda(total))

st.write("### 👤 Desempenho por Funcionário")
df_func = pd.DataFrame(
    [
        {"Funcionário": r.funcionario, "Faturamento": r.faturamento, "Atendimentos": r.atendimentos}
        for r in por_funcionario
    ]
)
render_styled_table(df_func, format_map={"Faturamento": moeda})
if not df_func.empty:
    st.plotly_chart(
        px.bar(df_func, x="Funcionário", y="Faturamento", labels={"Faturamento": "Faturamento (R$)"}),
        use_container_width=True,
    )

st.write("### 📅 Faturamento por Mês")
df_mes = pd.DataFrame([{"Mês": r.mes, "Faturamento": r.faturamento} for r in por_mes])
render_styled_table(df_mes, format_map={"Faturamento": moeda})
if not df_mes.empty:
    st.plotly_chart(px.bar(df_mes.sort_values("Mês"), x="Mês", y="Faturamento"), use_container_width=True)

st.write("### 🗓️ Faturamento Anual")
df_ano = pd.DataFrame([{"Ano": r.ano, "Faturamento": r.faturamento} for r in por_ano])
render_styled_table(df_ano, format_map={"Faturamento": moeda})

st.markdown("---")
st.write("### 💳 Cálculo de Repasse")

col1, col2, col3 = st.columns(3)
with col1:
    data_inicio = st.date_input("Data Inicial", value=date.today().replace(day=1))
with col2:
    data_fim = st.date_input("Data Final", value=date.today())
with col3:
    nomes_funcionarios = ["Todos"] + [f.nome for f in funcionarios]
    funcionario_filtro = st.selectbox("Funcionário", nomes_funcionarios)

with get_session() as session:
    linhas = faturamento_service.faturamento_por_periodo(
        session, data_inicio, data_fim, None if funcionario_filtro == "Todos" else funcionario_filtro
    )

repasse = faturamento_service.calcular_repasse(linhas)
df_repasse = pd.DataFrame(repasse)

if not df_repasse.empty:
    valor_total = df_repasse["preco_servico"].sum()
    valor_loja = df_repasse["repasse_loja"].sum()
    valor_funcionario = df_repasse["repasse_funcionario"].sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("Valor Total", moeda(valor_total))
    col2.metric("Repasse Loja", moeda(valor_loja))
    col3.metric("Repasse Funcionários", moeda(valor_funcionario))

    df_exibicao = df_repasse.rename(
        columns={
            "funcionario": "Funcionário",
            "servico": "Serviço",
            "preco_servico": "Preço",
            "data": "Data",
            "repasse_funcionario": "Repasse Funcionário",
            "repasse_loja": "Repasse Loja",
        }
    ).drop(columns=["funcionario_id"])

    render_styled_table(
        df_exibicao,
        format_map={"Preço": moeda, "Repasse Funcionário": moeda, "Repasse Loja": moeda},
    )

    def _gerar_excel(dataframe: pd.DataFrame) -> bytes:
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            dataframe.to_excel(writer, index=False, sheet_name="Repasse")
        return output.getvalue()

    st.download_button(
        "📥 Baixar Relatório em Excel",
        data=_gerar_excel(df_exibicao),
        file_name="relatorio_repasse.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
else:
    st.info("Nenhum registro encontrado para o filtro selecionado.")
