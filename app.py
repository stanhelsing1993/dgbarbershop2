import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from utils import load_static_files
from io import BytesIO


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
if 'usuario_logado' in st.session_state:
    pages = ["Dashboard", "Clientes", "Serviços", "Funcionários", "Faturamento"]
else:
    pages = ["Login", "Agenda"]  # Somente a página de Login estará disponível se o usuário não estiver logado

page = st.sidebar.radio("Navegue pelo sistema:", pages)

# Conteúdo Principal
st.markdown("""
    <div class="container">
        <h1 class="text-center">💈 Gerenciador de Barbearia Web</h1>
    </div>
""", unsafe_allow_html=True)

# Conexão com o banco
conn = sqlite3.connect('barbearia.db')
cursor = conn.cursor()


# Função para verificar o login
def verificar_login(usuario, senha):
    cursor.execute("SELECT * FROM usuarios WHERE nome_usuario = ? AND senha = ?", (usuario, senha))
    usuario_encontrado = cursor.fetchone()
    return usuario_encontrado is not None


# Página de login
def pagina_login():
    st.markdown("### 📝 Login")

    # Formulário de login
    nome_usuario = st.text_input("Nome de usuário")
    senha = st.text_input("Senha", type='password')

    if st.button("Entrar"):
        if verificar_login(nome_usuario, senha):
            st.success("Login realizado com sucesso!")
            # Salvar usuário logado em uma sessão
            st.session_state.usuario_logado = nome_usuario
            st.rerun()  # Recarregar a página para mostrar o conteúdo
        else:
            st.error("Nome de usuário ou senha incorretos.")


# Função para verificar se o usuário está logado
def verificar_usuario_logado():
    if 'usuario_logado' not in st.session_state:
        return False
    return True

def pagina_dashboard():
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
    selected_funcionario = st.sidebar.selectbox("Selecione o Funcionário",
                                                ["Todos Funcionários"] + list(df_agendamentos['Funcionario'].unique()))
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
    fig_servico = px.pie(servicos_populares, names='Servico', values='Quantidade',
                         title="Distribuição de Tipos de Serviço")
    st.plotly_chart(fig_servico, use_container_width=True)

    # 3️⃣ Faturamento por Funcionário
    st.write("### 👤 Faturamento por Funcionário")
    faturamento_func = df_filtered.groupby('Funcionario')['Preco'].sum().reset_index()
    fig_faturamento = px.bar(faturamento_func, x='Funcionario', y='Preco', title="Faturamento por Funcionário",
                             color='Preco')
    st.plotly_chart(fig_faturamento, use_container_width=True)

    # **Filtros**
    st.write("### Filtros de Data e Cliente")

    # Filtro de Mês
    start_date = st.date_input("Data Inicial", pd.to_datetime("2025-01-01"))
    end_date = st.date_input("Data Final", pd.to_datetime("2025-01-31"))

    # Filtro de Cliente
    clientes_query = "SELECT DISTINCT nome FROM clientes ORDER BY nome"
    clientes = pd.read_sql_query(clientes_query, conn)
    clientes_lista = ["Todos"] + clientes["nome"].tolist()

    cliente_filter = st.selectbox("Cliente", clientes_lista)

    # **Consulta ao banco de dados**
    query = f"""
    SELECT 
        strftime('%m-%Y', ag.data) AS Mes,
        c.nome AS Cliente,
        COUNT(ag.id) AS Total_Atendimentos,
        SUM(s.preco) AS Total_Faturamento
    FROM agendamentos ag
    JOIN funcionarios f ON ag.funcionario_id = f.id
    JOIN servicos s ON ag.servico_id = s.id
    JOIN clientes c ON ag.cliente_id = c.id
    WHERE ag.data BETWEEN '{start_date}' AND '{end_date}'
    """
    if cliente_filter != "Todos":
        query += f" AND c.nome = '{cliente_filter}'"

    query += """
    GROUP BY Mes, c.nome
    ORDER BY Mes DESC, Total_Atendimentos DESC;
    """

    # **Obter dados do banco de dados**
    df = pd.read_sql_query(query, conn)

    # **Exibir resultados**
    if not df.empty:
        st.write("### 📊 Resultados de Atendimentos e Faturamento")
        # Aqui usamos st.dataframe com ajuste automático de largura de colunas
        st.dataframe(df.style.set_table_styles([
            {'selector': 'thead th',
             'props': [('background-color', '#4CAF50'), ('color', 'white'), ('text-align', 'center')]},
            {'selector': 'tbody tr:nth-child(even)', 'props': [('background-color', '#f2f2f2')]},
            {'selector': 'tbody tr:hover', 'props': [('background-color', '#ddd')]},
            {'selector': 'td', 'props': [('text-align', 'center'), ('padding', '10px')]},
        ], axis=None), use_container_width=True)

        # **Gráfico de Atendimentos e Faturamento com Plotly**
        # Gráfico de barras para Total de Atendimentos
        fig = px.bar(df,
                     x=df['Mes'] + " " + df['Cliente'],
                     y='Total_Atendimentos',
                     labels={'Total_Atendimentos': 'Total de Atendimentos'},
                     title="Atendimentos e Faturamento por Cliente",
                     color='Cliente')

        # Adicionando Faturamento como uma linha
        fig.add_scatter(x=df['Mes'] + " " + df['Cliente'],
                        y=df['Total_Faturamento'],
                        mode='lines+markers',
                        name="Total Faturamento",
                        line=dict(color='green', width=3))

        # Atualizando o layout para eixos duplos
        fig.update_layout(
            xaxis_title="Mês / Cliente",
            yaxis_title="Atendimentos",
            yaxis2=dict(title="Faturamento (R$)", overlaying="y", side="right"),
            legend_title="Cliente",
            xaxis_tickangle=45
        )

        # Exibir gráfico
        st.plotly_chart(fig)

    else:
        st.write("Nenhum registro encontrado para o filtro selecionado.")

    conn.close()

