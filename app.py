from __future__ import annotations

import streamlit as st

from src import db, ui
from src.auth import init_auth_state, is_logged_in, logout, render_auth_page, try_restore_persistent_login
from src.config import get_config
from src.pages import admin, groups, home, open_when, places, playlists, timeline
from src.supabase_client import get_client

st.set_page_config(page_title="Presente Vii", page_icon="💌", layout="wide")

init_auth_state()
ui.inject_css()
cfg = get_config()

try_restore_persistent_login()

if not is_logged_in():
    render_auth_page()
    st.stop()

client = get_client()
user = st.session_state.get("app_user") or {}
invite_code_from_url = str(st.query_params.get("invite") or "").strip().upper()
if invite_code_from_url and user.get("id"):
    try:
        invited_group = db.join_group_by_invite(client, user["id"], invite_code_from_url)
        st.session_state.current_group_id = invited_group["id"]
        st.query_params.pop("invite", None)
        st.query_params["view"] = "home"
        st.toast(f"Você entrou em {invited_group['name']} 💖")
        st.rerun()
    except Exception as exc:
        st.warning(f"Não consegui entrar pelo convite: {exc}")
        st.query_params.pop("invite", None)

try:
    my_groups = db.list_my_groups(client, user["id"])
except db.NETWORK_EXCEPTIONS as exc:
    ui.hero("Conexão instável", "O Supabase demorou para responder. Aguarde alguns segundos e tente recarregar a página.", "rede")
    st.error(f"Erro de rede: {type(exc).__name__}. Isso costuma ser temporário no Windows quando a conexão HTTP não fecha/abre a tempo.")
    if st.button("Tentar novamente"):
        st.rerun()
    st.stop()

with st.sidebar:
    st.markdown(f"# {cfg.name}")
    st.markdown(ui.chip(f"{user.get('avatar_emoji', '💌')} {user.get('display_name', 'usuário')}") + ui.chip(f"@{user.get('username', '')}"), unsafe_allow_html=True)

    if my_groups:
        group_labels = [f"{g['name']} · {g.get('member_role')}" for g in my_groups]
        current_group_id = st.session_state.get("current_group_id")
        if current_group_id not in [g["id"] for g in my_groups]:
            st.session_state.current_group_id = my_groups[0]["id"]
            current_group_id = my_groups[0]["id"]
        current_index = next((i for i, g in enumerate(my_groups) if g["id"] == current_group_id), 0)
        selected_label = st.selectbox("Grupo atual", group_labels, index=current_index)
        selected_group = my_groups[group_labels.index(selected_label)]
        if selected_group["id"] != st.session_state.get("current_group_id"):
            st.session_state.current_group_id = selected_group["id"]
            if "letter" in st.query_params:
                st.query_params.pop("letter", None)
            st.rerun()
    else:
        st.info("Sem grupo ainda")
        st.session_state.current_group_id = None

    nav_options = {"Grupos": "groups"}
    if st.session_state.get("current_group_id"):
        nav_options = {
            "Home": "home",
            "Timeline": "timeline",
            "Mapa": "places",
            "Playlists": "playlists",
            "Abrir quando...": "open_when",
            "Grupos": "groups",
        }
        if db.can_manage_group(client):
            nav_options["Admin do grupo"] = "admin"

    current = st.query_params.get("view", "home" if st.session_state.get("current_group_id") else "groups")
    labels = list(nav_options.keys())
    values = list(nav_options.values())
    if current not in values:
        current = values[0]
    selected_nav = st.radio("Navegação", labels, index=values.index(current), label_visibility="collapsed")
    if nav_options[selected_nav] != st.query_params.get("view"):
        st.query_params["view"] = nav_options[selected_nav]
        if "letter" in st.query_params and nav_options[selected_nav] != "open_when":
            st.query_params.pop("letter", None)
        st.rerun()

    st.divider()
    if st.button("Sair"):
        logout()

view = st.query_params.get("view", "home" if st.session_state.get("current_group_id") else "groups")

if view == "home":
    home.render()
elif view == "timeline":
    timeline.render()
elif view == "places":
    places.render()
elif view == "playlists":
    playlists.render()
elif view == "open_when":
    open_when.render()
elif view == "groups":
    groups.render()
elif view == "admin":
    admin.render()
else:
    st.query_params["view"] = "groups"
    st.rerun()
