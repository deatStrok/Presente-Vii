from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any

import streamlit as st


@dataclass(frozen=True)
class AppConfig:
    name: str
    supabase_url: str
    supabase_service_role_key: str
    debug_auth: bool = False
    app_base_url: str = ""


def _secret(name: str, default: str = "") -> str:
    try:
        value: Any = st.secrets.get(name, default)
    except Exception:
        value = default
    return str(value or "").strip()


def _jwt_role(token: str) -> str | None:
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload.encode()).decode())
        return data.get("role")
    except Exception:
        return None


def get_config() -> AppConfig:
    return AppConfig(
        name=_secret("APP_NAME", "Presente Vii") or "Presente Vii",
        supabase_url=_secret("SUPABASE_URL"),
        supabase_service_role_key=_secret("SUPABASE_SERVICE_ROLE_KEY"),
        debug_auth=_secret("APP_DEBUG_AUTH", "false").lower() in {"1", "true", "yes", "sim"},
        app_base_url=_secret("APP_BASE_URL"),
    )


def config_errors() -> list[str]:
    cfg = get_config()
    errors: list[str] = []
    if not cfg.supabase_url or "SEU-PROJECT-REF" in cfg.supabase_url:
        errors.append("SUPABASE_URL não foi configurada em .streamlit/secrets.toml.")
    if not cfg.supabase_service_role_key or "SUA-SERVICE-ROLE-KEY" in cfg.supabase_service_role_key:
        errors.append("SUPABASE_SERVICE_ROLE_KEY não foi configurada em .streamlit/secrets.toml.")
    if cfg.supabase_service_role_key.startswith(("sb_publishable_", "sb_anon_")):
        errors.append("Use a service_role/secret key do Supabase, não a anon/publishable key.")
    role = _jwt_role(cfg.supabase_service_role_key)
    if role and role != "service_role":
        errors.append(f"A chave configurada tem role `{role}`. Para esta versão, use a service_role key.")
    return errors
