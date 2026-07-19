from datetime import date, timedelta

import pandas as pd
import streamlit as st

from src.database.connection import get_session
from src.database.models import TIPO_ENTRADA, TIPO_SAIDA
from src.repositories import adiantamento_repository, caixa_repository, funcionario_repository
from src.services import caixa_service, faturamento_service
from src.services.caixa_service import CaixaError
from src.ui.components import moeda, render_styled_table
from utils import load_static_files

load_static_files()

if "usuario_logado" not in st.session_state:
    st.warning("Você precisa estar logado para acessar esta página.")
    st.stop()
if st.session_state.get("role") != "admin":
    st.warning("Apenas administradores podem acessar o caixa.")
    st.stop()

st.title("💵 Caixa Diário")

if mensagem := st.session_state.pop("flash_caixa", None):
    st.success(mensagem)

hoje = date.today()

with get_session() as session:
    pendencias = caixa_service.pendencias(session)
    status_hoje = caixa_service.status_do_dia(session, hoje)

for alerta in pendencias:
    if alerta["nivel"] == "erro":
        st.error(alerta["mensagem"])
    elif alerta["nivel"] == "aviso":
        st.warning(alerta["mensagem"])
    else:
        st.info(alerta["mensagem"])

# --- Dias anteriores pendentes de fechamento ---
with get_session() as session:
    aberturas_passadas = caixa_repository.listar_aberturas(
        session, hoje - timedelta(days=caixa_service.JANELA_PENDENCIAS_DIAS), hoje - timedelta(days=1)
    )
    dias_pendentes = [
        a.data for a in aberturas_passadas
        if caixa_repository.obter_fechamento(session, a.data) is None
    ]

if dias_pendentes:
    with st.expander("🔴 Fechar caixas de dias anteriores", expanded=True):
        dia_pendente = st.selectbox(
            "Dia pendente",
            options=dias_pendentes,
            format_func=lambda d: d.strftime("%d/%m/%Y"),
        )
        with get_session() as session:
            resumo_pendente = caixa_service.resumo_do_dia(session, dia_pendente)
        st.write(
            f"Saldo apurado de {dia_pendente.strftime('%d/%m/%Y')}: "
            f"**{moeda(resumo_pendente['saldo'])}**"
        )
        obs_pendente = st.text_input("Observação do fechamento", key="obs_pendente")
        if st.button("Fechar caixa deste dia", type="primary", key="fechar_pendente"):
            try:
                with get_session() as session:
                    caixa_service.fechar_caixa(session, dia_pendente, obs_pendente or None)
                st.session_state["flash_caixa"] = (
                    f"✅ Caixa de {dia_pendente.strftime('%d/%m/%Y')} fechado."
                )
                st.rerun()
            except CaixaError as exc:
                st.error(str(exc))

st.markdown("---")

# --- Caixa de hoje ---
st.write(f"### 📅 Hoje — {hoje.strftime('%d/%m/%Y')}")

if status_hoje == caixa_service.STATUS_NAO_ABERTO:
    st.info("O caixa de hoje ainda não foi aberto.")
    with st.form("abrir_caixa_form"):
        valor_inicial = st.number_input(
            "Valor inicial em caixa (troco)", min_value=0.0, value=0.0, step=10.0
        )
        abrir = st.form_submit_button("🔓 Abrir caixa", type="primary")
    if abrir:
        try:
            with get_session() as session:
                caixa_service.abrir_caixa(
                    session, hoje, valor_inicial, st.session_state.get("usuario_logado")
                )
            st.session_state["flash_caixa"] = "✅ Caixa aberto. Bom trabalho!"
            st.rerun()
        except CaixaError as exc:
            st.error(str(exc))
