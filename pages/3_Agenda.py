import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from utils import load_static_files

# Carregar CSS
load_static_files()

# Conectar ao Banco de Dados
conn = sqlite3.connect('barbearia.db')
cursor = conn.cursor()

# Obter opções para Dropdowns
clientes = cursor.execute("SELECT id, nome FROM clientes").fetchall()
funcionarios = cursor.execute("SELECT id, nome FROM funcionarios").fetchall()
servicos = cursor.execute("SELECT id, nome FROM servicos").fetchall()

# Transformar em dicionários
clientes_dict = {str(c[1]): c[0] for c in clientes}
funcionarios_dict = {str(f[1]): f[0] for f in funcionarios}
servicos_dict = {str(s[1]): s[0] for s in servicos}


# Função para obter horários disponíveis
def obter_horarios_disponiveis(data):
    inicio = datetime.strptime("08:00", "%H:%M")
    fim = datetime.strptime("19:00", "%H:%M")
    horarios = []
    while inicio <= fim:
        horarios.append(inicio.strftime("%H:%M"))
        inicio += timedelta(minutes=30)

    # Buscar horários já agendados
    horarios_agendados = cursor.execute(
        "SELECT hora FROM agendamentos WHERE data = ?", (str(data),)
    ).fetchall()
    horarios_agendados = [h[0] for h in horarios_agendados]

    # Remover horários já agendados
    return [h for h in horarios if h not in horarios_agendados]


# --- 📌 Cadastro de Agendamento ---
st.write("### 📌 Novo Agendamento")
with st.form("agendamento_form"):
    cliente = st.selectbox("Selecione o Cliente", options=list(clientes_dict.keys()), index=None,
                           placeholder="Selecione...")
    funcionario = st.selectbox("Selecione o Funcionário", options=list(funcionarios_dict.keys()), index=None,
                               placeholder="Selecione...")
    servico = st.selectbox("Selecione o Serviço", options=list(servicos_dict.keys()), index=None,
                           placeholder="Selecione...")

    # Data obrigatória
    data = st.date_input("Data do Atendimento", value=None, min_value=datetime.today())
    hora = None

    if data:
        horarios_disponiveis = obter_horarios_disponiveis(data)
        if horarios_disponiveis:
            hora = st.selectbox("Hora do Atendimento", options=horarios_disponiveis, index=None,
                                placeholder="Selecione um horário disponível")
        else:
            st.warning("⚠️ Todos os horários para esta data estão ocupados!")

    submitted = st.form_submit_button("Agendar")

    if submitted:
        if cliente and funcionario and servico and data and hora:
            cursor.execute(
                "INSERT INTO agendamentos (cliente_id, funcionario_id, servico_id, data, hora) VALUES (?, ?, ?, ?, ?)",
                (clientes_dict[cliente], funcionarios_dict[funcionario], servicos_dict[servico], str(data), hora)
            )
            conn.commit()
            st.success("✅ Agendamento realizado com sucesso!")
        else:
            st.warning("⚠️ Preencha todos os campos corretamente, incluindo Data e Hora.")

# --- 📋 Listar Agendamentos ---
st.write("### 📋 Lista de Agendamentos")

agendamentos = cursor.execute("""
    SELECT 
    ag.id AS ID,
    c.nome AS Cliente,
    f.nome AS Funcionario,
    s.nome AS Servico,
    ag.data AS Data,
    ag.hora AS Horario
    FROM agendamentos ag
    JOIN clientes c ON ag.cliente_id = c.id
    JOIN funcionarios f ON ag.funcionario_id = f.id
    JOIN servicos s ON ag.servico_id = s.id
    ORDER BY ag.data, ag.hora;
""").fetchall()

# Criar um DataFrame para exibir na tabela
if agendamentos:
    df_agendamentos = pd.DataFrame(agendamentos, columns=["ID", "Cliente", "Funcionário", "Serviço", "Data", "Hora"])

    # Estilizar a tabela
    st.table(df_agendamentos.style.set_table_styles([
        {'selector': 'thead th',
         'props': [('background-color', '#4CAF50'), ('color', 'white'), ('text-align', 'center')]},
        {'selector': 'tbody tr:nth-child(even)', 'props': [('background-color', '#f2f2f2')]},
        {'selector': 'tbody tr:hover', 'props': [('background-color', '#ddd')]},
        {'selector': 'td', 'props': [('text-align', 'center'), ('padding', '10px')]},
    ]))
else:
    st.info("ℹ️ Nenhum agendamento encontrado.")

# Fechar Conexão
conn.close()
