import streamlit as st

from src.database.connection import get_session, init_db
from src.services import auth_service, caixa_service
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

# Lembrete inteligente do caixa: acompanha o admin em todas as páginas até o
# fechamento do dia ser feito (e cobra dias anteriores esquecidos em aberto).
if logged_in and st.session_state.get("role") == "admin":
    with get_session() as session:
        alertas_caixa = caixa_service.pendencias(session)
    if alertas_caixa:
        if not st.session_state.get("lembrete_caixa_exibido"):
            for alerta in alertas_caixa:
                st.toast(alerta["mensagem"], icon="🔔")
            st.session_state["lembrete_caixa_exibido"] = True
        with st.sidebar:
            st.markdown("#### 🔔 Lembretes do caixa")
            for alerta in alertas_caixa:
                if alerta["nivel"] == "erro":
                    st.error(alerta["mensagem"])
                elif alerta["nivel"] == "aviso":
                    st.warning(alerta["mensagem"])
                else:
                    st.info(alerta["mensagem"])

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
            st.Page("pages/9_Caixa.py", title="Caixa", icon="🧾"),
            st.Page("pages/10_Pagamentos.py", title="Pagamentos", icon="🤝"),
            st.Page("pages/11_Relatorios.py", title="Relatórios", icon="📈"),
            st.Page("pages/8_Usuarios.py", title="Usuários", icon="🔐"),
        ]

# "Sobre Nós" fica por último para aparecer no canto inferior esquerdo do menu.
paginas.append(st.Page("pages/7_Sobre.py", title="Sobre Nós", icon="ℹ️"))

pg = st.navigation(paginas)
pg.run()
