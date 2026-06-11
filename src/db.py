from __future__ import annotations

import secrets
import time
from datetime import datetime
from typing import Any, Callable

import httpx
import streamlit as st
from supabase import Client

CONTENT_TABLES = [
    "timeline_entries",
    "places",
    "playlists",
    "open_when_letters",
    "media",
    "member_locations",
]

NETWORK_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadError,
    httpx.ReadTimeout,
    httpx.RemoteProtocolError,
    httpx.TransportError,
)


def execute_query(query, *, attempts: int = 3, base_delay: float = 0.35):
    """Execute one Supabase/PostgREST query with a small retry for transient Windows/network errors.

    The WinError 10035 case usually means the non-blocking socket could not finish immediately.
    Retrying after a short delay avoids crashing the Streamlit rerun.
    """
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            return query.execute()
        except NETWORK_EXCEPTIONS as exc:
            last_exc = exc
            if attempt == attempts - 1:
                raise
            time.sleep(base_delay * (2 ** attempt))
    if last_exc:
        raise last_exc
    return query.execute()


def safe_data(loader: Callable[[], Any], default: Any):
    try:
        return loader()
    except NETWORK_EXCEPTIONS as exc:
        st.warning(
            "O Supabase demorou para responder. Recarregue a página em alguns segundos. "
            f"Detalhe técnico: {type(exc).__name__}."
        )
        return default


def _data(response) -> list[dict[str, Any]]:
    return response.data or []


def one_or_none(response) -> dict[str, Any] | None:
    rows = response.data or []
    return rows[0] if rows else None


def new_invite_code() -> str:
    return secrets.token_urlsafe(8).replace("-", "").replace("_", "")[:10].upper()


def app_user_count(client: Client) -> int:
    result = execute_query(client.table("app_users").select("id").limit(1))
    return len(result.data or [])


def get_user_by_username(client: Client, username_normalized: str) -> dict[str, Any] | None:
    result = execute_query(
        client.table("app_users")
        .select("*")
        .eq("username_normalized", username_normalized)
        .eq("is_active", True)
        .limit(1)
    )
    return one_or_none(result)


def get_user_by_id(client: Client, user_id: str) -> dict[str, Any] | None:
    result = execute_query(
        client.table("app_users")
        .select("id, username, display_name, avatar_emoji, is_active, created_at")
        .eq("id", user_id)
        .limit(1)
    )
    return one_or_none(result)


def list_users_by_ids(client: Client, user_ids: list[str]) -> dict[str, dict[str, Any]]:
    ids = [uid for uid in dict.fromkeys(user_ids) if uid]
    if not ids:
        return {}
    result = execute_query(
        client.table("app_users")
        .select("id, username, display_name, avatar_emoji, is_active, created_at")
        .in_("id", ids)
    )
    return {row["id"]: row for row in (result.data or [])}


def create_app_user(client: Client, username: str, display_name: str, password_hash: str, avatar_emoji: str = "💌") -> dict[str, Any]:
    result = execute_query(
        client.table("app_users")
        .insert(
            {
                "username": username,
                "username_normalized": username.lower(),
                "display_name": display_name.strip() or username,
                "password_hash": password_hash,
                "avatar_emoji": avatar_emoji or "💌",
            }
        )
    )
    return result.data[0]


def mark_login(client: Client, user_id: str) -> None:
    execute_query(client.table("app_users").update({"last_login_at": datetime.utcnow().isoformat()}).eq("id", user_id))


def current_user() -> dict[str, Any]:
    user = st.session_state.get("app_user")
    if not user:
        raise RuntimeError("Usuário não autenticado.")
    return user


def current_user_id() -> str:
    return current_user()["id"]


def current_group_id() -> str:
    group_id = st.session_state.get("current_group_id")
    if not group_id:
        raise RuntimeError("Nenhum grupo selecionado.")
    return group_id


def set_current_group(group_id: str | None) -> None:
    st.session_state.current_group_id = group_id