else:
    with get_session() as session:
        abertura = caixa_repository.obter_abertura(session, hoje)
        resumo = caixa_service.resumo_do_dia(session, hoje)
        movimentos = caixa_repository.listar_movimentos(session, hoje)
        vales = adiantamento_repository.listar_por_periodo(session, hoje, hoje)
        funcionarios_dict = {f.nome: f.id for f in funcionario_repository.listar(session)}

    if status_hoje == caixa_service.STATUS_FECHADO:
        st.success("✅ O caixa de hoje já foi fechado.")
    elif abertura is not None:
        st.caption(
            f"🔓 Aberto às {abertura.hora}"
            + (f" por **{abertura.aberto_por}**" if abertura.aberto_por else "")
        )

    col1, col2, col3 = st.columns(3)
    col1.metric("Valor inicial", moeda(resumo["valor_inicial"]))
    col2.metric("Receita de serviços", moeda(resumo["receita_servicos"]))
    col3.metric("Entradas avulsas", moeda(resumo["entradas"]))
    col4, col5, col6 = st.columns(3)
    col4.metric("Saídas", moeda(resumo["saidas"]))
    col5.metric("Vales (adiantamentos)", moeda(resumo["adiantamentos"]))
    col6.metric("💰 Saldo do dia", moeda(resumo["saldo"]))

    with get_session() as session:
        por_forma_dia = faturamento_service.receita_por_forma_pagamento(session, hoje, hoje)
    if por_forma_dia:
        st.caption(
            "💳 Receita de serviços por forma de pagamento: "
            + " · ".join(f"**{item['forma']}**: {moeda(item['receita'])}" for item in por_forma_dia)
        )

    caixa_aberto = status_hoje == caixa_service.STATUS_ABERTO

    if caixa_aberto:
        tab_mov, tab_vale, tab_fechar = st.tabs(
            ["➕ Movimentos", "💸 Vale / Adiantamento", "🔒 Fechar caixa"]
        )

        with tab_mov:
            with st.form("movimento_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    tipo = st.selectbox(
                        "Tipo",
                        options=[TIPO_ENTRADA, TIPO_SAIDA],
                        format_func=lambda t: "Entrada" if t == TIPO_ENTRADA else "Saída",
                    )
                with col2:
                    valor_mov = st.number_input("Valor", min_value=0.0, step=5.0)
                descricao_mov = st.text_input("Descrição (ex.: venda de pomada, compra de lâminas)")
                lancar_mov = st.form_submit_button("Lançar movimento")
            if lancar_mov:
                if valor_mov > 0 and descricao_mov.strip():
                    with get_session() as session:
                        caixa_repository.criar_movimento(
                            session, hoje, tipo, valor_mov, descricao_mov.strip()
                        )
                    st.session_state["flash_caixa"] = "✅ Movimento lançado."
                    st.rerun()
                else:
                    st.warning("Informe valor maior que zero e uma descrição.")

        with tab_vale:
            if funcionarios_dict:
                with st.form("vale_form", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        funcionario_vale = st.selectbox(
                            "Funcionário", options=list(funcionarios_dict.keys())
                        )
                    with col2:
                        valor_vale = st.number_input("Valor do vale", min_value=0.0, step=10.0)
                    descricao_vale = st.text_input("Motivo (opcional)")
                    lancar_vale = st.form_submit_button("Lançar vale")
                if lancar_vale:
                    if valor_vale > 0:
                        with get_session() as session:
                            adiantamento_repository.criar(
                                session,
                                funcionarios_dict[funcionario_vale],
                                hoje,
                                valor_vale,
                                descricao_vale.strip() or None,
                            )
                        st.session_state["flash_caixa"] = "✅ Vale lançado — será descontado no acerto."
                        st.rerun()
                    else:
                        st.warning("Informe um valor maior que zero.")
            else:
                st.info("Cadastre funcionários para lançar vales.")

        with tab_fechar:
            st.warning(
                "O fechamento registra o snapshot do dia e bloqueia novos lançamentos. "
                "Confira o saldo antes de fechar."
            )
            observacao = st.text_input("Observação do fechamento (opcional)")
            if st.button("🔒 Fechar caixa de hoje", type="primary"):
                try:
                    with get_session() as session:
                        caixa_service.fechar_caixa(session, hoje, observacao or None)
                    st.session_state["flash_caixa"] = "✅ Caixa de hoje fechado. Até amanhã!"
                    st.rerun()
                except CaixaError as exc:
                    st.error(str(exc))

    if movimentos:
        st.write("#### 📄 Movimentos do dia")
        df_mov = pd.DataFrame(
            [
                {
                    "ID": m.id,
                    "Tipo": "Entrada" if m.tipo == TIPO_ENTRADA else "Saída",
                    "Valor": m.valor,
                    "Descrição": m.descricao,
                }
                for m in movimentos
            ]
        )
        render_styled_table(df_mov, format_map={"Valor": moeda})
        if caixa_aberto:
            opcoes_mov = {f"#{m.id} · {m.descricao} ({moeda(m.valor)})": m.id for m in movimentos}
            col1, col2 = st.columns([3, 1])
            with col1:
                excluir_escolhido = st.selectbox(
                    "Excluir movimento lançado por engano",
                    options=list(opcoes_mov.keys()),
                    index=None,
                    placeholder="Selecione...",
                )
            with col2:
                if st.button("Excluir") and excluir_escolhido:
                    with get_session() as session:
                        caixa_repository.excluir_movimento(session, opcoes_mov[excluir_escolhido])
                    st.session_state["flash_caixa"] = "✅ Movimento excluído."
                    st.rerun()

    if vales:
        st.write("#### 💸 Vales do dia")
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

st.markdown("---")
st.write("### 🗂️ Histórico de Fechamentos")
col1, col2 = st.columns(2)
with col1:
    inicio_hist = st.date_input("De", value=hoje - timedelta(days=30), format="DD/MM/YYYY")
with col2:
    fim_hist = st.date_input("Até", value=hoje, format="DD/MM/YYYY")

with get_session() as session:
    fechamentos = caixa_repository.listar_fechamentos(session, inicio_hist, fim_hist)

df_fech = pd.DataFrame(
    [
        {
            "Data": f.data.strftime("%d/%m/%Y"),
            "Receita Serviços": f.receita_servicos,
            "Entradas": f.entradas,
            "Saídas": f.saidas,
            "Vales": f.adiantamentos,
            "Saldo": f.saldo,
            "Observação": f.observacao or "—",
        }
        for f in fechamentos
    ]
)
render_styled_table(
    df_fech,
    format_map={
        "Receita Serviços": moeda,
        "Entradas": moeda,
        "Saídas": moeda,
        "Vales": moeda,
        "Saldo": moeda,
    },
)
