import streamlit as st

from src.database.connection import get_session, init_db
from src.services import auth_service
from utils import load_static_files

st.set_page_config(page_title="Gerenciador de Barbearia", page_icon="💈", layout="wide")

init_db()
load_static_files()

st.markdown(
    """
    <div class="marca-barbearia">
        <h1>💈 Gerenciador de Barbearia</h1>
        <div class="divisa"></div>
        <p class="tagline">Agenda &middot; Clientes &middot; Faturamento</p>
    </div>
    """,
    unsafe_allow_html=True,
)


def _pagina_login() -> None:
    st.sidebar.markdown("### 📝 Login da equipe")
    with st.sidebar.form("login_form"):
        nome_usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")

    if submitted:
        with get_session() as session:
            usuario = auth_service.autenticar(session, nome_usuario, senha)
        if usuario:
            st.session_state.usuario_logado = usuario.nome_usuario
            st.session_state.role = usuario.role
            st.rerun()
        else:
            st.sidebar.error("Usuário ou senha incorretos.")


logged_in = "usuario_logado" in st.session_state

with st.sidebar:
    if logged_in:
        st.write(f"👋 Olá, **{st.session_state.usuario_logado}**")
        if st.button("Sair"):
            st.session_state.pop("usuario_logado", None)
            st.session_state.pop("role", None)
            st.rerun()
    else:
        _pagina_login()

# A Agenda é pública (clientes agendam sem login); as demais páginas são da equipe.
paginas = [st.Page("pages/3_Agenda.py", title="Agenda", icon="📅", default=True)]

if logged_in:
    paginas += [
        st.Page("pages/1_Dashboard.py", title="Dashboard", icon="📊"),
        st.Page("pages/2_Clientes.py", title="Clientes", icon="👤"),
    ]
    if st.session_state.get("role") == "admin":
        paginas += [
            st.Page("pages/4_Servicos.py", title="Serviços", icon="✂️"),
            st.Page("pages/5_Funcionarios.py", title="Funcionários", icon="🧑‍🔧"),
            st.Page("pages/6_Faturamento.py", title="Faturamento", icon="💵"),
        ]

pg = st.navigation(paginas)
pg.run()
