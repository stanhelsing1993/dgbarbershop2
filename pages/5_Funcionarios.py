import streamlit as st
import sqlite3
import pandas as pd
from utils import load_static_files

# Carregar CSS e JS
load_static_files()

# Verificar se o usuário está logado
if 'usuario_logado' not in st.session_state:
    st.warning("Você precisa estar logado para acessar esta página.")
    st.stop()  # Parar o código e não carregar o restante da página

# Título da Página
st.title("👤 Gestão de Funcionários")

# Conectar ao Banco de Dados
conn = sqlite3.connect('barbearia.db')
cursor = conn.cursor()

# Cadastro de Funcionário
with st.form("funcionario_form"):
    nome_func = st.text_input("Nome do Funcionário")
    cargo_func = st.text_input("Cargo")
    submitted = st.form_submit_button("Cadastrar Funcionário")

    if submitted:
        if nome_func and cargo_func:
            cursor.execute(
                "INSERT INTO funcionarios (nome, especialidade) VALUES (?, ?)",
                (nome_func, cargo_func)
            )
            conn.commit()
            st.success("Funcionário cadastrado com sucesso!")
        else:
            st.warning("Preencha todos os campos.")

# --- 📋 Listar Funcionários ---
st.write("### 📋 Lista de Funcionários")

# Consultar todos os funcionários cadastrados
funcionarios = cursor.execute("SELECT * FROM funcionarios").fetchall()

# Verificar se há funcionários cadastrados
if funcionarios:
    # Criar um DataFrame para os funcionários
    df_funcionarios = pd.DataFrame(funcionarios, columns=["ID", "Nome", "Cargo"])

    # Formatar as colunas antes de passar para o Streamlit
    df_funcionarios["ID"] = df_funcionarios["ID"].apply(lambda x: f"{x:d}")  # Formatar ID como inteiro
    df_funcionarios["Nome"] = df_funcionarios["Nome"].apply(lambda x: f"{x}")  # Nome como string
    df_funcionarios["Cargo"] = df_funcionarios["Cargo"].apply(lambda x: f"{x}")  # Cargo como string

    # Estilizar a tabela
    st.table(df_funcionarios.style.set_table_styles([
        {'selector': 'thead th', 'props': [('background-color', '#4CAF50'), ('color', 'white'), ('text-align', 'center')]},
        {'selector': 'tbody tr:nth-child(even)', 'props': [('background-color', '#f2f2f2')]},
        {'selector': 'tbody tr:hover', 'props': [('background-color', '#ddd')]},
        {'selector': 'td', 'props': [('text-align', 'center'), ('padding', '10px')]}
    ]))
else:
    st.info("Nenhum funcionário cadastrado.")

# Fechar Conexão
conn.close()
