from __future__ import annotations

from datetime import date, datetime, time, timedelta
import html

import streamlit as st

from src import db, storage, ui
from src.auth import require_group
from src.supabase_client import get_client
from src.validators import parse_tags, tags_to_text

MEDIA_TYPES = ["jpg", "jpeg", "png", "webp", "gif", "mp3", "wav", "ogg", "m4a", "mp4", "webm", "mov"]


def _upload_many(client, files, related_table: str, related_id: str) -> None:
    for idx, f in enumerate(files or []):
        storage.upload_media(client, f, related_table, related_id, sort_order=idx)


def _member_options(client) -> dict[str, str]:
    options: dict[str, str] = {}
    for m in db.list_group_members(client):
        user = m.get("user") or {}
        label = f"{user.get('avatar_emoji') or '💌'} {user.get('display_name') or user.get('username')} (@{user.get('username')})"
        options[label] = user["id"]
    return options


def _unlock_from_inputs(prefix: str, default_dt: datetime | None = None) -> str:
    default_dt = default_dt or (datetime.now() + timedelta(days=1)).replace(second=0, microsecond=0)
    unlock_date = st.date_input("Data em que a carta libera", value=default_dt.date(), key=f"{prefix}_unlock_date")
    unlock_time = st.time_input("Hora", value=default_dt.time().replace(second=0, microsecond=0), key=f"{prefix}_unlock_time")
    return datetime.combine(unlock_date, unlock_time).isoformat(timespec="minutes")


