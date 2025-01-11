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
st.title("🛠️ Gestão de Serviços")

# Conectar ao Banco de Dados
conn = sqlite3.connect('barbearia.db')
cursor = conn.cursor()

# --- 📝 Cadastro de Serviço ---
with st.form("servico_form"):
    nome_servico = st.text_input("Nome do Serviço")
    preco_servico = st.number_input("Preço (R$)", min_value=0.0, format="%.2f")
    duracao_servico = st.number_input("Duração (minutos)", min_value=0)
    submitted = st.form_submit_button("Cadastrar Serviço")

    if submitted:
        if nome_servico  and preco_servico and duracao_servico:
            cursor.execute(
                "INSERT INTO servicos (nome, preco, duracao) VALUES ( ?, ?, ?)",
                (nome_servico, preco_servico, duracao_servico)
            )
            conn.commit()
            st.success("Serviço cadastrado com sucesso!")
        else:
            st.warning("Preencha todos os campos corretamente.")

# --- 📋 Listar Serviços ---
st.write("### 📋 Lista de Serviços")

# Consultar todos os serviços cadastrados
servicos = cursor.execute("SELECT * FROM servicos").fetchall()

# Verificar se há serviços cadastrados
if servicos:
    # Criar um DataFrame para os serviços
    df_servicos = pd.DataFrame(servicos, columns=["ID", "Nome", "Preço (R$)", "Duração (min)"])

    # Ajustar a formatação
    df_servicos["Preço (R$)"] = df_servicos["Preço (R$)"].apply(lambda x: f"R$ {x:.2f}" if pd.notnull(x) else "N/A")
    df_servicos["Duração (min)"] = df_servicos["Duração (min)"].apply(lambda x: f"{int(x)} min" if pd.notnull(x) else "N/A")

    # Estilizar a tabela
    st.table(df_servicos.style.set_table_styles([
        {'selector': 'thead th', 'props': [('background-color', '#4CAF50'), ('color', 'white'), ('text-align', 'center')]},
        {'selector': 'tbody tr:nth-child(even)', 'props': [('background-color', '#f2f2f2')]},
        {'selector': 'tbody tr:hover', 'props': [('background-color', '#ddd')]},
        {'selector': 'td', 'props': [('text-align', 'center'), ('padding', '10px')]},
    ]))
else:
    st.info("Nenhum serviço cadastrado.")

# Fechar Conexão
conn.close()
