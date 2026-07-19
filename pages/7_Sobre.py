import streamlit as st

from src.config import HORARIO_ABERTURA, HORARIO_FECHAMENTO
from utils import load_static_files

load_static_files()

st.title("ℹ️ Sobre Nós")

st.markdown(
    f"""
    ### 💈 Nossa Barbearia

    Tradição e estilo no cuidado masculino. Trabalhamos com profissionais
    experientes, produtos de qualidade e um ambiente pensado para você relaxar
    enquanto cuida do visual.

    #### 🕗 Horário de funcionamento
    - Segunda a sábado, das **{HORARIO_ABERTURA}** às **{HORARIO_FECHAMENTO}**

    #### 📅 Como agendar
    Use a página **Agenda** para marcar seu horário — agendamentos são feitos
    com pelo menos **1 dia de antecedência**. Escolha o profissional, o serviço
    e o horário que preferir.

    #### 📞 Contato
    - WhatsApp: (00) 00000-0000
    - E-mail: contato@barbearia.com
    - Endereço: Rua Exemplo, 123 — Centro

    ---
    *Sistema de gestão da barbearia — agenda, clientes, caixa e faturamento em um só lugar.*
    """
)
