from __future__ import annotations

import streamlit as st

from src import db, ui
from src.auth import require_group
from src.supabase_client import get_client


def render() -> None:
    require_group()
    client = get_client()
    group = db.get_group(client) or {}
    ui.hero(group.get("name") or "Nosso grupo", group.get("description") or "Um espaço privado para guardar o que merece ficar.", "grupo selecionado")

    media = db.get_media(client, "home", None)
    ui.render_media_gallery(client, media, max_items=6)

    counts = db.group_counts(client)
    ui.render_nav_cards(
        [
            {
                "label": "Momentos",
                "value": counts["momentos"],
                "icon": "📸",
                "hint": "Ver timeline",
                "href": "?view=timeline",
                "aria": "Abrir timeline de momentos",
            },
            {
                "label": "Lugares",
                "value": counts["lugares"],
                "icon": "🗺️",
                "hint": "Ver mapa",
                "href": "?view=places",
                "aria": "Abrir mapa de lugares",
            },
            {
                "label": "Playlists",
                "value": counts["playlists"],
                "icon": "🎧",
                "hint": "Ouvir músicas",
                "href": "?view=playlists",
                "aria": "Abrir playlists",
            },
            {
                "label": "Cartas",
                "value": counts["cartas"],
                "icon": "💌",
                "hint": "Abrir cartas",
                "href": "?view=open_when",
                "aria": "Abrir cartas digitais",
            },
            {
                "label": "Membros",
                "value": counts["membros"],
                "icon": "🫶",
                "hint": "Ver grupo",
                "href": "?view=groups",
                "aria": "Abrir grupos e membros",
            },
        ]
    )

    st.subheader("Últimos momentos")
    entries = db.list_group_records(client, "timeline_entries", order="occurred_on", desc=True)[:3]
    if not entries:
        st.info("Ainda não há momentos neste grupo.")
    for entry in entries:
        with st.container():
            ui.card(entry["title"], entry.get("body"), ui.fmt_date(entry.get("occurred_on")), entry.get("tags"))

    st.subheader("Cartas esperando a hora certa")
    letters = db.list_visible_letters(client)[:3]
    if not letters:
        st.info("Ainda não há cartas visíveis para você neste grupo.")
    for letter in letters:
        unlocked = ui.is_unlocked(letter.get("unlock_at"))
        meta = "pode abrir agora" if unlocked else f"abre em {ui.fmt_datetime(letter.get('unlock_at'))}"
        audience = "para todos" if letter.get("audience_type") == "all" else f"para {db.recipient_label(client, letter.get('recipient_user_id'))}"
        ui.card(letter["title"], f"Abrir quando: {letter.get('trigger_label')} · {audience}", meta, letter.get("tags"), letter=True)
