import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from utils import load_static_files

# Configuração da Página
st.set_page_config(
    page_title="Gerenciador de Barbearia",
    page_icon="💈",
    layout="wide"
)

# Carregar os arquivos CSS e JS
load_static_files()


# Sidebar
st.sidebar.title("💈 Menu Principal")
page = st.sidebar.radio(
    "Navegue pelo sistema:",
    ["Dashboard", "Clientes", "Agenda", "Serviços", "Funcionários", "Faturamento"]
)

# Conteúdo Principal
st.markdown("""
    <div class="container">
        <h1 class="text-center">💈 Gerenciador de Barbearia Web</h1>
    </div>
""", unsafe_allow_html=True)

# Conexão com o banco
conn = sqlite3.connect('barbearia.db')
cursor = conn.cursor()

# Dashboard
if page == "Dashboard":
    st.markdown("### 📊 Dashboard Principal")
    st.write("Visão geral das operações diárias com métricas avançadas para análise gerencial.")

    # Carregar Dados Gerais
    df_agendamentos = pd.read_sql_query("""
        SELECT 
            ag.data AS Data,
            ag.hora AS Hora,
            f.nome AS Funcionario,
            s.nome AS Servico,
            s.preco AS Preco
        FROM agendamentos ag
        JOIN funcionarios f ON ag.funcionario_id = f.id
        JOIN servicos s ON ag.servico_id = s.id
    """, conn)

    df_agendamentos['Data'] = pd.to_datetime(df_agendamentos['Data'])
    df_agendamentos['Dia'] = df_agendamentos['Data'].dt.day_name()
    df_agendamentos['Semana'] = df_agendamentos['Data'].dt.strftime('%U')
    df_agendamentos['Mes'] = df_agendamentos['Data'].dt.strftime('%B')

    # 🎯 Filtros
    st.sidebar.markdown("### 🎛️ Filtros")
    selected_funcionario = st.sidebar.selectbox("Selecione o Funcionário", ["Todos Funcionários"] + list(df_agendamentos['Funcionario'].unique()))
    selected_mes = st.sidebar.selectbox("Selecione o Mês", ["Todos Meses"] + list(df_agendamentos['Mes'].unique()))

    df_filtered = df_agendamentos.copy()
    if selected_funcionario != "Todos Funcionários":
        df_filtered = df_filtered[df_filtered['Funcionario'] == selected_funcionario]
    if selected_mes != "Todos Meses":
        df_filtered = df_filtered[df_filtered['Mes'] == selected_mes]

    # 📊 MÉTRICAS
    st.markdown("## 📈 Métricas Principais")
    col1, col2, col3 = st.columns(3)

    # Atendimentos por Dia, Semana e Mês
    total_dia = df_filtered[df_filtered['Data'] == pd.Timestamp.now().date()].shape[0]
    total_semana = df_filtered[df_filtered['Semana'] == pd.Timestamp.now().strftime('%U')].shape[0]
    total_mes = df_filtered[df_filtered['Mes'] == pd.Timestamp.now().strftime('%B')].shape[0]

    with col1:
        st.metric(label="📅 Atendimentos Hoje", value=total_dia)
    with col2:
        st.metric(label="📆 Atendimentos na Semana", value=total_semana)
    with col3:
        st.metric(label="📊 Atendimentos no Mês", value=total_mes)

    # Faturamento Total
    faturamento_total = df_filtered['Preco'].sum()
    st.write("### 💵 Faturamento Total")
    st.metric(label="Faturamento Total (R$)", value=f"R$ {faturamento_total:,.2f}")

    # 🔍 GRÁFICOS DETALHADOS
    st.markdown("## 📊 Análises Gráficas")

    # 1️⃣ Atendimento por Dia
    st.write("### 📅 Atendimentos por Dia")
    atendimentos_dia = df_filtered.groupby('Data').size().reset_index(name='Atendimentos')
    fig_dia = px.bar(atendimentos_dia, x='Data', y='Atendimentos', title="Atendimentos por Dia", color='Atendimentos')
    st.plotly_chart(fig_dia, use_container_width=True)

    # 2️⃣ Tipos de Serviço Mais Realizados
    st.write("### 💈 Tipos de Serviço Mais Realizados")
    servicos_populares = df_filtered['Servico'].value_counts().reset_index()
    servicos_populares.columns = ['Servico', 'Quantidade']
    fig_servico = px.pie(servicos_populares, names='Servico', values='Quantidade', title="Distribuição de Tipos de Serviço")
    st.plotly_chart(fig_servico, use_container_width=True)

    # 3️⃣ Faturamento por Funcionário
    st.write("### 👤 Faturamento por Funcionário")
    faturamento_func = df_filtered.groupby('Funcionario')['Preco'].sum().reset_index()
    fig_faturamento = px.bar(faturamento_func, x='Funcionario', y='Preco', title="Faturamento por Funcionário", color='Preco')
    st.plotly_chart(fig_faturamento, use_container_width=True)

    conn.close()