def pagina_clientes():
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

    # Remover a coluna de índice e ajustar a exibição
    df_clientes = df_clientes.drop(columns=['index'], errors='ignore')

    # Estilizar a tabela
    st.table(df_clientes.style.set_table_styles([
        {'selector': 'thead th',
         'props': [('background-color', '#4CAF50'), ('color', 'white'), ('text-align', 'center')]},
        {'selector': 'tbody tr:nth-child(even)', 'props': [('background-color', '#f2f2f2')]},
        {'selector': 'tbody tr:hover', 'props': [('background-color', '#ddd')]},
        {'selector': 'td', 'props': [('text-align', 'center'), ('padding', '10px')]},
    ]))

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

def pagina_agenda():
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

    # Estilizar a tabela
    st.table(df_agenda.style.set_table_styles([
        {'selector': 'thead th',
         'props': [('background-color', '#4CAF50'), ('color', 'white'), ('text-align', 'center')]},
        {'selector': 'tbody tr:nth-child(even)', 'props': [('background-color', '#f2f2f2')]},
        {'selector': 'tbody tr:hover', 'props': [('background-color', '#ddd')]},
        {'selector': 'td', 'props': [('text-align', 'center'), ('padding', '10px')]},
    ]))

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

def pagina_servico():
    st.markdown("### ✂️ Gestão de Serviços")

    # 🔄 **CREATE: Adicionar Serviço**
    with st.form("form_servico"):
        descricao = st.text_input("Descrição do Serviço")
        preco = st.number_input("Preço do Serviço (R$)", min_value=0.0, step=0.1)
        duracao = st.number_input("Duração (min)", min_value=1, step=1)  # Adicionei o campo de duração
        submitted = st.form_submit_button("Adicionar Serviço")

        if submitted:
            cursor.execute("INSERT INTO servicos (nome, preco, duracao) VALUES (?, ?, ?)", (descricao, preco, duracao))
            conn.commit()
            st.success("Serviço adicionado com sucesso!")

    # 📊 **READ: Listar Serviços**
    st.write("### 📋 Lista de Serviços")
    df_servicos = pd.read_sql_query("SELECT * FROM servicos", conn)

    # Ajustar a formatação sem criar novas colunas
    df_servicos['Preço (R$)'] = df_servicos['preco'].apply(lambda x: f"R$ {x:.2f}")

    # Verificando se a duração é válida e aplicando a formatação
    df_servicos['Duração (min)'] = df_servicos['duracao'].apply(lambda x: f"{int(x)} min" if pd.notnull(x) else "N/A")

    # Selecionando apenas as colunas que queremos exibir
    df_servicos_display = df_servicos[['id', 'nome', 'Preço (R$)', 'Duração (min)']]

    # Estilizar a tabela
    st.table(df_servicos_display.style.set_table_styles([
        {'selector': 'thead th',
         'props': [('background-color', '#4CAF50'), ('color', 'white'), ('text-align', 'center')]},
        {'selector': 'tbody tr:nth-child(even)', 'props': [('background-color', '#f2f2f2')]},
        {'selector': 'tbody tr:hover', 'props': [('background-color', '#ddd')]},
        {'selector': 'td', 'props': [('text-align', 'center'), ('padding', '10px')]},
    ]))

    # 🛠️ **UPDATE: Editar Serviço**
    servico_id = st.selectbox("Selecione o Serviço para Editar", df_servicos['id'])
    nova_descricao = st.text_input("Nova Descrição")
    novo_preco = st.number_input("Novo Preço (R$)", min_value=0.0, step=0.1)
    nova_duracao = st.number_input("Nova Duração (min)", min_value=1, step=1)  # Campo para nova duração
    if st.button("Atualizar Serviço"):
        cursor.execute(
            "UPDATE servicos SET nome=?, preco=?, duracao=? WHERE id=?",
            (nova_descricao, novo_preco, nova_duracao, servico_id)
        )
        conn.commit()
        st.success("Serviço atualizado com sucesso!")

    # 🗑️ **DELETE: Excluir Serviço**
    servico_id_del = st.selectbox("Selecione o Serviço para Excluir", df_servicos['id'])
    if st.button("Excluir Serviço"):
        cursor.execute("DELETE FROM servicos WHERE id=?", (servico_id_del,))
        conn.commit()
        st.warning("Serviço excluído com sucesso!")