def list_my_memberships(client: Client, user_id: str | None = None) -> list[dict[str, Any]]:
    user_id = user_id or current_user_id()

    # Query única: evita N+1 chamadas HTTP, que era a principal fonte do WinError 10035 no Windows.
    try:
        rows = _data(
            execute_query(
                client.table("group_members")
                .select("id, group_id, user_id, role, joined_at, group:groups(*)")
                .eq("user_id", user_id)
                .order("joined_at", desc=False)
            )
        )
        return [row for row in rows if row.get("group")]
    except Exception:
        # Fallback compatível caso o PostgREST não consiga resolver a relação embutida por algum cache antigo.
        rows = _data(
            execute_query(
                client.table("group_members")
                .select("id, group_id, user_id, role, joined_at")
                .eq("user_id", user_id)
                .order("joined_at", desc=False)
            )
        )
        group_ids = [row["group_id"] for row in rows]
        if not group_ids:
            return []
        groups_resp = execute_query(client.table("groups").select("*").in_("id", group_ids))
        groups_by_id = {g["id"]: g for g in (groups_resp.data or [])}
        memberships: list[dict[str, Any]] = []
        for row in rows:
            group = groups_by_id.get(row["group_id"])
            if group:
                memberships.append(dict(row) | {"group": group})
        return memberships


def list_my_groups(client: Client, user_id: str | None = None) -> list[dict[str, Any]]:
    return [m["group"] | {"member_role": m["role"]} for m in list_my_memberships(client, user_id)]


def get_group(client: Client, group_id: str | None = None) -> dict[str, Any] | None:
    group_id = group_id or current_group_id()
    result = execute_query(client.table("groups").select("*").eq("id", group_id).limit(1))
    return one_or_none(result)


def get_membership(client: Client, group_id: str | None = None, user_id: str | None = None) -> dict[str, Any] | None:
    group_id = group_id or current_group_id()
    user_id = user_id or current_user_id()
    result = execute_query(
        client.table("group_members")
        .select("*")
        .eq("group_id", group_id)
        .eq("user_id", user_id)
        .limit(1)
    )
    return one_or_none(result)


def is_group_member(client: Client, group_id: str | None = None, user_id: str | None = None) -> bool:
    return bool(get_membership(client, group_id, user_id))


def current_group_role(client: Client, group_id: str | None = None, user_id: str | None = None) -> str:
    membership = get_membership(client, group_id, user_id)
    return str((membership or {}).get("role") or "")


def can_manage_group(client: Client, group_id: str | None = None, user_id: str | None = None) -> bool:
    return current_group_role(client, group_id, user_id) in {"owner", "admin"}


def create_group(client: Client, name: str, description: str | None, created_by: str | None = None, theme_color: str = "verde") -> dict[str, Any]:
    created_by = created_by or current_user_id()
    code = new_invite_code()
    for _ in range(5):
        exists = one_or_none(execute_query(client.table("groups").select("id").eq("invite_code", code).limit(1)))
        if not exists:
            break
        code = new_invite_code()
    result = execute_query(
        client.table("groups")
        .insert(
            {
                "name": name.strip(),
                "description": (description or "").strip() or None,
                "theme_color": theme_color,
                "invite_code": code,
                "created_by": created_by,
            }
        )
    )
    group = result.data[0]
    execute_query(client.table("group_members").insert({"group_id": group["id"], "user_id": created_by, "role": "owner"}))
    return group


def create_default_groups_for_first_user(client: Client, user_id: str) -> list[dict[str, Any]]:
    defaults = [
        ("Nós dois", "O cantinho mais íntimo: datas, cartas e lembranças só de vocês dois.", "azul"),
        ("Família dela", "Momentos com a família dela, com carinho e cuidado.", "verde"),
        ("Minha família", "Fotos e histórias com a sua família.", "azul"),
        ("Todo mundo junto", "O grupo para juntar os dois mundos na mesma página.", "rosa"),
    ]
    return [create_group(client, name, desc, created_by=user_id, theme_color=color) for name, desc, color in defaults]


def find_group_by_invite(client: Client, invite_code: str) -> dict[str, Any] | None:
    code = (invite_code or "").strip().upper()
    if not code:
        return None
    result = execute_query(client.table("groups").select("*").eq("invite_code", code).eq("is_active", True).limit(1))
    return one_or_none(result)


