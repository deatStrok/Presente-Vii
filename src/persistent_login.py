import streamlit as st
from streamlit_local_storage import LocalStorage

TOKEN_KEY = "presente_vii_remember_token"


@st.cache_resource
def _local_storage() -> LocalStorage:
    return LocalStorage()


def get_remember_token() -> str | None:
    try:
        value = _local_storage().getItem(TOKEN_KEY, key="remember_token_get")
        if isinstance(value, str) and value.strip():
            return value.strip()
    except Exception:
        return None
    return None


def set_remember_token(token: str) -> None:
    if not token:
        return
    try:
        _local_storage().setItem(TOKEN_KEY, token, key="remember_token_set")
    except Exception:
        pass


def clear_remember_token() -> None:
    try:
        _local_storage().deleteItem(TOKEN_KEY, key="remember_token_delete")
    except Exception:
        try:
            _local_storage().setItem(TOKEN_KEY, "", key="remember_token_clear")
        except Exception:
            pass
