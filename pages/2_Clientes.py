import pandas as pd
import streamlit as st

from src.database.connection import get_session
from src.repositories import cliente_repository
from src.ui.components import render_styled_table
from utils import load_static_files

load_static_files()

if "usuario_logado" not in st.session_state:
    st.warning("Você precisa estar logado para acessar esta página.")
    st.stop()

st.title("👤 Gestão de Clientes")

with st.form("cliente_form"):
    st.write("### 📝 Cadastro de Cliente")
    nome = st.text_input("Nome do Cliente")
    telefone = st.text_input("Telefone")
    email = st.text_input("Email")
    submitted = st.form_submit_button("Cadastrar Cliente")

    if submitted:
        if nome.strip():
            with get_session() as session:
                cliente_repository.criar(session, nome.strip(), telefone.strip(), email.strip())
            st.success("Cliente cadastrado com sucesso!")
            st.rerun()
        else:
            st.warning("Informe ao menos o nome do cliente.")

st.write("### 📋 Lista de Clientes")
with get_session() as session:
    clientes = cliente_repository.listar(session)
    df_clientes = pd.DataFrame(
        [{"ID": c.id, "Nome": c.nome, "Telefone": c.telefone, "Email": c.email} for c in clientes]
    )

render_styled_table(df_clientes)

if not df_clientes.empty:
    st.write("### ✏️ Editar ou Excluir Cliente")
    opcoes = {f"{row.Nome} (#{row.ID})": row.ID for row in df_clientes.itertuples()}
    selecionado = st.selectbox("Selecione o cliente", list(opcoes.keys()))
    cliente_id = opcoes[selecionado]
    atual = df_clientes[df_clientes["ID"] == cliente_id].iloc[0]

    with st.form("editar_cliente_form"):
        novo_nome = st.text_input("Nome", value=atual["Nome"])
        novo_telefone = st.text_input("Telefone", value=atual["Telefone"] or "")
        novo_email = st.text_input("Email", value=atual["Email"] or "")
        col1, col2 = st.columns(2)
        atualizar = col1.form_submit_button("Atualizar")
        excluir = col2.form_submit_button("Excluir")

    if atualizar:
        if novo_nome.strip():
            with get_session() as session:
                cliente_repository.atualizar(
                    session, cliente_id, novo_nome.strip(), novo_telefone.strip(), novo_email.strip()
                )
            st.success("Cliente atualizado com sucesso!")
            st.rerun()
        else:
            st.warning("O nome não pode ficar vazio.")

    if excluir:
        with get_session() as session:
            cliente_repository.excluir(session, cliente_id)
        st.warning("Cliente excluído com sucesso!")
        st.rerun()
