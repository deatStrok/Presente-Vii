from __future__ import annotations

import time
from typing import Any

import streamlit as st
from src import db
from src.config import config_errors, get_config
from src.supabase_client import get_client
from src.validators import validate_password, validate_username
from src.security import hash_password, needs_rehash, verify_password
from src.persistent_login import clear_remember_token, get_remember_token, set_remember_token

MAX_LOGIN_ATTEMPTS = 6
LOCK_SECONDS = 60


def init_auth_state() -> None:
    st.session_state.setdefault("app_user", None)
    st.session_state.setdefault("current_group_id", None)
    st.session_state.setdefault("login_fail_count", 0)
    st.session_state.setdefault("login_locked_until", 0.0)


def is_logged_in() -> bool:
    return bool(st.session_state.get("app_user"))


def current_user() -> dict[str, Any] | None:
    return st.session_state.get("app_user")


def _session_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["id"],
        "username": user["username"],
        "display_name": user.get("display_name") or user["username"],
        "avatar_emoji": user.get("avatar_emoji") or "💌",
    }

def _persist_login(client, user_id: str) -> None:
    try:
        token = db.create_persistent_session(client, user_id)
        set_remember_token(token)
    except Exception:
        # O login normal continua funcionando mesmo se o navegador bloquear o storage.
        pass


def try_restore_persistent_login() -> bool:
    """Restore login from the browser token when Streamlit creates a new session."""
    if is_logged_in():
        return True
    token = get_remember_token()
    if not token:
        return False
    try:
        client = get_client()
        user = db.get_user_by_persistent_token(client, token)
        if not user:
            clear_remember_token()
            return False
        st.session_state.app_user = _session_user(user)
        st.session_state.login_fail_count = 0
        st.session_state.login_locked_until = 0.0
        _select_first_available_group(client)
        return True
    except Exception:
        # Evita bloquear a tela de login se o token antigo não puder ser validado.
        return False



def login(username: str, password: str) -> tuple[bool, str]:
    now = time.time()
    if now < st.session_state.get("login_locked_until", 0.0):
        remaining = int(st.session_state["login_locked_until"] - now)
        return False, f"Muitas tentativas. Tente novamente em {remaining}s."

    try:
        normalized = validate_username(username)
        client = get_client()
        user = db.get_user_by_username(client, normalized)
        if not user or not verify_password(user["password_hash"], password or ""):
            raise ValueError("invalid credentials")
        if needs_rehash(user["password_hash"]):
            db.execute_query(client.table("app_users").update({"password_hash": hash_password(password)}).eq("id", user["id"]))
        db.mark_login(client, user["id"])
        st.session_state.app_user = _session_user(user)
        _persist_login(client, user["id"])
        st.session_state.login_fail_count = 0
        st.session_state.login_locked_until = 0.0
        invite_code = str(st.query_params.get("invite") or "").strip().upper()
        if invite_code:
            try:
                group = db.join_group_by_invite(client, user["id"], invite_code)
                st.session_state.current_group_id = group["id"]
                st.query_params.pop("invite", None)
                st.query_params["view"] = "home"
                return True, f"Entrou no grupo {group['name']} 💖"
            except Exception:
                pass
        _select_first_available_group(client)
        return True, "Entrou 💖"
    except ValueError:
        st.session_state.login_fail_count += 1
        if st.session_state.login_fail_count >= MAX_LOGIN_ATTEMPTS:
            st.session_state.login_locked_until = time.time() + LOCK_SECONDS
        return False, "Nome de usuário ou senha inválidos."
    except Exception as exc:
        if get_config().debug_auth:
            return False, f"Erro técnico no login: {exc}"
        return False, "Não consegui entrar agora. Confira as secrets e se as migrations foram executadas."


def _select_first_available_group(client=None) -> None:
    if not st.session_state.get("app_user"):
        st.session_state.current_group_id = None
        return
    client = client or get_client()
    groups = db.list_my_groups(client, st.session_state.app_user["id"])
    current = st.session_state.get("current_group_id")
    if current and any(g["id"] == current for g in groups):
        return
    st.session_state.current_group_id = groups[0]["id"] if groups else None


def logout() -> None:
    token = get_remember_token()
    try:
        if token:
            db.revoke_persistent_token(get_client(), token)
    except Exception:
        pass
    clear_remember_token()
    for key in ("app_user", "current_group_id"):
        st.session_state[key] = None
    st.rerun()


