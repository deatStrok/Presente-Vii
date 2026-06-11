from __future__ import annotations

import html
from datetime import date
from typing import Any

import folium
from folium.plugins import Geocoder
import streamlit as st
from streamlit_folium import st_folium

from src import db, storage, ui
from src.auth import require_group
from src.supabase_client import get_client
from src.validators import date_or_none, parse_tags, tags_to_text

MEDIA_TYPES = ["jpg", "jpeg", "png", "webp", "gif", "mp4", "webm", "mov"]
DEFAULT_MAP_CENTER = [-12.9714, -38.5014]  # Salvador/BA como ponto inicial do MVP


def _upload_many(client, files, related_table: str, related_id: str) -> None:
    for idx, f in enumerate(files or []):
        storage.upload_media(client, f, related_table, related_id, sort_order=idx)


def _coords_text(lat: float | str | None, lng: float | str | None) -> str:
    if lat is None or lng is None:
        return "sem coordenadas"
    try:
        return f"{float(lat):.6f}, {float(lng):.6f}"
    except Exception:
        return f"{lat}, {lng}"


def _escape(value: Any) -> str:
    return html.escape(str(value or ""))


def _parse_geocoder_result(result: dict | None) -> dict[str, Any] | None:
    """Normaliza o retorno do folium/leaflet-control-geocoder.

    O st_folium pode retornar estruturas levemente diferentes conforme a versão.
    Esta função aceita os formatos mais comuns: center.lat/lng, lat/lng diretos,
    properties.display_name/name e bbox/boundingbox.
    """
    if not result or not isinstance(result, dict):
        return None

    center = result.get("center") or {}
    lat = center.get("lat") if isinstance(center, dict) else None
    lng = center.get("lng") if isinstance(center, dict) else None

    if lat is None:
        lat = result.get("lat") or result.get("latitude")
    if lng is None:
        lng = result.get("lng") or result.get("lon") or result.get("longitude")

    geometry = result.get("geometry") or {}
    if isinstance(geometry, dict):
        coordinates = geometry.get("coordinates") or []
        if (lat is None or lng is None) and isinstance(coordinates, list) and len(coordinates) >= 2:
            lng = coordinates[0]
            lat = coordinates[1]

    try:
        lat_f = float(lat)
        lng_f = float(lng)
    except Exception:
        return None

    props = result.get("properties") or {}
    if not isinstance(props, dict):
        props = {}

    name = (
        result.get("name")
        or props.get("display_name")
        or props.get("name")
        or props.get("label")
        or props.get("formatted")
        or result.get("display_name")
        or "Resultado encontrado"
    )

    address = props.get("display_name") or props.get("label") or props.get("formatted") or name

    return {
        "name": str(name),
        "address": str(address),
        "latitude": lat_f,
        "longitude": lng_f,
        "raw": result,
    }


def _place_popup(client, place: dict, users_by_id: dict[str, dict]) -> str:
    media = db.get_media(client, "places", place["id"])
    image = next((x for x in media if x.get("type") == "image"), None)
    img_html = ""
    if image:
        url = storage.signed_url(client, image["storage_path"])
        if url:
            img_html = f"<img src='{html.escape(url)}' style='width:210px;max-height:140px;object-fit:cover;border-radius:14px;margin-bottom:8px;' />"

    creator = users_by_id.get(place.get("created_by") or "") or {}
    creator_name = creator.get("display_name") or "alguém do grupo"
    description = place.get("description") or "Sem descrição."
    address = place.get("address") or "Endereço não informado"
    location_text = _coords_text(place.get("latitude"), place.get("longitude"))

    return f"""
    <div style='width:250px;font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#143D35;'>
      {img_html}
      <strong style='font-size:16px;'>{_escape(place.get('title'))}</strong><br />
      <small><b>Data:</b> {_escape(ui.fmt_date(place.get('visited_on')))}</small><br />
      <small><b>Criado por:</b> {_escape(creator_name)}</small>
      <p style='margin:8px 0 6px;'>{_escape(description)}</p>
      <small><b>Localização:</b> {_escape(address)}</small><br />
      <small><b>Coordenadas:</b> {_escape(location_text)}</small>
    </div>
    """


