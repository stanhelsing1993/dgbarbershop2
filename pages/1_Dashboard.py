import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder
from utils import load_static_files

# Carregar CSS e JS
load_static_files()

# Verificar se o usuário está logado
if 'usuario_logado' not in st.session_state:
    st.warning("Você precisa estar logado para acessar esta página.")
    st.stop()  # Parar o código e não carregar o restante da página

# Título da Página
st.title("📊 Dashboard Principal")

# Conectar ao Banco de Dados
conn = sqlite3.connect('barbearia.db')

# Query com JOINs para substituir IDs pelos nomes correspondentes
query = """
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
"""

# Carregar os Dados
df_agendamentos = pd.read_sql_query(query, conn)

# Ajustar a coluna 'Horario' para garantir o formato 'HH:MM:SS'
df_agendamentos['Horario'] = df_agendamentos['Horario'].apply(lambda x: f"{x}:00" if len(x.split(':')) == 2 else x)

# Preparar DataFrame para conversão e concatenação
df_agenda_func = df_agendamentos.copy()

# Garantir que 'Data' seja convertido para datetime corretamente
df_agenda_func['Data'] = pd.to_datetime(df_agenda_func['Data'], format='%Y-%m-%d').dt.date

# Concatenar Data e Hora em uma nova coluna 'x_start'
df_agenda_func['x_start'] = pd.to_datetime(df_agenda_func['Data'].astype(str) + ' ' + df_agenda_func['Horario'])

# Criar a coluna 'x_end', que adiciona 30 minutos ao 'x_start'
df_agenda_func['x_end'] = df_agenda_func['x_start'] + pd.Timedelta(minutes=30)

# Exibir a tabela interativa
st.write("### 📅 Próximos Agendamentos")

# Configurar a tabela para ocupar toda a largura da tela
gb = GridOptionsBuilder.from_dataframe(df_agenda_func)
gb.configure_pagination(paginationAutoPageSize=True)  # Paginação automática
gb.configure_side_bar()  # Adiciona barra lateral para filtros
gb.configure_default_column(resizable=True, sortable=True, filterable=True)
grid_options = gb.build()

AgGrid(df_agenda_func, gridOptions=grid_options, height=400, fit_columns_on_grid_load=True)

st.markdown("---")

# Filtros para Calendário
col1, col2 = st.columns(2)
with col1:
    selected_funcionario = st.selectbox("Selecione o Funcionário", ["Todos Funcionários"] + list(df_agenda_func['Funcionario'].unique()))
with col2:
    selected_week = st.date_input("Selecione a Semana", pd.Timestamp.now().date())

# Preparar DataFrame para filtragem
df_agenda_func['Data'] = pd.to_datetime(df_agenda_func['Data']).dt.date

# Filtrar por Semana
df_agenda_func = df_agenda_func[
    (df_agenda_func['Data'] >= selected_week) & (df_agenda_func['Data'] < (selected_week + pd.Timedelta(days=7)))
]

# Adicionar coluna para DateTime Completo
df_agenda_func['x_start'] = pd.to_datetime(
    df_agenda_func['Data'].astype(str) + ' ' + df_agenda_func['Horario'].astype(str))
df_agenda_func['x_end'] = df_agenda_func['x_start'] + pd.Timedelta(minutes=30)

# 📊 Exibir Gráficos
st.write("## 📊 Gráficos de Agendamentos")

if selected_funcionario == "Todos Funcionários":
    st.write("### 🗓️ Agenda Geral - Data x Hora")
    calendar_all = px.scatter(
        df_agenda_func,
        x='x_start',
        y='Funcionario',
        color='Servico',
        title="📅 Agenda Geral - Data x Hora",
        labels={'x_start': 'Data e Hora', 'Funcionario': 'Funcionário'}
    )
    calendar_all.update_traces(marker=dict(size=10))
    calendar_all.update_layout(
        xaxis_title="Data e Hora",
        yaxis_title="Funcionário",
        height=500
    )
    st.plotly_chart(calendar_all, use_container_width=True)

    st.write("### 📊 Quantidade de Agendamentos por Funcionário")
    count_chart = px.bar(
        df_agenda_func,
        x='Funcionario',
        color='Servico',
        title="📊 Agendamentos por Funcionário",
        labels={'Funcionario': 'Funcionário', 'count': 'Quantidade'}
    )
    st.plotly_chart(count_chart, use_container_width=True)

    st.write("### 📊 Distribuição de Serviços Agendados")
    service_pie = px.pie(
        df_agenda_func,
        names='Servico',
        title="🍰 Distribuição de Serviços Agendados"
    )
    st.plotly_chart(service_pie, use_container_width=True)

else:
    st.write(f"### 🗓️ Agenda de {selected_funcionario} - Data x Hora")
    df_func = df_agenda_func[df_agenda_func['Funcionario'] == selected_funcionario]

    calendar_func = px.scatter(
        df_func,
        x='x_start',
        y='Servico',
        color='Cliente',
        title=f"📅 Agenda de {selected_funcionario} - Data x Hora",
        labels={'x_start': 'Data e Hora', 'Servico': 'Serviço'}
    )
    calendar_func.update_traces(marker=dict(size=10))
    calendar_func.update_layout(
        xaxis_title="Data e Hora",
        yaxis_title="Serviço",
        height=500
    )
    st.plotly_chart(calendar_func, use_container_width=True)

    st.write("### 📊 Distribuição de Serviços do Funcionário")
    service_pie_func = px.pie(
        df_func,
        names='Servico',
        title=f"🍰 Distribuição de Serviços de {selected_funcionario}"
    )
    st.plotly_chart(service_pie_func, use_container_width=True)

    st.write("### 📊 Quantidade de Agendamentos por Data")
    count_chart_func = px.bar(
        df_func,
        x='Data',
        color='Servico',
        title=f"📊 Agendamentos de {selected_funcionario} por Data",
        labels={'Data': 'Data', 'count': 'Quantidade'}
    )
    st.plotly_chart(count_chart_func, use_container_width=True)

# Fechar Conexão
conn.close()
