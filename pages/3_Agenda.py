from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from src.database.connection import get_session
from src.database.models import FORMAS_PAGAMENTO, STATUS_AGENDADO, STATUS_CONCLUIDO
from src.repositories import agendamento_repository, cliente_repository, funcionario_repository, servico_repository
from src.services import agendamento_service
from src.services.agendamento_service import (
    MENSAGEM_COMPROMISSO,
    STATUS_LABELS,
    AgendamentoDuplicadoError,
    ClienteBloqueadoError,
    ConclusaoAntecipadaError,
    ConflitoDeHorarioError,
)
from src.ui.components import render_styled_table
from utils import load_static_files

load_static_files()

st.title("📅 Agenda de Atendimentos")

with get_session() as session:
    clientes_dict = {c.nome: c.id for c in cliente_repository.listar(session)}
    funcionarios_dict = {f.nome: f.id for f in funcionario_repository.listar(session)}
    servicos_dict = {s.nome: s.id for s in servico_repository.listar(session)}

st.write("### 📌 Novo Agendamento")
st.info(MENSAGEM_COMPROMISSO)

col1, col2, col3 = st.columns(3)
with col1:
    cliente = st.selectbox("Cliente", options=list(clientes_dict.keys()), index=None, placeholder="Selecione...")
with col2:
    funcionario = st.selectbox(
        "Funcionário", options=list(funcionarios_dict.keys()), index=None, placeholder="Selecione..."
    )
with col3:
    servico = st.selectbox("Serviço", options=list(servicos_dict.keys()), index=None, placeholder="Selecione...")

data = st.date_input(
    "Data do Atendimento",
    value=None,
    min_value=agendamento_service.data_minima_agendamento(),
    format="DD/MM/YYYY",
)
st.caption("ℹ️ Agendamentos são feitos com pelo menos 1 dia de antecedência.")

hora = None
if data and funcionario:
    with get_session() as session:
        horarios = agendamento_service.horarios_disponiveis(session, funcionarios_dict[funcionario], data)
    if horarios:
        hora = st.selectbox(
            "Horário", options=horarios, index=None, placeholder="Selecione um horário disponível"
        )
    else:
        st.warning("⚠️ Não há mais horários disponíveis para este funcionário nesta data.")
elif data and not funcionario:
    st.info("Selecione um funcionário para ver os horários disponíveis.")

if st.button("Agendar", type="primary"):
    if cliente and funcionario and servico and data and hora:
        try:
            with get_session() as session:
                agendamento_service.criar_agendamento(
                    session,
                    clientes_dict[cliente],
                    funcionarios_dict[funcionario],
                    servicos_dict[servico],
                    data,
                    hora,
                )
            st.success("✅ Agendamento realizado com sucesso!")
            st.rerun()
        except AgendamentoDuplicadoError as exc:
            st.warning(f"⚠️ {exc}")
        except (ClienteBloqueadoError, ConflitoDeHorarioError, ValueError) as exc:
            st.error(str(exc))
    else:
        st.warning("⚠️ Preencha todos os campos, incluindo data e horário.")


# Encaixe: cliente atendido na hora, sem agendamento prévio (só equipe).
if "usuario_logado" in st.session_state:
    with st.expander("⚡ Lançar atendimento sem agendamento (encaixe)"):
        with st.form("avulso_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                cliente_avulso = st.selectbox(
                    "Cliente", options=list(clientes_dict.keys()), index=None, placeholder="Selecione..."
                )
            with col2:
                funcionario_avulso = st.selectbox(
                    "Funcionário", options=list(funcionarios_dict.keys()), index=None, placeholder="Selecione..."
                )
            with col3:
                servico_avulso = st.selectbox(
                    "Serviço", options=list(servicos_dict.keys()), index=None, placeholder="Selecione..."
                )
            col4, col5, col6 = st.columns(3)
            with col4:
                data_avulso = st.date_input(
                    "Data", value=date.today(), max_value=date.today(), format="DD/MM/YYYY"
                )
            with col5:
                hora_avulso = st.time_input(
                    "Hora", value=datetime.now().time().replace(second=0, microsecond=0)
                )
            with col6:
                forma_avulso = st.selectbox(
                    "Forma de pagamento",
                    options=list(FORMAS_PAGAMENTO.keys()),
                    format_func=FORMAS_PAGAMENTO.get,
                    index=None,
                    placeholder="Selecione...",
                )
            lancar = st.form_submit_button("Lançar como concluído", type="primary")

        if lancar:
            if cliente_avulso and funcionario_avulso and servico_avulso and forma_avulso:
                try:
                    with get_session() as session:
                        agendamento_service.lancar_atendimento_avulso(
                            session,
                            clientes_dict[cliente_avulso],
                            funcionarios_dict[funcionario_avulso],
                            servicos_dict[servico_avulso],
                            dia=data_avulso,
                            hora=hora_avulso.strftime("%H:%M"),
                            forma_pagamento=forma_avulso,
                        )
                    st.success("✅ Atendimento avulso lançado como concluído!")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
            else:
                st.warning("⚠️ Selecione cliente, funcionário, serviço e forma de pagamento.")


def _montar_df(linhas) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ID": r.id,
                "Cliente": r.cliente,
                "Funcionário": r.funcionario,
                "Serviço": r.servico,
                "Data": r.data.strftime("%d/%m/%Y"),
                "Hora": r.hora,
                "Status": STATUS_LABELS.get(r.status, r.status),
                "Pagamento": FORMAS_PAGAMENTO.get(r.forma_pagamento, "—"),
            }
            for r in linhas
        ]
    )


