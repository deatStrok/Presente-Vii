from __future__ import annotations

import re
from datetime import date, datetime
from urllib.parse import urlparse

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,24}$")


def normalize_username(username: str | None) -> str:
    return (username or "").strip().lower()


def validate_username(username: str | None) -> str:
    value = normalize_username(username)
    if not USERNAME_RE.fullmatch(value):
        raise ValueError("Nome de usuário deve ter 3 a 24 caracteres e usar apenas letras, números, ponto, hífen ou underline.")
    return value


def validate_password(password: str | None) -> str:
    value = password or ""
    if len(value) < 8:
        raise ValueError("A senha precisa ter pelo menos 8 caracteres.")
    if len(value) > 128:
        raise ValueError("A senha está longa demais.")
    return value


def parse_tags(raw: str | list[str] | None) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(t).strip().lower() for t in raw if str(t).strip()]
    return [t.strip().lower() for t in raw.split(",") if t.strip()]


def tags_to_text(tags: list[str] | None) -> str:
    return ", ".join(tags or [])


def required(value: str | None, label: str) -> str:
    value = (value or "").strip()
    if not value:
        raise ValueError(f"{label} é obrigatório.")
    return value


def valid_url(value: str, label: str = "URL") -> str:
    value = required(value, label)
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"{label} precisa começar com http:// ou https://.")
    return value


def date_or_none(value: date | None) -> str | None:
    return value.isoformat() if value else None


def datetime_to_iso(value: datetime | None) -> str | None:
    return value.isoformat(timespec="minutes") if value else None