def render() -> None:
    require_group()
    client = get_client()
    ui.hero("Abrir quando...", "Cartas digitais para todos ou para alguém específico, com foto, áudio, vídeo e data de desbloqueio.", "cartas com tempo")

    members = _member_options(client)

    with st.expander("Criar uma carta", expanded=False):
        with st.form("new_letter"):
            title = st.text_input("Título", placeholder="ex.: Abrir quando estiver com saudade")
            trigger_label = st.text_input("Gatilho", placeholder="saudade, aniversário, dia difícil...")
            audience_label = st.radio("Quem recebe?", ["Todos do grupo", "Uma pessoa específica"], horizontal=True)
            recipient_user_id = None
            if audience_label == "Uma pessoa específica":
                recipient_label = st.selectbox("Pessoa", list(members.keys()))
                recipient_user_id = members[recipient_label]
            body = st.text_area("Texto da carta", placeholder="Escreva como se fosse uma carta mesmo...", height=220)
            unlock_at = _unlock_from_inputs("new_letter")
            tags = st.text_input("Tags", placeholder="saudade, carinho, surpresa")
            files = st.file_uploader("Fotos, áudios ou vídeos", type=MEDIA_TYPES, accept_multiple_files=True)
            submitted = st.form_submit_button("Guardar carta")
            if submitted:
                if not title.strip() or not trigger_label.strip() or not body.strip():
                    st.error("Título, gatilho e texto são obrigatórios.")
                else:
                    saved = db.create_record(
                        client,
                        "open_when_letters",
                        {
                            "title": title.strip(),
                            "trigger_label": trigger_label.strip(),
                            "body": body.strip(),
                            "unlock_at": unlock_at,
                            "audience_type": "specific" if recipient_user_id else "all",
                            "recipient_user_id": recipient_user_id,
                            "is_active": True,
                            "tags": parse_tags(tags),
                        },
                    )
                    _upload_many(client, files, "open_when_letters", saved["id"])
                    st.success("Carta guardada. Ela só abre depois da data definida.")
                    st.rerun()

    letters = db.list_visible_letters(client)
    if not letters:
        st.info("Nenhuma carta visível para você neste grupo ainda.")
        return

    selected_id = st.query_params.get("letter")
    selected = next((l for l in letters if l["id"] == selected_id), None)

    if selected:
        if st.button("← Voltar para cartas"):
            st.query_params.pop("letter", None)
            st.rerun()

        unlocked = ui.is_unlocked(selected.get("unlock_at"))
        audience = "todos" if selected.get("audience_type") == "all" else db.recipient_label(client, selected.get("recipient_user_id"))
        st.markdown("<div class='letter-card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='meta'>Abrir quando: {selected.get('trigger_label')} · para {audience}</div>", unsafe_allow_html=True)
        st.markdown(f"## {selected['title']}")
        st.caption(f"Libera em {ui.fmt_datetime(selected.get('unlock_at'))}")
        if not unlocked:
            st.markdown(
                f"<div class='unlock-box'>🔒 Essa carta ainda está fechada. Ela abre em {ui.fmt_datetime(selected.get('unlock_at'))}.</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f"<div class='letter-body'>{html.escape(selected.get('body') or '')}</div>", unsafe_allow_html=True)
            media = db.get_media(client, "open_when_letters", selected["id"])
            ui.render_media_gallery(client, media)
        st.markdown("</div>", unsafe_allow_html=True)
        return

    cols = st.columns(3)
    for i, letter in enumerate(letters):
        unlocked = ui.is_unlocked(letter.get("unlock_at"))
        audience = "todos" if letter.get("audience_type") == "all" else db.recipient_label(client, letter.get("recipient_user_id"))
        with cols[i % 3]:
            st.markdown("<div class='letter-card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='meta'>{'aberta' if unlocked else 'fechada'} · para {audience}</div>", unsafe_allow_html=True)
            st.markdown(f"### {letter['title']}")
            st.caption(f"Gatilho: {letter.get('trigger_label')}")
            st.caption(f"Libera em {ui.fmt_datetime(letter.get('unlock_at'))}")
            if letter.get("tags"):
                st.markdown(ui.tags_html(letter.get("tags")), unsafe_allow_html=True)
            if st.button("Abrir carta" if unlocked else "Ver data", key=f"open_letter_{letter['id']}"):
                st.query_params["letter"] = letter["id"]
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        if db.user_can_edit_record(client, letter, "open_when_letters"):
            with st.expander(f"Editar carta: {letter['title']}"):
                current_dt = ui.parse_datetime(letter.get("unlock_at"))
                with st.form(f"edit_letter_{letter['id']}"):
                    title = st.text_input("Título", value=letter.get("title") or "", key=f"lt_title_{letter['id']}")
                    trigger_label = st.text_input("Gatilho", value=letter.get("trigger_label") or "", key=f"lt_trigger_{letter['id']}")
                    audience_default = "Todos do grupo" if letter.get("audience_type") == "all" else "Uma pessoa específica"
                    audience_label = st.radio("Quem recebe?", ["Todos do grupo", "Uma pessoa específica"], index=0 if audience_default == "Todos do grupo" else 1, horizontal=True, key=f"lt_audience_{letter['id']}")
                    recipient_user_id = None
                    if audience_label == "Uma pessoa específica":
                        labels = list(members.keys())
                        current_recipient = letter.get("recipient_user_id")
                        current_label = next((label for label, uid in members.items() if uid == current_recipient), labels[0])
                        recipient_label = st.selectbox("Pessoa", labels, index=labels.index(current_label), key=f"lt_recipient_{letter['id']}")
                        recipient_user_id = members[recipient_label]
                    body = st.text_area("Texto", value=letter.get("body") or "", height=180, key=f"lt_body_{letter['id']}")
                    unlock_at = _unlock_from_inputs(f"edit_letter_{letter['id']}", current_dt)
                    is_active = st.checkbox("Carta ativa", value=letter.get("is_active", True), key=f"lt_active_{letter['id']}")
                    tags = st.text_input("Tags", value=tags_to_text(letter.get("tags")), key=f"lt_tags_{letter['id']}")
                    files = st.file_uploader("Adicionar mídia", type=MEDIA_TYPES, accept_multiple_files=True, key=f"lt_files_{letter['id']}")
                    submitted = st.form_submit_button("Salvar carta")
                    if submitted:
                        db.update_record(
                            client,
                            "open_when_letters",
                            letter["id"],
                            {
                                "title": title.strip() or letter["title"],
                                "trigger_label": trigger_label.strip() or letter.get("trigger_label"),
                                "body": body.strip() or letter.get("body"),
                                "unlock_at": unlock_at,
                                "audience_type": "specific" if recipient_user_id else "all",
                                "recipient_user_id": recipient_user_id,
                                "is_active": bool(is_active),
                                "tags": parse_tags(tags),
                            },
                        )
                        _upload_many(client, files, "open_when_letters", letter["id"])
                        st.success("Carta atualizada.")
                        st.rerun()
                media = db.get_media(client, "open_when_letters", letter["id"])
                if media:
                    st.caption("Mídias da carta")
                    for item in media:
                        cols2 = st.columns([3, 1])
                        cols2[0].write(f"{item.get('type')} · {item.get('caption') or item.get('storage_path', '').split('/')[-1]}")
                        if cols2[1].button("Remover", key=f"rm_letter_media_{item['id']}"):
                            storage.remove_media(client, item)
                            st.rerun()
                if db.user_can_delete_record(client, letter) and st.button("Apagar carta", key=f"del_letter_{letter['id']}"):
                    for item in media:
                        storage.remove_media(client, item)
                    db.delete_record(client, "open_when_letters", letter["id"])
                    st.success("Carta apagada.")
                    st.rerun()