# Clientes
elif page == "Clientes":
    st.markdown("### 👤 Gestão de Clientes")

    # 🔄 **CREATE: Adicionar Cliente**
    with st.form("form_cliente"):
        nome = st.text_input("Nome do Cliente")
        telefone = st.text_input("Telefone")
        email = st.text_input("E-mail")
        submitted = st.form_submit_button("Adicionar Cliente")

        if submitted:
            cursor.execute("INSERT INTO clientes (nome, telefone, email) VALUES (?, ?, ?)", (nome, telefone, email))
            conn.commit()
            st.success("Cliente adicionado com sucesso!")

    # 📊 **READ: Listar Clientes**
    st.write("### 📋 Lista de Clientes")
    df_clientes = pd.read_sql_query("SELECT * FROM clientes", conn)
    st.dataframe(df_clientes)

    # 🛠️ **UPDATE: Editar Cliente**
    cliente_id = st.selectbox("Selecione o Cliente para Editar", df_clientes['id'])
    novo_nome = st.text_input("Novo Nome")
    novo_telefone = st.text_input("Novo Telefone")
    novo_email = st.text_input("Novo E-mail")
    if st.button("Atualizar Cliente"):
        cursor.execute(
            "UPDATE clientes SET nome=?, telefone=?, email=? WHERE id=?",
            (novo_nome, novo_telefone, novo_email, cliente_id)
        )
        conn.commit()
        st.success("Cliente atualizado com sucesso!")

    # 🗑️ **DELETE: Excluir Cliente**
    cliente_id_del = st.selectbox("Selecione o Cliente para Excluir", df_clientes['id'])
    if st.button("Excluir Cliente"):
        cursor.execute("DELETE FROM clientes WHERE id=?", (cliente_id_del,))
        conn.commit()
        st.warning("Cliente excluído com sucesso!")

if page == "Agenda":
    st.markdown("### 📅 Agenda de Atendimentos")

    # 🔄 **CREATE: Inserir Agendamento**
    with st.form("form_agenda"):
        cliente_id = st.selectbox("Cliente", pd.read_sql_query("SELECT id, nome FROM clientes", conn)['id'])
        funcionario_id = st.selectbox("Funcionário", pd.read_sql_query("SELECT id, nome FROM funcionarios", conn)['id'])
        servico_id = st.selectbox("Serviço", pd.read_sql_query("SELECT id, nome FROM servicos", conn)['id'])
        data = st.date_input("Data do Atendimento")
        hora = st.time_input("Hora do Atendimento")
        submitted = st.form_submit_button("Agendar")

        if submitted:
            cursor.execute(
                "INSERT INTO agendamentos (cliente_id, funcionario_id, servico_id, data, hora) VALUES (?, ?, ?, ?, ?)",
                (cliente_id, funcionario_id, servico_id, str(data), str(hora))
            )
            conn.commit()
            st.success("Agendamento realizado com sucesso!")

    # 📊 **READ: Listar Agendamentos**
    st.write("### 📋 Lista de Agendamentos")
    df_agenda = pd.read_sql_query("""
        SELECT ag.id, c.nome AS Cliente, f.nome AS Funcionario, s.nome AS Serviço, ag.data, ag.hora 
        FROM agendamentos ag
        JOIN clientes c ON ag.cliente_id = c.id
        JOIN funcionarios f ON ag.cliente_id = f.id
        JOIN servicos s ON ag.cliente_id = s.id
    """, conn)
    st.dataframe(df_agenda)

    # 🛠️ **UPDATE: Editar Agendamento**
    agendamento_id = st.selectbox("Selecione o Agendamento para Editar", df_agenda['id'])
    nova_data = st.date_input("Nova Data")
    nova_hora = st.time_input("Nova Hora")
    if st.button("Atualizar Agendamento"):
        cursor.execute(
            "UPDATE agendamentos SET data=?, hora=? WHERE id=?",
            (str(nova_data), str(nova_hora), agendamento_id)
        )
        conn.commit()
        st.success("Agendamento atualizado com sucesso!")

    # 🗑️ **DELETE: Excluir Agendamento**
    agendamento_id_del = st.selectbox("Selecione o Agendamento para Excluir", df_agenda['id'])
    if st.button("Excluir Agendamento"):
        cursor.execute("DELETE FROM agendamentos WHERE id=?", (agendamento_id_del,))
        conn.commit()
        st.warning("Agendamento excluído com sucesso!")