def _member_popup(member_location: dict, users_by_id: dict[str, dict]) -> str:
    user = users_by_id.get(member_location.get("user_id") or "") or {}
    display_name = user.get("display_name") or user.get("username") or "Pessoa do grupo"
    emoji = user.get("avatar_emoji") or "🫶"
    description = member_location.get("description") or "Sem descrição."
    address = member_location.get("address") or "Endereço não informado"
    location_text = _coords_text(member_location.get("latitude"), member_location.get("longitude"))

    return f"""
    <div style='width:240px;font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#143D35;'>
      <strong style='font-size:16px;'>{_escape(emoji)} {_escape(display_name)}</strong><br />
      <small><b>Atualizado em:</b> {_escape(ui.fmt_datetime(member_location.get('updated_at')))}</small>
      <p style='margin:8px 0 6px;'>{_escape(description)}</p>
      <small><b>Localização:</b> {_escape(address)}</small><br />
      <small><b>Coordenadas:</b> {_escape(location_text)}</small>
    </div>
    """


def _build_map(client, places: list[dict], member_locations: list[dict]) -> folium.Map:
    all_points: list[list[float]] = []
    for p in places:
        all_points.append([float(p["latitude"]), float(p["longitude"])])
    for loc in member_locations:
        all_points.append([float(loc["latitude"]), float(loc["longitude"])])

    if all_points:
        avg_lat = sum(p[0] for p in all_points) / len(all_points)
        avg_lng = sum(p[1] for p in all_points) / len(all_points)
        zoom = 13 if len(all_points) == 1 else 11
        m = folium.Map(location=[avg_lat, avg_lng], zoom_start=zoom, tiles="CartoDB positron", control_scale=True)
    else:
        m = folium.Map(location=DEFAULT_MAP_CENTER, zoom_start=11, tiles="CartoDB positron", control_scale=True)

    # Caixa de busca de endereços dentro do mapa. Usa Nominatim/OpenStreetMap.
    Geocoder(collapsed=False, add_marker=True, position="topleft", placeholder="Pesquisar rua, número, bairro...").add_to(m)

    user_ids = [p.get("created_by") for p in places if p.get("created_by")] + [loc.get("user_id") for loc in member_locations if loc.get("user_id")]
    users_by_id = db.list_users_by_ids(client, user_ids)

    for place in places:
        folium.Marker(
            [float(place["latitude"]), float(place["longitude"])],
            popup=folium.Popup(_place_popup(client, place, users_by_id), max_width=280),
            tooltip=f"📍 {place['title']}",
            icon=folium.Icon(color="green", icon="heart", prefix="fa"),
        ).add_to(m)

    for loc in member_locations:
        user = users_by_id.get(loc.get("user_id") or "") or {}
        label = user.get("display_name") or user.get("username") or "Pessoa do grupo"
        folium.Marker(
            [float(loc["latitude"]), float(loc["longitude"])],
            popup=folium.Popup(_member_popup(loc, users_by_id), max_width=270),
            tooltip=f"🫶 {label}",
            icon=folium.Icon(color="pink", icon="user", prefix="fa"),
        ).add_to(m)

    if len(all_points) > 1:
        m.fit_bounds(all_points, padding=(28, 28))

    return m


def _render_map(client, places: list[dict], member_locations: list[dict]) -> dict | None:
    st.markdown("<div class='soft-card'>", unsafe_allow_html=True)
    st.markdown("### 🗺️ Nosso mapa")
    st.caption("Use a busca no canto superior esquerdo do mapa para pesquisar rua, número, bairro ou cidade. Clique nos marcadores para ver data, descrição e localização.")
    map_data = st_folium(
        _build_map(client, places, member_locations),
        height=560,
        use_container_width=True,
        returned_objects=["last_clicked", "last_geocoder_result"],
    )
    st.markdown("</div>", unsafe_allow_html=True)
    return map_data


def _render_search_result(client, geocoded: dict | None) -> None:
    if not geocoded:
        return

    st.markdown("<div class='soft-card'>", unsafe_allow_html=True)
    st.markdown("### Resultado da busca")
    st.write(geocoded["address"])
    st.caption(f"Latitude {geocoded['latitude']:.6f} · Longitude {geocoded['longitude']:.6f}")
    c1, c2 = st.columns(2)
    if c1.button("Usar no formulário de lugar", use_container_width=True):
        st.session_state.place_prefill = geocoded
        st.toast("Resultado copiado para o formulário de novo lugar.")
        st.rerun()
    if c2.button("Usar como minha localização", use_container_width=True):
        st.session_state.my_location_prefill = geocoded
        st.toast("Resultado copiado para o formulário de localização.")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _default_prefill(key: str) -> dict[str, Any]:
    return st.session_state.get(key) or {}


