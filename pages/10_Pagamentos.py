from datetime import date, timedelta
from io import BytesIO

import pandas as pd
import streamlit as st

from src.database.connection import get_session
from src.repositories import adiantamento_repository, funcionario_repository, pagamento_repository
from src.services import pagamento_service
from src.services.pagamento_service import PagamentoError
from src.ui.components import moeda, render_styled_table
from utils import load_static_files

load_static_files()

if "usuario_logado" not in st.session_state:
    st.warning("Você precisa estar logado para acessar esta página.")
    st.stop()
if st.session_state.get("role") != "admin":
    st.warning("Apenas administradores podem acessar os pagamentos.")
    st.stop()

st.title("🤝 Pagamentos aos Funcionários")

if mensagem := st.session_state.pop("flash_pagamentos", None):
    st.success(mensagem)

hoje = date.today()

with get_session() as session:
    funcionarios = funcionario_repository.listar(session)

if not funcionarios:
    st.info("Cadastre funcionários para registrar pagamentos.")
    st.stop()

# --- Registrar acerto ---
st.write("### 💳 Registrar Acerto")
st.caption(
    "O acerto calcula a comissão do período, abate **todos os vales pendentes** do "
    "funcionário (de qualquer data até o fim do período) e registra o pagamento."
)

funcionarios_dict = {f.nome: f.id for f in funcionarios}
col1, col2, col3 = st.columns(3)
with col1:
    nome_escolhido = st.selectbox("Funcionário", options=list(funcionarios_dict.keys()))
with col2:
    periodo_inicio = st.date_input("Início do período", value=hoje.replace(day=1), format="DD/MM/YYYY")
with col3:
    periodo_fim = st.date_input("Fim do período", value=hoje, format="DD/MM/YYYY")

funcionario_id = funcionarios_dict[nome_escolhido]

with get_session() as session:
    previa = pagamento_service.previa_acerto(session, funcionario_id, periodo_inicio, periodo_fim)
    vales_previa = [
        {"Data": v.data.strftime("%d/%m/%Y"), "Valor": v.valor, "Motivo": v.descricao or "—"}
        for v in previa["vales_pendentes"]
    ]

col1, col2, col3 = st.columns(3)
col1.metric("Comissão do período", moeda(previa["comissao"]))
col2.metric("Vales pendentes a abater", moeda(previa["total_vales"]))
col3.metric("💰 Líquido a pagar", moeda(previa["liquido"]))

if vales_previa:
    with st.expander(f"📄 Vales pendentes de {nome_escolhido} ({len(vales_previa)})", expanded=False):
        render_styled_table(pd.DataFrame(vales_previa), format_map={"Valor": moeda})

if previa["liquido"] < 0:
    st.error(
        "Os vales pendentes excedem a comissão do período. Amplie o período ou aguarde "
        "novas comissões antes de fazer o acerto."
    )
else:
    with st.form("acerto_form"):
        col1, col2 = st.columns(2)
        with col1:
            data_pagamento = st.date_input("Data do pagamento", value=hoje, format="DD/MM/YYYY")
        with col2:
            valor_pago = st.number_input(
                "Valor a pagar", min_value=0.0, value=float(previa["liquido"]), step=10.0
            )
        observacao = st.text_input("Observação (opcional)")
        lancar_caixa = st.checkbox(
            "Lançar como saída no caixa do dia do pagamento", value=True
        )
        confirmar = st.form_submit_button("✅ Confirmar pagamento", type="primary")

    if confirmar:
        try:
            with get_session() as session:
                pagamento_service.registrar_pagamento(
                    session,
                    funcionario_id,
                    periodo_inicio,
                    periodo_fim,
                    data_pagamento,
                    valor_pago=valor_pago,
                    observacao=observacao.strip() or None,
                    lancar_no_caixa=lancar_caixa,
                )
            st.session_state["flash_pagamentos"] = (
                f"✅ Pagamento de {moeda(valor_pago)} a {nome_escolhido} registrado"
                + (" e lançado como saída no caixa." if lancar_caixa else ".")
            )
            st.rerun()
        except PagamentoError as exc:
            st.error(str(exc))

st.markdown("---")

# --- Histórico de pagamentos ---
st.write("### 📜 Pagamentos Realizados")
col1, col2, col3 = st.columns(3)
with col1:
    hist_inicio = st.date_input("De", value=hoje - timedelta(days=90), format="DD/MM/YYYY")
with col2:
    hist_fim = st.date_input("Até", value=hoje, format="DD/MM/YYYY")
with col3:
    filtro_nome = st.selectbox("Filtrar funcionário", ["Todos"] + list(funcionarios_dict.keys()))

with get_session() as session:
    pagamentos = pagamento_repository.listar_por_periodo(
        session,
        hist_inicio,
        hist_fim,
        None if filtro_nome == "Todos" else funcionarios_dict[filtro_nome],
    )

df_pag = pd.DataFrame(
    [
        {
            "ID": p.id,
            "Funcionário": p.funcionario,
            "Pago em": p.data_pagamento.strftime("%d/%m/%Y"),
            "Período": f"{p.periodo_inicio.strftime('%d/%m')} – {p.periodo_fim.strftime('%d/%m/%Y')}",
            "Comissão": p.comissao_base,
            "Vales Abatidos": p.descontos_abatidos,
            "Valor Pago": p.valor_pago,
            "Observação": p.observacao or "—",
        }
        for p in pagamentos
    ]
)
render_styled_table(
    df_pag, format_map={"Comissão": moeda, "Vales Abatidos": moeda, "Valor Pago": moeda}
)

if not df_pag.empty:
    total_pago = df_pag["Valor Pago"].sum()
    st.caption(f"Total pago no período filtrado: **{moeda(total_pago)}**")

    def _gerar_excel(dataframe: pd.DataFrame) -> bytes:
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            dataframe.to_excel(writer, index=False, sheet_name="Pagamentos")
        return output.getvalue()

    st.download_button(
        "📥 Baixar Pagamentos em Excel",
        data=_gerar_excel(df_pag),
        file_name="pagamentos_funcionarios.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

st.markdown("---")

# --- Vales lançados ---
st.write("### 💸 Vales Lançados")
with get_session() as session:
    vales = adiantamento_repository.listar_por_periodo(session, hist_inicio, hist_fim)

df_vales = pd.DataFrame(
    [
        {
            "Data": v.data.strftime("%d/%m/%Y"),
            "Funcionário": v.funcionario,
            "Valor": v.valor,
            "Motivo": v.descricao or "—",
            "Situação": f"Abatido no acerto #{v.pagamento_id}" if v.pagamento_id else "⏳ Pendente",
        }
        for v in vales
    ]
)
render_styled_table(df_vales, format_map={"Valor": moeda})