# Serviços
elif page == "Serviços":
    st.markdown("### ✂️ Gestão de Serviços")

    # 🔄 **CREATE: Adicionar Serviço**
    with st.form("form_servico"):
        descricao = st.text_input("Descrição do Serviço")
        preco = st.number_input("Preço do Serviço (R$)", min_value=0.0, step=0.1)
        submitted = st.form_submit_button("Adicionar Serviço")

        if submitted:
            cursor.execute("INSERT INTO servicos (nome, preco) VALUES (?, ?)", (descricao, preco))
            conn.commit()
            st.success("Serviço adicionado com sucesso!")

    # 📊 **READ: Listar Serviços**
    st.write("### 📋 Lista de Serviços")
    df_servicos = pd.read_sql_query("SELECT * FROM servicos", conn)
    st.dataframe(df_servicos)

    # 🛠️ **UPDATE: Editar Serviço**
    servico_id = st.selectbox("Selecione o Serviço para Editar", df_servicos['id'])
    nova_descricao = st.text_input("Nova Descrição")
    novo_preco = st.number_input("Novo Preço (R$)", min_value=0.0, step=0.1)
    if st.button("Atualizar Serviço"):
        cursor.execute(
            "UPDATE servicos SET nome=?, preco=? WHERE id=?",
            (nova_descricao, novo_preco, servico_id)
        )
        conn.commit()
        st.success("Serviço atualizado com sucesso!")

    # 🗑️ **DELETE: Excluir Serviço**
    servico_id_del = st.selectbox("Selecione o Serviço para Excluir", df_servicos['id'])
    if st.button("Excluir Serviço"):
        cursor.execute("DELETE FROM servicos WHERE id=?", (servico_id_del,))
        conn.commit()
        st.warning("Serviço excluído com sucesso!")

# Funcionários
elif page == "Funcionários":
    st.markdown("### 🧑‍🔧 Gestão de Funcionários")

    # 🔄 **CREATE: Adicionar Funcionário**
    with st.form("form_funcionario"):
        nome = st.text_input("Nome do Funcionário")
        cargo = st.text_input("Cargo")
        submitted = st.form_submit_button("Adicionar Funcionário")

        if submitted:
            cursor.execute("INSERT INTO funcionarios (nome, especialidade) VALUES (?, ?)", (nome, cargo))
            conn.commit()
            st.success("Funcionário adicionado com sucesso!")

    # 📊 **READ: Listar Funcionários**
    st.write("### 📋 Lista de Funcionários")
    df_funcionarios = pd.read_sql_query("SELECT * FROM funcionarios", conn)
    st.dataframe(df_funcionarios)

    # 🛠️ **UPDATE: Editar Funcionário**
    funcionario_id = st.selectbox("Selecione o Funcionário para Editar", df_funcionarios['id'])
    novo_nome = st.text_input("Novo Nome")
    novo_cargo = st.text_input("Novo Cargo")
    if st.button("Atualizar Funcionário"):
        cursor.execute(
            "UPDATE funcionarios SET nome=?, especialidade=? WHERE id=?",
            (novo_nome, novo_cargo, funcionario_id)
        )
        conn.commit()
        st.success("Funcionário atualizado com sucesso!")

    # 🗑️ **DELETE: Excluir Funcionário**
    funcionario_id_del = st.selectbox("Selecione o Funcionário para Excluir", df_funcionarios['id'])
    if st.button("Excluir Funcionário"):
        cursor.execute("DELETE FROM funcionarios WHERE id=?", (funcionario_id_del,))
        conn.commit()
        st.warning("Funcionário excluído com sucesso!")

