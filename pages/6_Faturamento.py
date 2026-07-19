from datetime import date
from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st

from src.database.connection import get_session
from src.repositories import funcionario_repository
from src.services import faturamento_service
from src.ui.components import moeda, percentual, render_styled_table
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

st.title("💵 Faturamento e Pagamentos")


def _gerar_excel(dataframe: pd.DataFrame, aba: str) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        dataframe.to_excel(writer, index=False, sheet_name=aba)
    return output.getvalue()


st.write("### 📆 Período de análise")
col1, col2 = st.columns(2)
with col1:
    data_inicio = st.date_input("Data Inicial", value=date.today().replace(day=1), format="DD/MM/YYYY")
with col2:
    data_fim = st.date_input("Data Final", value=date.today(), format="DD/MM/YYYY")

with get_session() as session:
    resumo = faturamento_service.resumo_financeiro(session, data_inicio, data_fim)
    pagamentos = faturamento_service.relatorio_pagamentos(session, data_inicio, data_fim)
    por_forma = faturamento_service.receita_por_forma_pagamento(session, data_inicio, data_fim)
    total_geral = faturamento_service.faturamento_total(session)
    por_funcionario = faturamento_service.faturamento_por_funcionario(session)
    por_mes = faturamento_service.faturamento_por_mes(session)
    por_ano = faturamento_service.faturamento_por_ano(session)
    funcionarios = funcionario_repository.listar(session)
    percentuais = {f.id: f.percentual_comissao for f in funcionarios}

st.write("### 💰 Resumo do Período")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Receita Bruta", moeda(resumo["receita_bruta"]))
col2.metric(
    "Pagamentos aos Funcionários",
    moeda(resumo["pagamentos_funcionarios"]),
    help="Comissões geradas no período, pela % cadastrada de cada funcionário.",
)
col3.metric(
    "Descontos (vales pendentes)",
    moeda(resumo["descontos"]),
    help="Vales ainda não abatidos em acerto, que serão descontados no próximo pagamento.",
)
col4.metric(
    "Receita Total (Loja)",
    moeda(resumo["receita_loja"]),
    help="Receita bruta menos as comissões dos funcionários.",
)
st.caption(
    f"Já pago em acertos no período: **{moeda(resumo['pagos'])}** · "
    f"Líquido restante a pagar: **{moeda(resumo['liquido_a_pagar'])}** — "
    "registre os acertos na página **Pagamentos**."
)

st.write("### 💳 Receita por Forma de Pagamento")
df_forma = pd.DataFrame(por_forma)
if not df_forma.empty:
    render_styled_table(
        df_forma.rename(
            columns={"forma": "Forma de Pagamento", "receita": "Receita", "atendimentos": "Atendimentos"}
        ),
        format_map={"Receita": moeda},
    )
else:
    st.info("Nenhum atendimento concluído no período.")

st.markdown("---")
st.write("### 🧾 Relatório de Pagamentos completo")
df_pagamentos = pd.DataFrame(pagamentos)
if not df_pagamentos.empty:
    df_exibicao = df_pagamentos.drop(columns=["funcionario_id"]).rename(
        columns={
            "funcionario": "Funcionário",
            "atendimentos": "Atendimentos",
            "receita_bruta": "Receita Bruta",
            "percentual": "% Comissão",
            "comissao": "Comissão",
            "descontos": "Descontos (vales)",
            "pago": "Já Pago",
            "liquido": "Líquido a Pagar",
        }
    )
    render_styled_table(
        df_exibicao,
        format_map={
            "Receita Bruta": moeda,
            "% Comissão": percentual,
            "Comissão": moeda,
            "Descontos (vales)": moeda,
            "Já Pago": moeda,
            "Líquido a Pagar": moeda,
        },
    )
    st.download_button(
        "📥 Baixar Relatório de Pagamentos em Excel",
        data=_gerar_excel(df_exibicao, "Pagamentos"),
        file_name="relatorio_pagamentos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
else:
    st.info("Nenhum atendimento concluído ou vale lançado no período selecionado.")

st.markdown("---")
st.write("### 💳 Detalhamento de Repasse por Atendimento")

nomes_funcionarios = ["Todos"] + [f.nome for f in funcionarios]
funcionario_filtro = st.selectbox("Funcionário", nomes_funcionarios)

with get_session() as session:
    linhas = faturamento_service.faturamento_por_periodo(
        session, data_inicio, data_fim, None if funcionario_filtro == "Todos" else funcionario_filtro
    )

repasse = faturamento_service.calcular_repasse(linhas, percentuais=percentuais)
df_repasse = pd.DataFrame(repasse)

if not df_repasse.empty:
    df_detalhe = df_repasse.rename(
        columns={
            "funcionario": "Funcionário",
            "servico": "Serviço",
            "preco_servico": "Preço",
            "data": "Data",
            "percentual": "% Comissão",
            "repasse_funcionario": "Repasse Funcionário",
            "repasse_loja": "Repasse Loja",
        }
    ).drop(columns=["funcionario_id"])

    render_styled_table(
        df_detalhe,
        format_map={
            "Preço": moeda,
            "% Comissão": percentual,
            "Repasse Funcionário": moeda,
            "Repasse Loja": moeda,
        },
    )
    st.download_button(
        "📥 Baixar Detalhamento em Excel",
        data=_gerar_excel(df_detalhe, "Repasse"),
        file_name="relatorio_repasse.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
else:
    st.info("Nenhum registro encontrado para o filtro selecionado.")

st.markdown("---")
st.write("### 📈 Histórico Geral")
st.metric("💰 Faturamento acumulado da Loja (Concluídos)", moeda(total_geral))

st.write("#### 👤 Desempenho por Funcionário")
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

st.write("#### 📅 Faturamento por Mês")
df_mes = pd.DataFrame([{"Mês": r.mes, "Faturamento": r.faturamento} for r in por_mes])
render_styled_table(df_mes, format_map={"Faturamento": moeda})
if not df_mes.empty:
    st.plotly_chart(px.bar(df_mes.sort_values("Mês"), x="Mês", y="Faturamento"), use_container_width=True)

st.write("#### 🗓️ Faturamento Anual")
df_ano = pd.DataFrame([{"Ano": r.ano, "Faturamento": r.faturamento} for r in por_ano])
render_styled_table(df_ano, format_map={"Faturamento": moeda})