def create_account(username: str, display_name: str, password: str, invite_code: str | None = None, avatar_emoji: str = "💌") -> tuple[bool, str]:
    try:
        username_normalized = validate_username(username)
        password = validate_password(password)
        if not (display_name or "").strip():
            raise ValueError("Escolha um nome para aparecer no grupo.")
        client = get_client()
        first = db.app_user_count(client) == 0
        if db.get_user_by_username(client, username_normalized):
            raise ValueError("Esse nome de usuário já existe.")
        if not first and not (invite_code or "").strip():
            raise ValueError("Para criar conta, use o código de convite de um grupo.")
        if not first and not db.find_group_by_invite(client, invite_code or ""):
            raise ValueError("Código de convite inválido ou expirado.")
        user = db.create_app_user(client, username_normalized, display_name, hash_password(password), avatar_emoji=avatar_emoji or "💌")
        if first:
            groups = db.create_default_groups_for_first_user(client, user["id"])
            msg = f"Primeiro usuário criado. Também criei {len(groups)} grupos iniciais para você."
        else:
            group = db.join_group_by_invite(client, user["id"], invite_code or "")
            msg = f"Conta criada e adicionada ao grupo {group['name']}."
        st.session_state.app_user = _session_user(user)
        _persist_login(client, user["id"])
        _select_first_available_group(client)
        return True, msg
    except Exception as exc:
        if get_config().debug_auth:
            return False, f"Erro ao criar conta: {exc}"
        return False, str(exc)


def require_auth() -> None:
    if not is_logged_in():
        st.warning("Entre para acessar este presente privado.")
        st.stop()


def require_group() -> None:
    require_auth()
    if not st.session_state.get("current_group_id"):
        st.info("Você ainda não está em nenhum grupo. Crie um grupo ou entre com um convite.")
        st.stop()


def render_auth_page() -> None:
    from src import ui

    cfg = get_config()
    ui.hero(
        "Entre no presente",
        "Um lugar fofo e privado para grupos guardarem fotos, vídeos, músicas e cartas que só abrem na hora certa.",
        "login simples",
    )

    errors = config_errors()
    if errors:
        st.error("Antes de entrar, configure o Supabase:")
        for err in errors:
            st.write(f"• {err}")
        st.code(
            'SUPABASE_URL = "https://SEU-PROJECT-REF.supabase.co"\n'
            'SUPABASE_SERVICE_ROLE_KEY = "SUA-SERVICE-ROLE-KEY"\n'
            'APP_NAME = "Presente Vii"',
            language="toml",
        )
        st.stop()

    client = get_client()
    try:
        first_user = db.app_user_count(client) == 0
    except Exception as exc:
        st.error("Não consegui acessar as tabelas. Rode as migrations SQL no Supabase primeiro.")
        if cfg.debug_auth:
            st.exception(exc)
        st.stop()

    login_tab, create_tab = st.tabs(["Entrar", "Criar conta"])

    with login_tab:
        st.markdown("<div class='soft-card'>", unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("Nome de usuário", placeholder="ex.: jorge")
            password = st.text_input("Senha", type="password")
            st.caption("Este navegador ficará conectado até você clicar em Sair.")
            submitted = st.form_submit_button("Entrar no presente")
            if submitted:
                ok, msg = login(username, password)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
        st.markdown("</div>", unsafe_allow_html=True)

    with create_tab:
        if first_user:
            st.info("Como ainda não existe usuário, a primeira conta vira dona dos grupos iniciais.")
        else:
            st.info("Peça para alguém do grupo te enviar o código de convite.")
        st.markdown("<div class='soft-card'>", unsafe_allow_html=True)
        with st.form("create_account_form"):
            display_name = st.text_input("Nome que aparece para os outros", placeholder="ex.: Jorge")
            username = st.text_input("Escolha um nome de usuário", placeholder="ex.: jorge")
            avatar_emoji = st.text_input("Emoji do perfil", value="💌", max_chars=3)
            password = st.text_input("Escolha uma senha", type="password")
            password_confirm = st.text_input("Repita a senha", type="password")
            invite_from_url = str(st.query_params.get("invite") or "").strip().upper()
            invite_code = ""
            if not first_user:
                invite_code = st.text_input("Código de convite", value=invite_from_url, placeholder="ex.: ABC123XYZ").upper()
            submitted = st.form_submit_button("Criar minha conta")
            if submitted:
                if password != password_confirm:
                    st.error("As senhas não são iguais.")
                else:
                    ok, msg = create_account(username, display_name, password, invite_code, avatar_emoji)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
        st.markdown("</div>", unsafe_allow_html=True)

    st.caption("Privado por convite. Sem email, sem cadastro público aberto e sem senha em texto puro. A persistência usa um token revogável salvo neste navegador.")
