from __future__ import annotations

import streamlit as st
import qrcode
from io import BytesIO

from src.config import get_config

from src import db, storage, ui
from src.auth import require_auth
from src.supabase_client import get_client

COVER_TYPES = ["jpg", "jpeg", "png", "webp", "gif", "mp4", "webm", "mov"]


def _invite_url(code: str) -> str:
    base = (get_config().app_base_url or "http://localhost:8501").rstrip("/")
    return f"{base}/?invite={code}"


def _qr_png_bytes(text: str) -> BytesIO:
    img = qrcode.make(text)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def render() -> None:
    require_auth()
    client = get_client()
    ui.hero("Grupos", "Crie espaços separados: namoro, família dela, sua família e todo mundo junto.", "multi-grupos")

    user_id = db.current_user_id()
    groups = db.list_my_groups(client, user_id)

    if groups:
        st.subheader("Meus grupos")
        cols = st.columns(2)
        for i, group in enumerate(groups):
            with cols[i % 2]:
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.markdown(f"<div class='meta'>{group.get('member_role')}</div>", unsafe_allow_html=True)
                st.markdown(f"### {group['name']}")
                if group.get("description"):
                    st.write(group["description"])
                selected = st.session_state.get("current_group_id") == group["id"]
                st.caption("Selecionado agora" if selected else "")
                if st.button("Usar este grupo", key=f"select_group_{group['id']}"):
                    db.set_current_group(group["id"])
                    st.query_params["view"] = "home"
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Você ainda não está em nenhum grupo. Crie um novo ou entre com código de convite.")

    col_create, col_join = st.columns(2)
    with col_create:
        st.subheader("Criar grupo")
        with st.form("create_group"):
            name = st.text_input("Nome do grupo", placeholder="ex.: Família dela")
            description = st.text_area("Descrição", placeholder="O que esse grupo vai guardar?", height=100)
            theme_color = st.selectbox("Cor do grupo", ["azul", "verde", "rosa"])
            submitted = st.form_submit_button("Criar grupo")
            if submitted:
                if not name.strip():
                    st.error("Nome é obrigatório.")
                else:
                    group = db.create_group(client, name, description, theme_color=theme_color)
                    db.set_current_group(group["id"])
                    st.success("Grupo criado.")
                    st.rerun()

    with col_join:
        st.subheader("Entrar com convite")
        with st.form("join_group"):
            invite_code = st.text_input("Código de convite", placeholder="ex.: ABC123XYZ").upper()
            submitted = st.form_submit_button("Entrar no grupo")
            if submitted:
                try:
                    group = db.join_group_by_invite(client, user_id, invite_code)
                    db.set_current_group(group["id"])
                    st.success(f"Você entrou em {group['name']}.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

    current_group = db.get_group(client, st.session_state.get("current_group_id")) if st.session_state.get("current_group_id") else None
    if not current_group:
        return

    st.divider()
    st.subheader(f"Configurações de {current_group['name']}")

    media = db.get_media(client, "home", None)
    if media:
        st.caption("Capa/mídias da Home deste grupo")
        ui.render_media_gallery(client, media, max_items=4)

    if db.can_manage_group(client):
        with st.form("edit_current_group"):
            name = st.text_input("Nome", value=current_group.get("name") or "")
            description = st.text_area("Descrição", value=current_group.get("description") or "", height=120)
            theme_color = st.selectbox("Cor", ["azul", "verde", "rosa"], index=["azul", "verde", "rosa"].index(current_group.get("theme_color") or "verde"))
            files = st.file_uploader("Adicionar fotos/vídeos à Home do grupo", type=COVER_TYPES, accept_multiple_files=True)
            submitted = st.form_submit_button("Salvar grupo")
            if submitted:
                db.update_group(client, current_group["id"], {"name": name.strip() or current_group["name"], "description": description.strip() or None, "theme_color": theme_color})
                for idx, f in enumerate(files or []):
                    storage.upload_media(client, f, "home", None, sort_order=idx)
                st.success("Grupo atualizado.")
                st.rerun()

        st.markdown("#### Convite")
        st.write("Envie o código ou o QR Code para quem você quer adicionar ao grupo:")
        invite_code = current_group.get("invite_code") or "sem código"
        invite_url = _invite_url(invite_code)
        c_code, c_qr = st.columns([2, 1])
        with c_code:
            st.caption("Código")
            st.code(invite_code, language="text")
            st.caption("Link do convite")
            st.code(invite_url, language="text")
        with c_qr:
            st.markdown("<div class='qr-box'>", unsafe_allow_html=True)
            st.image(_qr_png_bytes(invite_url), caption="Escaneie para entrar no presente", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        if st.button("Gerar novo código de convite"):
            code = db.regenerate_invite_code(client, current_group["id"])
            st.success(f"Novo código: {code}")
            st.rerun()

    st.markdown("#### Membros")
    members = db.list_group_members(client)
    for item in members:
        user = item.get("user") or {}
        cols = st.columns([3, 1, 1])
        cols[0].write(f"{user.get('avatar_emoji') or '💌'} **{user.get('display_name')}** · @{user.get('username')} · `{item.get('role')}`")
        if db.can_manage_group(client) and item.get("role") != "owner" and item.get("user_id") != user_id:
            new_role = cols[1].selectbox("Papel", ["member", "admin"], index=0 if item.get("role") == "member" else 1, key=f"role_{item['id']}", label_visibility="collapsed")
            if new_role != item.get("role"):
                db.update_member_role(client, item["id"], new_role)
                st.rerun()
            if cols[2].button("Remover", key=f"remove_member_{item['id']}"):
                db.remove_member(client, item["id"])
                st.rerun()
