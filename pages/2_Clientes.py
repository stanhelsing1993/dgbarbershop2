import streamlit as st
import sqlite3
import pandas as pd
from utils import load_static_files

# Carregar CSS
load_static_files()

# Conectar ao Banco de Dados
conn = sqlite3.connect('barbearia.db')
cursor = conn.cursor()

# --- 📋 CADASTRO DE CLIENTES ---
with st.form("cliente_form"):
    st.write("### 📝 Cadastro de Cliente")
    nome = st.text_input("Nome do Cliente")
    telefone = st.text_input("Telefone")
    email = st.text_input("Email")
    submitted = st.form_submit_button("Cadastrar Cliente")

    if submitted:
        cursor.execute("INSERT INTO clientes (nome, telefone, email) VALUES (?, ?, ?)", (nome, telefone, email))
        conn.commit()
        st.success("Cliente cadastrado com sucesso!")

# --- 📊 LISTAGEM DE CLIENTES ---
# Obter lista de clientes
clientes = cursor.execute("SELECT * FROM clientes").fetchall()

# Título estilizado
st.write("### 📋 Lista de Clientes")

# Criar um DataFrame com os dados
df_clientes = pd.DataFrame(clientes, columns=["ID", "Nome", "Telefone", "Email"])

# Estilizar a tabela
st.table(df_clientes.style.set_table_styles([
    {'selector': 'thead th', 'props': [('background-color', '#4CAF50'), ('color', 'white'), ('text-align', 'center')]},
    {'selector': 'tbody tr:nth-child(even)', 'props': [('background-color', '#f2f2f2')]},
    {'selector': 'tbody tr:hover', 'props': [('background-color', '#ddd')]},
    {'selector': 'td', 'props': [('text-align', 'center'), ('padding', '10px')]}
]))
