from __future__ import annotations

from datetime import date

import streamlit as st

from src import db, storage, ui
from src.auth import require_group
from src.supabase_client import get_client
from src.validators import date_or_none, parse_tags, tags_to_text

MEDIA_TYPES = ["jpg", "jpeg", "png", "webp", "gif", "mp3", "wav", "ogg", "mp4", "webm", "mov"]


def _upload_many(client, files, related_table: str, related_id: str, caption: str = "") -> None:
    for idx, f in enumerate(files or []):
        storage.upload_media(client, f, related_table, related_id, caption=caption or None, sort_order=idx)




def _place_choices(places: list[dict]) -> list[str]:
    return ["Sem lugar relacionado"] + [str(place["title"]) for place in places]


def _place_id_from_choice(places: list[dict], choice: str) -> str | None:
    for place in places:
        if str(place["title"]) == choice:
            return place["id"]
    return None


def _place_label(places_by_id: dict[str, dict], place_id: str | None) -> str | None:
    if not place_id:
        return None
    place = places_by_id.get(place_id)
    return place.get("title") if place else None


def _remove_record_with_media(client, table: str, record_id: str) -> None:
    for item in db.get_media(client, table, record_id):
        storage.remove_media(client, item)
    db.delete_record(client, table, record_id)


def render() -> None:
    require_group()
    client = get_client()
    ui.hero("Timeline", "Fotos, vídeos, áudios e textos curtinhos para guardar o caminho do grupo.", "momentos")

    places = db.list_group_records(client, "places", order="title", desc=False)
    places_by_id = {place["id"]: place for place in places}

    with st.expander("Adicionar momento", expanded=False):
        with st.form("new_timeline_entry"):
            title = st.text_input("Título", placeholder="ex.: Domingo na casa da vó")
            occurred_on = st.date_input("Data do momento", value=date.today())
            place_choice = st.selectbox("Lugar relacionado", _place_choices(places), help="Opcional: conecte este momento a um lugar já cadastrado no mapa.")
            body = st.text_area("Texto", placeholder="O que aconteceu? O que você quer lembrar?", height=120)
            tags = st.text_input("Tags separadas por vírgula", placeholder="família, almoço, risada")
            files = st.file_uploader("Fotos, vídeos ou áudios", type=MEDIA_TYPES, accept_multiple_files=True)
            submitted = st.form_submit_button("Guardar momento")
            if submitted:
                if not title.strip():
                    st.error("Título é obrigatório.")
                else:
                    saved = db.create_record(
                        client,
                        "timeline_entries",
                        {
                            "title": title.strip(),
                            "body": body.strip() or None,
                            "occurred_on": date_or_none(occurred_on),
                            "place_id": _place_id_from_choice(places, place_choice),
                            "tags": parse_tags(tags),
                        },
                    )
                    _upload_many(client, files, "timeline_entries", saved["id"])
                    st.success("Momento guardado.")
                    st.rerun()

    entries = db.list_group_records(client, "timeline_entries", order="occurred_on", desc=True)
    if not entries:
        st.info("Nenhum momento cadastrado ainda.")
        return

    for entry in entries:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='meta'>{ui.fmt_date(entry.get('occurred_on'))}</div>", unsafe_allow_html=True)
        st.markdown(f"### {entry['title']}")
        place_title = _place_label(places_by_id, entry.get("place_id"))
        if place_title:
            st.markdown(f"<span class='place-chip'>📍 {place_title}</span>", unsafe_allow_html=True)
        if entry.get("body"):
            st.write(entry["body"])
        if entry.get("tags"):
            st.markdown(ui.tags_html(entry.get("tags")), unsafe_allow_html=True)
        media = db.get_media(client, "timeline_entries", entry["id"])
        ui.render_media_gallery(client, media)
        st.markdown("</div>", unsafe_allow_html=True)

        if db.user_can_edit_record(client, entry, "timeline_entries"):
            with st.expander(f"Editar: {entry['title']}"):
                with st.form(f"edit_timeline_{entry['id']}"):
                    title = st.text_input("Título", value=entry.get("title") or "", key=f"tl_title_{entry['id']}")
                    occurred_on = st.date_input(
                        "Data",
                        value=date.fromisoformat(entry["occurred_on"]) if entry.get("occurred_on") else date.today(),
                        key=f"tl_date_{entry['id']}",
                    )
                    current_place_id = entry.get("place_id")
                    current_place_title = _place_label(places_by_id, current_place_id)
                    place_options = _place_choices(places)
                    place_index = place_options.index(current_place_title) if current_place_title in place_options else 0
                    place_choice = st.selectbox("Lugar relacionado", place_options, index=place_index, key=f"tl_place_{entry['id']}")
                    body = st.text_area("Texto", value=entry.get("body") or "", height=100, key=f"tl_body_{entry['id']}")
                    tags = st.text_input("Tags", value=tags_to_text(entry.get("tags")), key=f"tl_tags_{entry['id']}")
                    files = st.file_uploader("Adicionar mais mídia", type=MEDIA_TYPES, accept_multiple_files=True, key=f"tl_files_{entry['id']}")
                    submitted = st.form_submit_button("Salvar alterações")
                    if submitted:
                        db.update_record(
                            client,
                            "timeline_entries",
                            entry["id"],
                            {
                                "title": title.strip() or entry["title"],
                                "body": body.strip() or None,
                                "occurred_on": date_or_none(occurred_on),
                                "place_id": _place_id_from_choice(places, place_choice),
                                "tags": parse_tags(tags),
                            },
                        )
                        _upload_many(client, files, "timeline_entries", entry["id"])
                        st.success("Momento atualizado.")
                        st.rerun()

                if media:
                    st.caption("Mídias deste momento")
                    for item in media:
                        cols = st.columns([3, 1])
                        cols[0].write(f"{item.get('type')} · {item.get('caption') or item.get('storage_path', '').split('/')[-1]}")
                        if cols[1].button("Remover mídia", key=f"rm_tl_media_{item['id']}"):
                            storage.remove_media(client, item)
                            st.rerun()

                if db.user_can_delete_record(client, entry) and st.button("Apagar momento", key=f"del_tl_{entry['id']}"):
                    _remove_record_with_media(client, "timeline_entries", entry["id"])
                    st.success("Momento apagado.")
                    st.rerun()
