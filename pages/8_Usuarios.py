from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from src.config import DATABASE_URL
from src.database.connection import engine, get_session
from src.database.models import ROLES
from src.repositories import usuario_repository
from src.services import auth_service
from src.ui.components import render_styled_table
from utils import load_static_files

load_static_files()

if "usuario_logado" not in st.session_state:
    st.warning("Você precisa estar logado para acessar esta página.")
    st.stop()
if st.session_state.get("role") != "admin":
    st.warning("Apenas administradores podem gerenciar usuários.")
    st.stop()

st.title("🔐 Gestão de Usuários")

if mensagem := st.session_state.pop("flash_usuarios", None):
    st.success(mensagem)

st.write("### ➕ Cadastrar Usuário")
with st.form("usuario_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        novo_nome = st.text_input("Nome de usuário")
        novo_role = st.selectbox("Tipo de usuário", options=list(ROLES.keys()), format_func=ROLES.get)
    with col2:
        nova_senha = st.text_input("Senha", type="password")
        confirmacao = st.text_input("Confirmar senha", type="password")
    cadastrar = st.form_submit_button("Cadastrar", type="primary")

if cadastrar:
    if nova_senha != confirmacao:
        st.error("As senhas não conferem.")
    else:
        try:
            with get_session() as session:
                auth_service.criar_usuario(session, novo_nome, nova_senha, novo_role)
            st.session_state["flash_usuarios"] = f"✅ Usuário '{novo_nome.strip()}' cadastrado."
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))

st.write("### 📋 Usuários cadastrados")
with get_session() as session:
    usuarios = usuario_repository.listar(session)

df_usuarios = pd.DataFrame(
    [{"ID": u.id, "Usuário": u.nome_usuario, "Tipo": ROLES.get(u.role, u.role)} for u in usuarios]
)
render_styled_table(df_usuarios)

if usuarios:
    st.write("### ✏️ Gerenciar Usuário")
    opcoes = {f"{u.nome_usuario} ({ROLES.get(u.role, u.role)})": u for u in usuarios}
    escolhido = st.selectbox("Usuário", options=list(opcoes.keys()))
    usuario = opcoes[escolhido]

    tab_tipo, tab_senha, tab_excluir = st.tabs(["Tipo de usuário", "Redefinir senha", "Excluir"])

    with tab_tipo:
        roles = list(ROLES.keys())
        role_novo = st.selectbox(
            "Novo tipo", options=roles, index=roles.index(usuario.role) if usuario.role in roles else 0,
            format_func=ROLES.get,
        )
        if st.button("Alterar tipo"):
            try:
                with get_session() as session:
                    auth_service.alterar_role(session, usuario.id, role_novo)
                st.session_state["flash_usuarios"] = f"✅ Tipo de '{usuario.nome_usuario}' alterado."
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

    with tab_senha:
        senha_redefinida = st.text_input("Nova senha", type="password", key="senha_redefinida")
        if st.button("Redefinir senha"):
            try:
                with get_session() as session:
                    auth_service.redefinir_senha(session, usuario.id, senha_redefinida)
                st.session_state["flash_usuarios"] = f"✅ Senha de '{usuario.nome_usuario}' redefinida."
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

    with tab_excluir:
        if usuario.nome_usuario == st.session_state.get("usuario_logado"):
            st.info("Você não pode excluir o usuário com o qual está logado.")
        else:
            st.warning(f"Esta ação remove o acesso de '{usuario.nome_usuario}' e não pode ser desfeita.")
            if st.button("Excluir usuário", type="primary"):
                try:
                    with get_session() as session:
                        auth_service.excluir_usuario(session, usuario.id)
                    st.session_state["flash_usuarios"] = f"✅ Usuário '{usuario.nome_usuario}' excluído."
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

# --- Backup do banco (somente SQLite) ---
if DATABASE_URL.startswith("sqlite"):
    st.markdown("---")
    st.write("### 💾 Backup do Banco de Dados")
    st.caption(
        "Em hospedagens como o Streamlit Cloud o banco SQLite é apagado a cada redeploy. "
        "Baixe o backup regularmente (especialmente antes de atualizar o app) e restaure-o "
        "depois do redeploy. Para persistência definitiva, configure um `DATABASE_URL` "
        "de Postgres nos secrets."
    )
    caminho_db = Path(DATABASE_URL.replace("sqlite:///", ""))

    col1, col2 = st.columns(2)
    with col1:
        if caminho_db.exists():
            st.download_button(
                "📥 Baixar backup (barbearia.db)",
                data=caminho_db.read_bytes(),
                file_name=f"barbearia_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.db",
                mime="application/octet-stream",
            )
        else:
            st.info("Arquivo do banco ainda não existe.")
    with col2:
        arquivo = st.file_uploader("Restaurar backup (.db)", type=["db"])
        if arquivo is not None and st.button("♻️ Restaurar este backup", type="primary"):
            engine.dispose()  # solta as conexões para liberar o arquivo no Windows
            caminho_db.write_bytes(arquivo.getvalue())
            st.success("✅ Backup restaurado. Recarregando…")
            st.rerun()
