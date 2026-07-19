import pandas as pd
import streamlit as st

from src.database.connection import get_session
from src.repositories import funcionario_repository
from src.ui.components import percentual, render_styled_table
from utils import load_static_files

load_static_files()

if "usuario_logado" not in st.session_state:
    st.warning("Você precisa estar logado para acessar esta página.")
    st.stop()
if st.session_state.get("role") != "admin":
    st.warning("Apenas administradores podem gerenciar funcionários.")
    st.stop()

st.title("🧑‍🔧 Gestão de Funcionários")

with st.form("funcionario_form"):
    nome_func = st.text_input("Nome do Funcionário")
    cargo_func = st.text_input("Cargo / Especialidade")
    comissao_func = st.number_input(
        "% de comissão (parte do funcionário em cada serviço)",
        min_value=0.0,
        max_value=100.0,
        value=50.0,
        step=5.0,
    )
    submitted = st.form_submit_button("Cadastrar Funcionário")

    if submitted:
        if nome_func.strip() and cargo_func.strip():
            with get_session() as session:
                funcionario_repository.criar(
                    session, nome_func.strip(), cargo_func.strip(), comissao_func / 100
                )
            st.success("Funcionário cadastrado com sucesso!")
            st.rerun()
        else:
            st.warning("Preencha nome e cargo.")

st.write("### 📋 Lista de Funcionários")
with get_session() as session:
    funcionarios = funcionario_repository.listar(session)
    df_funcionarios = pd.DataFrame(
        [
            {
                "ID": f.id,
                "Nome": f.nome,
                "Cargo": f.especialidade,
                "Comissao": f.percentual_comissao,
            }
            for f in funcionarios
        ]
    )

render_styled_table(
    df_funcionarios.rename(columns={"Comissao": "Comissão"}) if not df_funcionarios.empty else df_funcionarios,
    format_map={"Comissão": percentual},
)

if not df_funcionarios.empty:
    st.write("### ✏️ Editar ou Excluir Funcionário")
    opcoes = {f"{row.Nome} (#{row.ID})": row.ID for row in df_funcionarios.itertuples()}
    selecionado = st.selectbox("Selecione o funcionário", list(opcoes.keys()))
    funcionario_id = opcoes[selecionado]
    atual = df_funcionarios[df_funcionarios["ID"] == funcionario_id].iloc[0]

    with st.form("editar_funcionario_form"):
        novo_nome = st.text_input("Nome", value=atual["Nome"])
        novo_cargo = st.text_input("Cargo", value=atual["Cargo"] or "")
        nova_comissao = st.number_input(
            "% de comissão",
            min_value=0.0,
            max_value=100.0,
            value=float(atual["Comissao"]) * 100,
            step=5.0,
        )
        col1, col2 = st.columns(2)
        atualizar = col1.form_submit_button("Atualizar")
        excluir = col2.form_submit_button("Excluir")

    if atualizar:
        if novo_nome.strip() and novo_cargo.strip():
            with get_session() as session:
                funcionario_repository.atualizar(
                    session, funcionario_id, novo_nome.strip(), novo_cargo.strip(), nova_comissao / 100
                )
            st.success("Funcionário atualizado com sucesso!")
            st.rerun()
        else:
            st.warning("Preencha nome e cargo.")

    if excluir:
        with get_session() as session:
            funcionario_repository.excluir(session, funcionario_id)
        st.warning("Funcionário excluído com sucesso!")
        st.rerun()