# Faturamento
elif page == "Faturamento":
    st.markdown("### 💵 Gestão de Faturamento Loja")
    st.write("Gerencie o Faturamento dos Funcionários e Serviços.")

    # 🔄 **Cálculos de Faturamento**

    # Faturamento Total da Loja
    df_faturamento_total = pd.read_sql_query("""
           SELECT SUM(servicos.preco) as total 
           FROM agendamentos 
           JOIN servicos ON agendamentos.servico_id = servicos.id
       """, conn)
    faturamento_total = df_faturamento_total['total'][0]

    # Criando colunas para mostrar métricas lado a lado
    col1, col2 = st.columns(2)

    with col1:
        st.metric(label="Faturamento Total da Loja (R$)", value=f"R$ {faturamento_total:,.2f}")

    # Faturamento por Funcionário com Métricas
    df_faturamento_funcionario = pd.read_sql_query("""
           SELECT f.id AS FuncionarioID, f.nome AS Funcionario, 
                  SUM(s.preco) as Faturamento, COUNT(a.id) AS Atendimentos
           FROM agendamentos a
           JOIN servicos s ON a.servico_id = s.id
           JOIN funcionarios f ON a.funcionario_id = f.id
           GROUP BY f.id
           ORDER BY Faturamento DESC
       """, conn)

    # **Filtro de Funcionário** (para selecionar o funcionário específico ou todos)
    filtro_funcionario = st.radio("Filtrar por Funcionário ou Loja", ["Funcionário", "Loja"])

    if filtro_funcionario == "Funcionário":
        funcionarios_list = df_faturamento_funcionario['Funcionario'].tolist()
        selected_funcionario = st.selectbox("Selecione o Funcionário", funcionarios_list)
        # Filtrando os dados para o funcionário selecionado
        df_funcionario_selecionado = df_faturamento_funcionario[
            df_faturamento_funcionario['Funcionario'] == selected_funcionario]
        st.write(f"### 🧑‍🔧 {selected_funcionario} - Desempenho")
    else:
        # Se for para mostrar todos os funcionários, mostramos os dados gerais
        df_funcionario_selecionado = df_faturamento_funcionario
        st.write("### 🧑‍🔧 Desempenho de Todos os Funcionários")

    # Faturamento e métricas do Funcionário Selecionado ou Todos
    faturamento_funcionario = df_funcionario_selecionado['Faturamento'].sum()
    atendimentos_funcionario = df_funcionario_selecionado['Atendimentos'].sum()

    # 📊 **Métricas de Desempenho**
    # % Faturamento do Funcionário em relação ao Faturamento Total
    percentual_faturamento = (faturamento_funcionario / faturamento_total) * 100 if faturamento_total > 0 else 0
    # Faturamento Médio por Atendimento
    faturamento_medio = faturamento_funcionario / atendimentos_funcionario if atendimentos_funcionario > 0 else 0

    # Exibindo métricas lado a lado para **Funcionário ou Loja**
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="Faturamento do Funcionário (R$)", value=f"R$ {faturamento_funcionario:,.2f}")

    with col2:
        st.metric(label="Atendimentos Realizados", value=f"{atendimentos_funcionario:.0f}")

    with col3:
        st.metric(label="% do Faturamento da Loja", value=f"{percentual_faturamento:.2f}%")

    # 📈 **Faturamento Total por Funcionário**
    st.write("### 📊 Faturamento por Funcionário")
    fig_faturamento_funcionario = px.bar(df_faturamento_funcionario,
                                         x='Funcionario',
                                         y='Faturamento',
                                         title="Faturamento por Funcionário",
                                         color='Funcionario')
    st.plotly_chart(fig_faturamento_funcionario)

    # **Tabela de Faturamento por Funcionário**
    st.write("### 📋 Detalhamento de Faturamento")
    st.dataframe(df_faturamento_funcionario)

    # **Outras Métricas**
    st.write("### 🔍 Outras Métricas de Desempenho dos Funcionários")

    # Faturamento Médio por Funcionário
    faturamento_medio_funcionario = df_faturamento_funcionario['Faturamento'].mean()
    # Atendimentos Médios por Funcionário
    atendimentos_medios_funcionario = df_faturamento_funcionario['Atendimentos'].mean()

    # Exibindo as métricas de outras formas lado a lado
    col1, col2 = st.columns(2)

    with col1:
        st.metric(label="Faturamento Médio por Funcionário (R$)", value=f"R$ {faturamento_medio_funcionario:,.2f}")

    with col2:
        st.metric(label="Atendimentos Médios por Funcionário", value=f"{atendimentos_medios_funcionario:.0f}")

    # Faturamento por Mês
    df_faturamento_mes = pd.read_sql_query("""
        SELECT strftime('%Y-%m', a.data) as mes, SUM(s.preco) as faturamento 
        FROM agendamentos a
        JOIN servicos s ON a.servico_id = s.id
        GROUP BY mes
        ORDER BY mes DESC
    """, conn)

    st.write("### 📅 Faturamento por Mês")
    st.dataframe(df_faturamento_mes)

    # Gráfico de Faturamento Mensal
    st.write("### 📊 Gráfico de Faturamento Mensal")
    fig_faturamento = px.bar(df_faturamento_mes, x='mes', y='faturamento', title="Faturamento por Mês")
    st.plotly_chart(fig_faturamento)

    # Faturamento Anual
    df_faturamento_ano = pd.read_sql_query("""
        SELECT strftime('%Y', a.data) as ano, SUM(s.preco) as faturamento 
        FROM agendamentos a
        JOIN servicos s ON a.servico_id = s.id
        GROUP BY ano
        ORDER BY ano DESC
    """, conn)

    st.write("### 🗓️ Faturamento Anual")
    st.dataframe(df_faturamento_ano)