def join_group_by_invite(client: Client, user_id: str, invite_code: str) -> dict[str, Any]:
    group = find_group_by_invite(client, invite_code)
    if not group:
        raise ValueError("Código de convite inválido ou expirado.")
    existing = get_membership(client, group["id"], user_id)
    if existing:
        return group
    execute_query(client.table("group_members").insert({"group_id": group["id"], "user_id": user_id, "role": "member"}))
    return group


def update_group(client: Client, group_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    result = execute_query(client.table("groups").update(payload).eq("id", group_id))
    return result.data[0]


def regenerate_invite_code(client: Client, group_id: str) -> str:
    code = new_invite_code()
    update_group(client, group_id, {"invite_code": code})
    return code


def list_group_members(client: Client, group_id: str | None = None) -> list[dict[str, Any]]:
    group_id = group_id or current_group_id()
    rows = _data(
        execute_query(
            client.table("group_members")
            .select("id, group_id, user_id, role, joined_at")
            .eq("group_id", group_id)
            .order("joined_at", desc=False)
        )
    )
    users_by_id = list_users_by_ids(client, [row["user_id"] for row in rows])
    return [row | {"user": users_by_id[row["user_id"]]} for row in rows if row.get("user_id") in users_by_id]


def update_member_role(client: Client, membership_id: str, role: str) -> None:
    if role not in {"admin", "member"}:
        raise ValueError("Papel inválido.")
    execute_query(client.table("group_members").update({"role": role}).eq("id", membership_id).neq("role", "owner"))


def remove_member(client: Client, membership_id: str) -> None:
    execute_query(client.table("group_members").delete().eq("id", membership_id).neq("role", "owner"))


def list_group_records(client: Client, table: str, order: str | None = None, desc: bool = False) -> list[dict[str, Any]]:
    query = client.table(table).select("*").eq("group_id", current_group_id())
    if order:
        query = query.order(order, desc=desc)
    result = execute_query(query)
    return result.data or []


def count_group_records(client: Client, table: str) -> int:
    result = execute_query(client.table(table).select("id", count="exact").eq("group_id", current_group_id()))
    return int(result.count or 0)


def get_record(client: Client, table: str, record_id: str) -> dict[str, Any] | None:
    result = execute_query(client.table(table).select("*").eq("group_id", current_group_id()).eq("id", record_id).limit(1))
    return one_or_none(result)


def create_record(client: Client, table: str, payload: dict[str, Any]) -> dict[str, Any]:
    payload = dict(payload)
    payload["group_id"] = current_group_id()
    payload.setdefault("created_by", current_user_id())
    result = execute_query(client.table(table).insert(payload))
    return result.data[0]


def update_record(client: Client, table: str, record_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    result = execute_query(client.table(table).update(payload).eq("group_id", current_group_id()).eq("id", record_id))
    return result.data[0]


def delete_record(client: Client, table: str, record_id: str) -> None:
    execute_query(client.table(table).delete().eq("group_id", current_group_id()).eq("id", record_id))


def user_can_edit_record(client: Client, record: dict[str, Any], table: str) -> bool:
    if table == "playlists" and is_group_member(client):
        return True
    return can_manage_group(client) or record.get("created_by") == current_user_id()


def user_can_delete_record(client: Client, record: dict[str, Any]) -> bool:
    return can_manage_group(client) or record.get("created_by") == current_user_id()


def get_media(client: Client, related_table: str, related_id: str | None = None) -> list[dict[str, Any]]:
    query = (
        client.table("media")
        .select("*")
        .eq("group_id", current_group_id())
        .eq("related_table", related_table)
        .order("sort_order")
    )
    if related_id:
        query = query.eq("related_id", related_id)
    else:
        query = query.is_("related_id", "null")
    result = execute_query(query)
    return result.data or []


def create_media_record(client: Client, payload: dict[str, Any]) -> dict[str, Any]:
    payload = dict(payload)
    payload["group_id"] = current_group_id()
    payload.setdefault("created_by", current_user_id())
    result = execute_query(client.table("media").insert(payload))
    return result.data[0]


def delete_media_record(client: Client, media_id: str) -> None:
    execute_query(client.table("media").delete().eq("group_id", current_group_id()).eq("id", media_id))


def list_visible_letters(client: Client) -> list[dict[str, Any]]:
    rows = list_group_records(client, "open_when_letters", order="created_at", desc=True)
    user_id = current_user_id()
    manager = can_manage_group(client)
    visible: list[dict[str, Any]] = []
    for row in rows:
        if not row.get("is_active", True) and row.get("created_by") != user_id and not manager:
            continue
        audience = row.get("audience_type") or "all"
        if audience == "all" or row.get("recipient_user_id") == user_id or row.get("created_by") == user_id or manager:
            visible.append(row)
    return visible


def recipient_label(client: Client, recipient_user_id: str | None) -> str:
    if not recipient_user_id:
        return "todos"
    user = get_user_by_id(client, recipient_user_id)
    return (user or {}).get("display_name") or "alguém do grupo"


def group_counts(client: Client) -> dict[str, int]:
    return {
        "momentos": count_group_records(client, "timeline_entries"),
        "lugares": count_group_records(client, "places"),
        "playlists": count_group_records(client, "playlists"),
        "cartas": len(list_visible_letters(client)),
        "membros": len(list_group_members(client)),
    }


def export_group(client: Client) -> dict[str, Any]:
    group = get_group(client)
    members = []
    for item in list_group_members(client):
        user = item.get("user") or {}
        members.append(
            {
                "role": item.get("role"),
                "joined_at": item.get("joined_at"),
                "user": {
                    "id": user.get("id"),
                    "username": user.get("username"),
                    "display_name": user.get("display_name"),
                    "avatar_emoji": user.get("avatar_emoji"),
                },
            }
        )
    data: dict[str, Any] = {"group": group, "members": members}
    for table in CONTENT_TABLES:
        data[table] = list_group_records(client, table, order="created_at", desc=False)
    return data


def delete_group_content(client: Client) -> None:
    for table in ["media", "member_locations", "open_when_letters", "playlists", "places", "timeline_entries"]:
        execute_query(client.table(table).delete().eq("group_id", current_group_id()))


def list_moments_for_place(client: Client, place_id: str) -> list[dict[str, Any]]:
    """Lista momentos da timeline vinculados a um lugar do grupo atual."""
    result = execute_query(
        client.table("timeline_entries")
        .select("*")
        .eq("group_id", current_group_id())
        .eq("place_id", place_id)
        .order("occurred_on", desc=True)
    )
    return result.data or []



def list_member_locations(client: Client, group_id: str | None = None) -> list[dict[str, Any]]:
    """Lista as localizações compartilhadas pelos membros no grupo atual."""
    group_id = group_id or current_group_id()
    result = execute_query(
        client.table("member_locations")
        .select("*")
        .eq("group_id", group_id)
        .order("updated_at", desc=True)
    )
    return result.data or []


def get_my_member_location(client: Client, group_id: str | None = None, user_id: str | None = None) -> dict[str, Any] | None:
    group_id = group_id or current_group_id()
    user_id = user_id or current_user_id()
    result = execute_query(
        client.table("member_locations")
        .select("*")
        .eq("group_id", group_id)
        .eq("user_id", user_id)
        .limit(1)
    )
    return one_or_none(result)


def upsert_member_location(
    client: Client,
    *,
    latitude: float,
    longitude: float,
    address: str | None = None,
    description: str | None = None,
    group_id: str | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Cria ou atualiza a localização compartilhada do usuário no grupo."""
    group_id = group_id or current_group_id()
    user_id = user_id or current_user_id()
    payload = {
        "group_id": group_id,
        "user_id": user_id,
        "latitude": latitude,
        "longitude": longitude,
        "address": address,
        "description": description,
        "updated_at": datetime.utcnow().isoformat(),
    }
    result = execute_query(
        client.table("member_locations")
        .upsert(payload, on_conflict="group_id,user_id")
    )
    return result.data[0]


def delete_my_member_location(client: Client, group_id: str | None = None, user_id: str | None = None) -> None:
    group_id = group_id or current_group_id()
    user_id = user_id or current_user_id()
    execute_query(
        client.table("member_locations")
        .delete()
        .eq("group_id", group_id)
        .eq("user_id", user_id)
    )