def render() -> None:
    require_group()
    client = get_client()
    ui.hero("Mapa dos lugares", "Pesquise endereços, guarde lugares especiais e veja onde cada pessoa do grupo marcou sua localização.", "lugares")

    places = db.list_group_records(client, "places", order="visited_on", desc=True)
    member_locations = db.list_member_locations(client)
    map_data = _render_map(client, places, member_locations)

    geocoded = _parse_geocoder_result((map_data or {}).get("last_geocoder_result"))
    if geocoded:
        st.session_state.map_last_search = geocoded
    else:
        geocoded = st.session_state.get("map_last_search")
    _render_search_result(client, geocoded)

    if map_data and map_data.get("last_clicked"):
        clicked = map_data["last_clicked"]
        st.caption(
            f"Clique detectado: latitude {clicked['lat']:.6f}, longitude {clicked['lng']:.6f}. "
            "Você pode copiar esses valores para cadastrar um lugar ou atualizar sua localização."
        )

    st.subheader("Minha localização no grupo")
    my_location = db.get_my_member_location(client)
    loc_prefill = _default_prefill("my_location_prefill")
    with st.form("share_my_location"):
        description = st.text_area(
            "Descrição",
            value=(my_location or {}).get("description") or "",
            placeholder="ex.: Estou aqui hoje / nossa casa / ponto de encontro",
            height=80,
        )
        address = st.text_input(
            "Endereço ou referência",
            value=str(loc_prefill.get("address") or (my_location or {}).get("address") or ""),
            placeholder="ex.: Rua X, 123 - Salvador",
        )
        c_lat, c_lng = st.columns(2)
        latitude = c_lat.number_input(
            "Latitude",
            value=float(loc_prefill.get("latitude") or (my_location or {}).get("latitude") or DEFAULT_MAP_CENTER[0]),
            format="%.6f",
        )
        longitude = c_lng.number_input(
            "Longitude",
            value=float(loc_prefill.get("longitude") or (my_location or {}).get("longitude") or DEFAULT_MAP_CENTER[1]),
            format="%.6f",
        )
        submitted = st.form_submit_button("Salvar minha localização")
        if submitted:
            db.upsert_member_location(
                client,
                latitude=float(latitude),
                longitude=float(longitude),
                address=address.strip() or None,
                description=description.strip() or None,
            )
            st.session_state.pop("my_location_prefill", None)
            st.success("Sua localização foi salva para este grupo.")
            st.rerun()
    if my_location and st.button("Remover minha localização deste grupo"):
        db.delete_my_member_location(client)
        st.success("Sua localização foi removida.")
        st.rerun()

    st.subheader("Adicionar lugar")
    place_prefill = _default_prefill("place_prefill")
    with st.expander("Guardar um lugar no mapa", expanded=bool(place_prefill)):
        with st.form("new_place"):
            title = st.text_input("Nome do lugar", value=str(place_prefill.get("name") or ""), placeholder="ex.: Praia do Forte")
            description = st.text_area("Descrição", placeholder="Por que esse lugar importa?", height=100)
            address = st.text_input("Endereço ou referência", value=str(place_prefill.get("address") or ""), placeholder="ex.: Rua X, 123 - bairro")
            c1, c2 = st.columns(2)
            latitude = c1.number_input("Latitude", value=float(place_prefill.get("latitude") or DEFAULT_MAP_CENTER[0]), format="%.6f")
            longitude = c2.number_input("Longitude", value=float(place_prefill.get("longitude") or DEFAULT_MAP_CENTER[1]), format="%.6f")
            visited_on = st.date_input("Data", value=date.today())
            tags = st.text_input("Tags", placeholder="viagem, almoço, família")
            files = st.file_uploader("Fotos ou vídeos do lugar", type=MEDIA_TYPES, accept_multiple_files=True)
            submitted = st.form_submit_button("Guardar lugar")
            if submitted:
                if not title.strip():
                    st.error("Nome do lugar é obrigatório.")
                else:
                    saved = db.create_record(
                        client,
                        "places",
                        {
                            "title": title.strip(),
                            "description": description.strip() or None,
                            "address": address.strip() or None,
                            "latitude": float(latitude),
                            "longitude": float(longitude),
                            "visited_on": date_or_none(visited_on),
                            "tags": parse_tags(tags),
                        },
                    )
                    _upload_many(client, files, "places", saved["id"])
                    st.session_state.pop("place_prefill", None)
                    st.success("Lugar guardado.")
                    st.rerun()

    if not places and not member_locations:
        st.info("Nenhum lugar ou localização cadastrado ainda. Pesquise um endereço no mapa ou compartilhe sua localização para aparecer o primeiro marcador.")
        return

    if places:
        st.subheader("Lista de lugares")
        for place in places:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='meta'>{ui.fmt_date(place.get('visited_on'))}</div>", unsafe_allow_html=True)
            st.markdown(f"### {place['title']}")
            if place.get("address"):
                st.markdown(f"<span class='place-chip'>📍 {html.escape(place['address'])}</span>", unsafe_allow_html=True)
            st.caption(f"Coordenadas: {_coords_text(place.get('latitude'), place.get('longitude'))}")
            if place.get("description"):
                st.write(place["description"])
            if place.get("tags"):
                st.markdown(ui.tags_html(place.get("tags")), unsafe_allow_html=True)
            media = db.get_media(client, "places", place["id"])
            ui.render_media_gallery(client, media)
            related_moments = db.list_moments_for_place(client, place["id"])
            if related_moments:
                st.markdown("#### Momentos neste lugar")
                for moment in related_moments[:5]:
                    st.markdown(f"- **{moment.get('title')}** · {ui.fmt_date(moment.get('occurred_on'))}")
            st.markdown("</div>", unsafe_allow_html=True)

            if db.user_can_edit_record(client, place, "places"):
                with st.expander(f"Editar lugar: {place['title']}"):
                    with st.form(f"edit_place_{place['id']}"):
                        title = st.text_input("Nome", value=place.get("title") or "", key=f"pl_title_{place['id']}")
                        description = st.text_area("Descrição", value=place.get("description") or "", height=100, key=f"pl_desc_{place['id']}")
                        address = st.text_input("Endereço ou referência", value=place.get("address") or "", key=f"pl_address_{place['id']}")
                        c1, c2 = st.columns(2)
                        latitude = c1.number_input("Latitude", value=float(place["latitude"]), format="%.6f", key=f"pl_lat_{place['id']}")
                        longitude = c2.number_input("Longitude", value=float(place["longitude"]), format="%.6f", key=f"pl_lng_{place['id']}")
                        visited_on = st.date_input("Data", value=date.fromisoformat(place["visited_on"]) if place.get("visited_on") else date.today(), key=f"pl_date_{place['id']}")
                        tags = st.text_input("Tags", value=tags_to_text(place.get("tags")), key=f"pl_tags_{place['id']}")
                        files = st.file_uploader("Adicionar mais mídia", type=MEDIA_TYPES, accept_multiple_files=True, key=f"pl_files_{place['id']}")
                        submitted = st.form_submit_button("Salvar lugar")
                        if submitted:
                            db.update_record(
                                client,
                                "places",
                                place["id"],
                                {
                                    "title": title.strip() or place["title"],
                                    "description": description.strip() or None,
                                    "address": address.strip() or None,
                                    "latitude": float(latitude),
                                    "longitude": float(longitude),
                                    "visited_on": date_or_none(visited_on),
                                    "tags": parse_tags(tags),
                                },
                            )
                            _upload_many(client, files, "places", place["id"])
                            st.success("Lugar atualizado.")
                            st.rerun()
                    if db.user_can_delete_record(client, place) and st.button("Apagar lugar", key=f"del_place_{place['id']}"):
                        for item in media:
                            storage.remove_media(client, item)
                        db.delete_record(client, "places", place["id"])
                        st.success("Lugar apagado.")
                        st.rerun()

    if member_locations:
        st.subheader("Localizações compartilhadas")
        users_by_id = db.list_users_by_ids(client, [loc.get("user_id") for loc in member_locations if loc.get("user_id")])
        for loc in member_locations:
            user = users_by_id.get(loc.get("user_id") or "") or {}
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"### {user.get('avatar_emoji', '🫶')} {user.get('display_name') or user.get('username') or 'Pessoa do grupo'}")
            st.caption(f"Atualizado em {ui.fmt_datetime(loc.get('updated_at'))}")
            if loc.get("description"):
                st.write(loc["description"])
            st.write(f"📍 {loc.get('address') or 'Endereço não informado'}")
            st.caption(f"Coordenadas: {_coords_text(loc.get('latitude'), loc.get('longitude'))}")
            st.markdown("</div>", unsafe_allow_html=True)