def pagina_funcionarios():
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
    # Estilizar a tabela
    st.table(df_funcionarios.style.set_table_styles([
        {'selector': 'thead th',
         'props': [('background-color', '#4CAF50'), ('color', 'white'), ('text-align', 'center')]},
        {'selector': 'tbody tr:nth-child(even)', 'props': [('background-color', '#f2f2f2')]},
        {'selector': 'tbody tr:hover', 'props': [('background-color', '#ddd')]},
        {'selector': 'td', 'props': [('text-align', 'center'), ('padding', '10px')]},
    ]))

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

def pagina_faturamento():
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

    # Garantir que o valor está no formato correto (remover valores desnecessários)
    df_faturamento_funcionario['Faturamento'] = df_faturamento_funcionario['Faturamento'].astype(float).round(2)

    # Adicionar uma coluna formatada para exibição
    df_faturamento_funcionario['Faturamento_Formatado'] = df_faturamento_funcionario['Faturamento'].apply(
        lambda x: f'R$ {x:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    )

    # Estilizar a tabela
    st.table(df_faturamento_funcionario[
        ['FuncionarioID', 'Funcionario', 'Faturamento_Formatado', 'Atendimentos']].style.set_table_styles([
        {'selector': 'thead th',
         'props': [('background-color', '#4CAF50'), ('color', 'white'), ('text-align', 'center')]},
        {'selector': 'tbody tr:nth-child(even)', 'props': [('background-color', '#f2f2f2')]},
        {'selector': 'tbody tr:hover', 'props': [('background-color', '#ddd')]},
        {'selector': 'td', 'props': [('text-align', 'center'), ('padding', '10px')]},
    ]))

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
            SELECT 
            strftime('%m-%Y', a.data) AS mes,
            'R$ ' || REPLACE(printf('%.2f', SUM(s.preco)), '.', ',') AS faturamento
        FROM agendamentos a
        JOIN servicos s ON a.servico_id = s.id
        GROUP BY mes
        ORDER BY mes DESC;
        """, conn)

    st.write("### 📅 Faturamento por Mês")

    st.table(df_faturamento_mes.style.set_table_styles([
        {'selector': 'thead th',
         'props': [('background-color', '#4CAF50'), ('color', 'white'), ('text-align', 'center')]},
        {'selector': 'tbody tr:nth-child(even)', 'props': [('background-color', '#f2f2f2')]},
        {'selector': 'tbody tr:hover', 'props': [('background-color', '#ddd')]},
        {'selector': 'td', 'props': [('text-align', 'center'), ('padding', '10px')]},
    ]))

    # Gráfico de Faturamento Mensal
    st.write("### 📊 Gráfico de Faturamento Mensal")
    # Converter para datetime e extrair apenas o mês/ano
    df_faturamento_mes['mes'] = pd.to_datetime(df_faturamento_mes['mes']).dt.strftime('%m-%Y')  # Formato: Ano-Mês

    # Ordenar os dados por mês
    df_faturamento_mes = df_faturamento_mes.sort_values(by='mes')

    # Gráfico de Faturamento Mensal

    fig_faturamento = px.bar(
        df_faturamento_mes,
        x='mes',
        y='faturamento',
        title="Faturamento por Mês",
        labels={'mes': 'Mês', 'faturamento': 'Faturamento (R$)'},
        text='faturamento'
    )

    # Melhorar o layout do gráfico
    fig_faturamento.update_traces(marker_color='skyblue', textposition='outside')
    fig_faturamento.update_layout(
        xaxis_title='Mês',
        yaxis_title='Faturamento (R$)',
        xaxis=dict(tickmode='linear'),
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(showgrid=True, gridcolor='lightgrey')
    )

    st.plotly_chart(fig_faturamento)

    # Faturamento Anual
    df_faturamento_ano = pd.read_sql_query("""
            SELECT 
            strftime('%Y', a.data) AS ano,
            'R$ ' || REPLACE(printf('%.2f', SUM(s.preco)), '.', ',') AS faturamento
        FROM agendamentos a
        JOIN servicos s ON a.servico_id = s.id
        GROUP BY ano
        ORDER BY ano DESC;
        """, conn)

    st.write("### 🗓️ Faturamento Anual")

    st.table(df_faturamento_ano.style.set_table_styles([
        {'selector': 'thead th',
         'props': [('background-color', '#4CAF50'), ('color', 'white'), ('text-align', 'center')]},
        {'selector': 'tbody tr:nth-child(even)', 'props': [('background-color', '#f2f2f2')]},
        {'selector': 'tbody tr:hover', 'props': [('background-color', '#ddd')]},
        {'selector': 'td', 'props': [('text-align', 'center'), ('padding', '10px')]},
    ]))

    st.write("### 💳 Resultado do Cálculo de Repasse")

    # **Filtros**


    col1, col2, col3 = st.columns(3)
    with col1:
        start_date = st.date_input("Data Inicial")
    with col2:
        end_date = st.date_input("Data Final")
    with col3:
        # Consulta para buscar os funcionários do banco de dados
        funcionarios_query = "SELECT DISTINCT nome FROM funcionarios ORDER BY nome"
        funcionarios = pd.read_sql_query(funcionarios_query, conn)

        # Adicionar a opção "Todos" ao início da lista de funcionários
        funcionarios_lista = ["Todos"] + funcionarios["nome"].tolist()

        # Filtro de Funcionário
        funcionario_filter = st.selectbox("Funcionário", funcionarios_lista)

    # **Consulta ao banco de dados**
    query = f"""
       SELECT 
       f.id AS funcionario_id,
       f.nome AS funcionario,
       s.nome AS servico,
       s.preco AS preco_servico,
       strftime('%d-%m-%Y', a.data) AS data
FROM agendamentos a
       JOIN servicos s ON a.servico_id = s.id
       JOIN funcionarios f ON a.funcionario_id = f.id
       WHERE a.data BETWEEN '{start_date}' AND '{end_date}'
       """
    if funcionario_filter != "Todos":
        query += f" AND f.nome = '{funcionario_filter}'"

    df = pd.read_sql_query(query, conn)

    # Adicionar cálculo do repasse (50%)
    df["Repasse_Funcionario"] = df["preco_servico"] * 0.50
    df["Repasse_Loja"] = df["preco_servico"] * 0.50

    # Exibir tabela de resultados

    # Cálculo dos totais
    valor_total = df["preco_servico"].sum()
    valor_loja = df["Repasse_Loja"].sum()
    valor_funcionario = df["Repasse_Funcionario"].sum()

    # Exibir métricas em colunas

    col1, col2, col3 = st.columns(3)
    col1.metric("Valor Total", f"R$ {valor_total:,.2f}")
    col2.metric("Valor Pago para a Loja", f"R$ {valor_loja:,.2f}")
    col3.metric("Valor Pago aos Funcionários", f"R$ {valor_funcionario:,.2f}")

    if not df.empty:
        # Arredondar os valores numéricos para duas casas decimais
        df["preco_servico"] = df["preco_servico"].round(2)
        df["Repasse_Funcionario"] = df["Repasse_Funcionario"].round(2)
        df["Repasse_Loja"] = df["Repasse_Loja"].round(2)

        # Estilizar a tabela usando pandas
        styled_df = df.style.format(
            {
                "preco_servico": "R$ {:,.2f}",
                "Repasse_Funcionario": "R$ {:,.2f}",
                "Repasse_Loja": "R$ {:,.2f}",
            }
        ).set_table_styles([
            {'selector': 'thead th',
             'props': [('background-color', '#4CAF50'), ('color', 'white'), ('text-align', 'center')]},
            {'selector': 'tbody tr:nth-child(even)', 'props': [('background-color', '#f2f2f2')]},
            {'selector': 'tbody tr:hover', 'props': [('background-color', '#ddd')]},
            {'selector': 'td', 'props': [('text-align', 'center'), ('padding', '10px')]},
        ])


        # Renderizar a tabela estilizada como HTML
        tabela_html = styled_df.to_html(escape=False)



        # Exibir a tabela estilizada
        st.write("### 💳 Resultado do Cálculo de Repasse")
        st.write(tabela_html, unsafe_allow_html=True)
    else:
        st.write("Nenhum registro encontrado para o filtro selecionado.")




    # **Baixar Relatório em Excel**
    def download_excel(dataframe):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            dataframe.to_excel(writer, index=False, sheet_name="Repasse")
        processed_data = output.getvalue()
        return processed_data


    if not df.empty:
        excel_data = download_excel(df)
        st.download_button(
            label="📥 Baixar Relatório em Excel",
            data=excel_data,
            file_name="relatorio_repasse.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# Login
if page == "Login":
    if verificar_usuario_logado():
        st.write(f"Olá, {st.session_state.usuario_logado}!")
        st.write("Você já está logado. Pode acessar as outras páginas.")
    # Adicionando a funcionalidade de logout
    elif st.button("Sair"):
        del st.session_state.usuario_logado
        st.rerun()  # Recarregar a página após o logout



# Restringir o acesso às páginas com login (Dashboard, Clientes, etc.)
if verificar_usuario_logado():
    if page == "Dashboard":
        pagina_dashboard()
    # Adicione as páginas restritas aqui, por exemplo:
    elif page == "Clientes":
        pagina_clientes()
    elif page == "Serviços":
        pagina_servico()
    elif page == "Funcionários":
        pagina_funcionarios()
    elif page == "Faturamento":
        pagina_faturamento()
else:
    st.warning("Você precisa estar logado para acessar essa página.")
    pagina_login()


