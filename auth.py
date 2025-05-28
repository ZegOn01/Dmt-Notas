# auth.py
import streamlit as st
import os

def check_password():
    """Verifica a senha usando st.secrets."""
    if "users" not in st.secrets:
        st.error("Configuração '[users]' não encontrada em st.secrets.")
        return False

    def password_entered():
        user = st.session_state.get("username")
        pwd = st.session_state.get("password")
        users_dict = st.secrets["users"].to_dict()

        if user and pwd and user in users_dict and pwd == users_dict[user]:
            st.session_state["password_correct"] = True
            st.session_state["logged_in_user"] = user
            if "password" in st.session_state:
                del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.title("Login :closed_lock_with_key:")
        usernames = list(st.secrets["users"].keys())
        st.selectbox("Selecione seu nome de usuário:", usernames, key="username")
        st.text_input("Senha:", type="password", on_change=password_entered, key="password")

        if "password" in st.session_state and st.session_state["password"] and not st.session_state["password_correct"]:
            st.error("Usuário ou senha incorretos.")
        return False

    return True

def force_relogin_on_navigate(current_script_file):
    """
    Verifica a navegação e força o relogin se a página mudou.
    Retorna True se o usuário está logado (após a verificação), False caso contrário.
    """
    current_path = os.path.abspath(current_script_file)
    last_path = st.session_state.get("last_script_path")

    if last_path and current_path != last_path:
        if "password_correct" in st.session_state:
            del st.session_state["password_correct"]
        if "logged_in_user" in st.session_state:
            del st.session_state["logged_in_user"]
        del st.session_state["last_script_path"]
        st.toast("Navegação detectada. Faça login novamente.") # Usando toast para ser menos intrusivo

    is_logged_in = check_password()

    if is_logged_in:
        st.session_state["last_script_path"] = current_path
        return True
    else:
        if "last_script_path" in st.session_state:
            del st.session_state["last_script_path"]
        return False

def add_logout_button():
    """Adiciona um botão de logout à barra lateral."""
    if st.sidebar.button("🚪 Sair"):
        keys_to_delete = ["password_correct", "logged_in_user", "last_script_path"]
        for key in keys_to_delete:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()