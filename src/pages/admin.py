from __future__ import annotations

import json

import streamlit as st

from src import db, storage, ui
from src.auth import require_group
from src.supabase_client import get_client


def render() -> None:
    require_group()
    client = get_client()
    if not db.can_manage_group(client):
        st.error("Somente donos ou admins do grupo podem acessar esta área.")
        st.stop()

    group = db.get_group(client) or {}
    ui.hero("Privacidade e administração", "Exporte dados, gerencie segurança do grupo e apague conteúdo quando precisar.", "admin do grupo")

    st.subheader("Exportar dados do grupo")
    export = db.export_group(client)
    st.download_button(
        "Baixar JSON do grupo",
        data=json.dumps(export, ensure_ascii=False, indent=2),
        file_name=f"{group.get('name', 'grupo').lower().replace(' ', '_')}_export.json",
        mime="application/json",
    )

    st.subheader("Apagar conteúdo do grupo")
    st.warning("Isso apaga timeline, lugares, playlists, cartas e mídias deste grupo. Membros e grupo continuam existindo.")
    confirm = st.text_input("Digite APAGAR para confirmar", key="delete_group_content_confirm")
    if st.button("Apagar conteúdo deste grupo", type="primary"):
        if confirm != "APAGAR":
            st.error("Confirmação incorreta.")
        else:
            for item in db.list_group_records(client, "media"):
                storage.remove_media(client, item)
            db.delete_group_content(client)
            st.success("Conteúdo apagado.")
            st.rerun()

    st.subheader("Checklist rápido")
    st.markdown(
        """
        - Use convites só com pessoas do grupo.
        - Gere novo código se alguém repassou o convite sem querer.
        - Nunca coloque a `SUPABASE_SERVICE_ROLE_KEY` no GitHub.
        - Não use bucket público para fotos, áudios ou vídeos pessoais.
        """
    )