hoje = date.today()
with get_session() as session:
    proximos = agendamento_repository.listar_detalhado(session, a_partir_de=hoje)
    historico = agendamento_repository.listar_detalhado(session, ate=hoje - timedelta(days=1))

tab_proximos, tab_historico = st.tabs(["📋 Próximos Agendamentos", "🕓 Histórico"])

with tab_proximos:
    render_styled_table(_montar_df(proximos))

with tab_historico:
    pendentes = [r for r in historico if r.status == STATUS_AGENDADO]
    if pendentes:
        st.warning(
            f"⚠️ {len(pendentes)} atendimento(s) em data passada ainda constam como 'Agendado'. "
            "Marque como Concluído, Cancelado ou Não compareceu para manter os relatórios corretos."
        )
    # Histórico do mais recente para o mais antigo.
    render_styled_table(_montar_df(list(reversed(historico))))

def _rotulo(r) -> str:
    return (
        f"#{r.id} · {r.data.strftime('%d/%m/%Y')} {r.hora} · {r.cliente} · "
        f"{r.servico} com {r.funcionario} ({STATUS_LABELS.get(r.status, r.status)})"
    )


# Apenas a equipe altera status (a página é pública para agendamento).
if "usuario_logado" in st.session_state:
    if mensagem := st.session_state.pop("flash_status", None):
        st.success(mensagem)

    st.write("### ✅ Encerrar Atendimentos")
    st.caption(
        "Somente atendimentos pendentes aparecem aqui — ao encerrar, saem da lista. "
        "A receita só entra no financeiro quando o atendimento é marcado como **Concluído**."
    )

    # Pendentes em ordem cronológica: os mais antigos são os mais urgentes de encerrar.
    pendentes = [r for r in list(historico) + list(proximos) if r.status == STATUS_AGENDADO]
    if pendentes:
        opcoes = {_rotulo(r): r.id for r in pendentes}
        selecionados = st.multiselect(
            "Atendimentos pendentes", options=list(opcoes.keys()), placeholder="Selecione um ou mais..."
        )
        encerramentos = [s for s in STATUS_LABELS if s != STATUS_AGENDADO]
        col1, col2 = st.columns(2)
        with col1:
            novo_status = st.selectbox(
                "Encerrar como",
                options=encerramentos,
                format_func=STATUS_LABELS.get,
                index=None,
                placeholder="Selecione...",
            )
        forma_encerramento = None
        if novo_status == STATUS_CONCLUIDO:
            with col2:
                forma_encerramento = st.selectbox(
                    "Forma de pagamento",
                    options=list(FORMAS_PAGAMENTO.keys()),
                    format_func=FORMAS_PAGAMENTO.get,
                    index=None,
                    placeholder="Selecione...",
                )
        if st.button("Encerrar selecionados", type="primary"):
            if novo_status == STATUS_CONCLUIDO and not forma_encerramento:
                st.warning("⚠️ Informe a forma de pagamento para concluir o atendimento.")
            elif selecionados and novo_status:
                try:
                    with get_session() as session:
                        alterados = agendamento_service.alterar_status_em_lote(
                            session,
                            [opcoes[s] for s in selecionados],
                            novo_status,
                            forma_pagamento=forma_encerramento,
                        )
                    st.session_state["flash_status"] = (
                        f"✅ {alterados} atendimento(s) encerrado(s) como {STATUS_LABELS[novo_status]}."
                    )
                    st.rerun()
                except ConclusaoAntecipadaError as exc:
                    st.error(str(exc))
            else:
                st.warning("⚠️ Selecione ao menos um atendimento e como encerrá-lo.")
    else:
        st.info("🎉 Nenhum atendimento pendente de encerramento.")

    encerrados = [r for r in reversed(list(historico) + list(proximos)) if r.status != STATUS_AGENDADO]
    if encerrados:
        with st.expander("✏️ Corrigir um lançamento já encerrado"):
            st.caption("Uso excepcional: reabrir ou reclassificar um atendimento encerrado por engano.")
            opcoes_corrigir = {_rotulo(r): r.id for r in encerrados}
            col1, col2 = st.columns([2, 1])
            with col1:
                escolhido = st.selectbox(
                    "Atendimento", options=list(opcoes_corrigir.keys()), index=None, placeholder="Selecione..."
                )
            with col2:
                status_corrigido = st.selectbox(
                    "Novo status",
                    options=list(STATUS_LABELS.keys()),
                    format_func=STATUS_LABELS.get,
                    index=None,
                    placeholder="Selecione...",
                )
            forma_corrigida = None
            if status_corrigido == STATUS_CONCLUIDO:
                forma_corrigida = st.selectbox(
                    "Forma de pagamento",
                    options=list(FORMAS_PAGAMENTO.keys()),
                    format_func=FORMAS_PAGAMENTO.get,
                    index=None,
                    placeholder="Selecione...",
                    key="forma_corrigida",
                )
            if st.button("Corrigir lançamento"):
                if status_corrigido == STATUS_CONCLUIDO and not forma_corrigida:
                    st.warning("⚠️ Informe a forma de pagamento para concluir o atendimento.")
                elif escolhido and status_corrigido:
                    try:
                        with get_session() as session:
                            agendamento_service.alterar_status(
                                session,
                                opcoes_corrigir[escolhido],
                                status_corrigido,
                                forma_pagamento=forma_corrigida,
                            )
                        st.session_state["flash_status"] = "✅ Lançamento corrigido."
                        st.rerun()
                    except (ConclusaoAntecipadaError, ConflitoDeHorarioError) as exc:
                        st.error(str(exc))
                else:
                    st.warning("⚠️ Selecione o atendimento e o novo status.")
