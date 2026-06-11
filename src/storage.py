from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import streamlit as st
from supabase import Client

from src import db

BUCKET = "memories"
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
AUDIO_TYPES = {"audio/mpeg", "audio/mp3", "audio/wav", "audio/ogg", "audio/x-wav", "audio/aac", "audio/mp4"}
VIDEO_TYPES = {"video/mp4", "video/webm", "video/quicktime", "video/mpeg"}
ALLOWED_TYPES = IMAGE_TYPES | AUDIO_TYPES | VIDEO_TYPES


def _safe_ext(filename: str, mime_type: str) -> str:
    ext = Path(filename or "upload").suffix.lower()
    if ext and len(ext) <= 10 and all(ch.isalnum() or ch == "." for ch in ext):
        return ext
    return {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/ogg": ".ogg",
        "audio/aac": ".aac",
        "audio/mp4": ".m4a",
        "video/mp4": ".mp4",
        "video/webm": ".webm",
        "video/quicktime": ".mov",
        "video/mpeg": ".mpeg",
    }.get(mime_type, ".bin")


def media_kind(mime_type: str) -> str:
    if mime_type in IMAGE_TYPES:
        return "image"
    if mime_type in AUDIO_TYPES:
        return "audio"
    if mime_type in VIDEO_TYPES:
        return "video"
    raise ValueError("Formato não permitido. Use imagem, áudio ou vídeo nos formatos comuns: JPG, PNG, WebP, GIF, MP3, WAV, OGG, MP4, WebM ou MOV.")


def upload_media(
    client: Client,
    uploaded_file,
    related_table: str,
    related_id: str | None,
    caption: str | None = None,
    sort_order: int = 0,
) -> dict:
    mime_type = getattr(uploaded_file, "type", None) or "application/octet-stream"
    kind = media_kind(mime_type)
    group_id = db.current_group_id()
    entity_id = related_id or "home"
    ext = _safe_ext(uploaded_file.name, mime_type)
    path = f"{group_id}/{related_table}/{entity_id}/{uuid4().hex}{ext}"

    client.storage.from_(BUCKET).upload(
        path,
        uploaded_file.getvalue(),
        file_options={"content-type": mime_type, "upsert": "false"},
    )
    return db.create_media_record(
        client,
        {
            "related_table": related_table,
            "related_id": related_id,
            "type": kind,
            "mime_type": mime_type,
            "storage_bucket": BUCKET,
            "storage_path": path,
            "caption": caption,
            "sort_order": sort_order,
        },
    )


def signed_url(client: Client, storage_path: str, expires_in: int = 3600) -> str | None:
    try:
        result = client.storage.from_(BUCKET).create_signed_url(storage_path, expires_in)
        if isinstance(result, dict):
            return result.get("signedURL") or result.get("signedUrl") or result.get("signed_url") or result.get("signedUrl")
        if hasattr(result, "get"):
            return result.get("signedURL") or result.get("signed_url")
    except Exception:
        return None
    return None


def remove_media(client: Client, media: dict) -> None:
    try:
        client.storage.from_(media.get("storage_bucket") or BUCKET).remove([media["storage_path"]])
    except Exception:
        st.warning("Arquivo não removido do Storage; removendo o registro do banco.")
    db.delete_media_record(client, media["id"])
