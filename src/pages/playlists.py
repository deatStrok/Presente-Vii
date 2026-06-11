from __future__ import annotations

import streamlit as st

from src import db, storage, ui
from src.auth import require_group
from src.supabase_client import get_client
from src.validators import parse_tags, tags_to_text, valid_url

MEDIA_TYPES = ["jpg", "jpeg", "png", "webp", "gif"]
PLATFORMS = {
    "spotify": "Spotify",
    "youtube": "YouTube",
    "apple_music": "Apple Music",
    "deezer": "Deezer",
    "other": "Outro link",
}


def _upload_many(client, files, related_table: str, related_id: str) -> None:
    for idx, f in enumerate(files or []):
        storage.upload_media(client, f, related_table, related_id, sort_order=idx)


def render() -> None:
    require_group()
    client = get_client()
    ui.hero("Playlists", "Todo mundo do grupo pode colocar e ajustar as trilhas sonoras dos momentos.", "músicas")

    with st.expander("Adicionar playlist", expanded=False):
        with st.form("new_playlist"):
            title = st.text_input("Título", placeholder="ex.: Músicas para o caminho")
            platform_label = st.selectbox("Plataforma", list(PLATFORMS.values()))
            platform = next(k for k, v in PLATFORMS.items() if v == platform_label)
            url = st.text_input("Link", placeholder="https://open.spotify.com/...")
            note = st.text_area("Nota", placeholder="Por que essa playlist combina com o grupo?", height=100)
            tags = st.text_input("Tags", placeholder="viagem, saudade, domingo")
            files = st.file_uploader("Capa/fotos opcionais", type=MEDIA_TYPES, accept_multiple_files=True)
            submitted = st.form_submit_button("Salvar playlist")
            if submitted:
                try:
                    saved = db.create_record(
                        client,
                        "playlists",
                        {
                            "title": title.strip(),
                            "platform": platform,
                            "url": valid_url(url),
                            "note": note.strip() or None,
                            "tags": parse_tags(tags),
                            "updated_by": db.current_user_id(),
                        },
                    )
                    _upload_many(client, files, "playlists", saved["id"])
                    st.success("Playlist salva.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

    playlists = db.list_group_records(client, "playlists", order="updated_at", desc=True)
    if not playlists:
        st.info("Nenhuma playlist cadastrada ainda.")
        return

    for item in playlists:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='meta'>{PLATFORMS.get(item.get('platform'), item.get('platform') or 'link')}</div>", unsafe_allow_html=True)
        st.markdown(f"### {item['title']}")
        if item.get("note"):
            st.write(item["note"])
        st.link_button("Abrir playlist", item["url"])
        if item.get("tags"):
            st.markdown(ui.tags_html(item.get("tags")), unsafe_allow_html=True)
        media = db.get_media(client, "playlists", item["id"])
        ui.render_media_gallery(client, media, max_items=3)
        st.markdown("</div>", unsafe_allow_html=True)

        if db.user_can_edit_record(client, item, "playlists"):
            with st.expander(f"Alterar playlist: {item['title']}"):
                with st.form(f"edit_playlist_{item['id']}"):
                    title = st.text_input("Título", value=item.get("title") or "", key=f"ps_title_{item['id']}")
                    current_platform = PLATFORMS.get(item.get("platform"), "Outro link")
                    platform_label = st.selectbox("Plataforma", list(PLATFORMS.values()), index=list(PLATFORMS.values()).index(current_platform) if current_platform in PLATFORMS.values() else 0, key=f"ps_platform_{item['id']}")
                    platform = next(k for k, v in PLATFORMS.items() if v == platform_label)
                    url = st.text_input("Link", value=item.get("url") or "", key=f"ps_url_{item['id']}")
                    note = st.text_area("Nota", value=item.get("note") or "", height=100, key=f"ps_note_{item['id']}")
                    tags = st.text_input("Tags", value=tags_to_text(item.get("tags")), key=f"ps_tags_{item['id']}")
                    files = st.file_uploader("Adicionar capa/fotos", type=MEDIA_TYPES, accept_multiple_files=True, key=f"ps_files_{item['id']}")
                    submitted = st.form_submit_button("Salvar alterações")
                    if submitted:
                        try:
                            db.update_record(
                                client,
                                "playlists",
                                item["id"],
                                {
                                    "title": title.strip() or item["title"],
                                    "platform": platform,
                                    "url": valid_url(url),
                                    "note": note.strip() or None,
                                    "tags": parse_tags(tags),
                                    "updated_by": db.current_user_id(),
                                },
                            )
                            _upload_many(client, files, "playlists", item["id"])
                            st.success("Playlist atualizada.")
                            st.rerun()
                        except Exception as exc:
                            st.error(str(exc))

                if db.user_can_delete_record(client, item) and st.button("Apagar playlist", key=f"del_playlist_{item['id']}"):
                    for media_item in media:
                        storage.remove_media(client, media_item)
                    db.delete_record(client, "playlists", item["id"])
                    st.success("Playlist apagada.")
                    st.rerun()
