import pandas as pd
import streamlit as st

from src.database.connection import get_session
from src.repositories import servico_repository
from src.ui.components import render_styled_table
from utils import load_static_files

load_static_files()

if "usuario_logado" not in st.session_state:
    st.warning("Você precisa estar logado para acessar esta página.")
    st.stop()
if st.session_state.get("role") != "admin":
    st.warning("Apenas administradores podem gerenciar serviços.")
    st.stop()

st.title("✂️ Gestão de Serviços")

with st.form("servico_form"):
    nome_servico = st.text_input("Nome do Serviço")
    preco_servico = st.number_input("Preço (R$)", min_value=0.0, format="%.2f")
    duracao_servico = st.number_input("Duração (minutos)", min_value=1, step=5)
    submitted = st.form_submit_button("Cadastrar Serviço")

    if submitted:
        if nome_servico.strip() and preco_servico > 0 and duracao_servico > 0:
            with get_session() as session:
                servico_repository.criar(session, nome_servico.strip(), preco_servico, int(duracao_servico))
            st.success("Serviço cadastrado com sucesso!")
            st.rerun()
        else:
            st.warning("Preencha nome, preço (> 0) e duração (> 0).")

st.write("### 📋 Lista de Serviços")
with get_session() as session:
    servicos = servico_repository.listar(session)
    df_servicos = pd.DataFrame(
        [{"ID": s.id, "Nome": s.nome, "Preço (R$)": s.preco, "Duração (min)": s.duracao} for s in servicos]
    )

render_styled_table(df_servicos, format_map={"Preço (R$)": "R$ {:.2f}", "Duração (min)": "{:.0f} min"})

if not df_servicos.empty:
    st.write("### ✏️ Editar ou Excluir Serviço")
    opcoes = {f"{row.Nome} (#{row.ID})": row.ID for row in df_servicos.itertuples()}
    selecionado = st.selectbox("Selecione o serviço", list(opcoes.keys()))
    servico_id = opcoes[selecionado]
    atual = df_servicos[df_servicos["ID"] == servico_id].iloc[0]

    with st.form("editar_servico_form"):
        novo_nome = st.text_input("Nome", value=atual["Nome"])
        novo_preco = st.number_input("Preço (R$)", min_value=0.0, value=float(atual["Preço (R$)"]), format="%.2f")
        nova_duracao = st.number_input("Duração (min)", min_value=1, value=int(atual["Duração (min)"]), step=5)
        col1, col2 = st.columns(2)
        atualizar = col1.form_submit_button("Atualizar")
        excluir = col2.form_submit_button("Excluir")

    if atualizar:
        if novo_nome.strip() and novo_preco > 0 and nova_duracao > 0:
            with get_session() as session:
                servico_repository.atualizar(session, servico_id, novo_nome.strip(), novo_preco, int(nova_duracao))
            st.success("Serviço atualizado com sucesso!")
            st.rerun()
        else:
            st.warning("Preencha nome, preço (> 0) e duração (> 0).")

    if excluir:
        with get_session() as session:
            servico_repository.excluir(session, servico_id)
        st.warning("Serviço excluído com sucesso!")
        st.rerun()
