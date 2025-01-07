import streamlit as st
import os

# Função para carregar arquivos estáticos
def load_static_files():
    static_dir = "static"
    css_files = [ "style.css"]  # Adicionei o style.css
    js_files = ["bootstrap.bundle.min.js"]

    # Carrega CSS
    for css_file in css_files:
        file_path = os.path.join(static_dir, css_file)
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                css = f.read()
                st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
        else:
            st.warning(f"Arquivo CSS não encontrado: {css_file}")

    # Carrega JS
    for js_file in js_files:
        file_path = os.path.join(static_dir, js_file)
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                js = f.read()
                st.markdown(f"<script>{js}</script>", unsafe_allow_html=True)
        else:
            st.warning(f"Arquivo JS não encontrado: {js_file}")