from __future__ import annotations

import html
import json
from datetime import date, datetime
from typing import Iterable

import streamlit as st
import streamlit.components.v1 as components

from src import storage


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
          --blue-deep: #0B3D5C;
          --blue-soft: #7EC8F2;
          --green-deep: #143D35;
          --green-soft: #DDEFE8;
          --pink: #F28AB2;
          --pink-soft: #FFE0EC;
          --cream: #FFF8F5;
          --paper: rgba(255, 255, 255, 0.78);
          --paper-strong: rgba(255, 255, 255, 0.92);
          --ink: #123D36;
          --muted: #6F7471;
          --line: rgba(20, 61, 53, .15);
          --shadow: 0 18px 50px rgba(11, 61, 92, .12);
          --radius-xl: 30px;
          --radius-lg: 22px;
          --radius-md: 16px;
        }

        html, body, [data-testid="stAppViewContainer"] {
          background:
            radial-gradient(circle at 8% 8%, rgba(126, 200, 242, .35), transparent 28%),
            radial-gradient(circle at 88% 12%, rgba(242, 138, 178, .32), transparent 30%),
            radial-gradient(circle at 50% 88%, rgba(221, 239, 232, .75), transparent 34%),
            linear-gradient(135deg, #FFF8F5 0%, #F7FBFF 45%, #FFF3F8 100%);
          color: var(--ink);
        }

        .block-container {
          max-width: 1180px;
          padding-top: 1.25rem;
          padding-bottom: 5rem;
        }

        [data-testid="stSidebar"] {
          background: linear-gradient(180deg, rgba(20,61,53,.98), rgba(11,61,92,.96));
          color: white;
        }
        [data-testid="stSidebar"] * { color: rgba(255,255,255,.94) !important; }
        [data-testid="stSidebar"] [data-baseweb="select"] * { color: var(--ink) !important; }
        [data-testid="stSidebar"] input { color: var(--ink) !important; }

        h1, h2, h3 { letter-spacing: -.03em; }
        h1 { font-size: clamp(2.4rem, 7vw, 5.5rem) !important; line-height: .95 !important; }
        h2 { font-size: clamp(1.7rem, 4vw, 3rem) !important; }
        h3 { font-size: clamp(1.15rem, 2vw, 1.55rem) !important; }
        p, li, label, .stMarkdown { font-size: clamp(.98rem, 1.3vw, 1.06rem); }

        .hero {
          position: relative;
          overflow: hidden;
          padding: clamp(1.4rem, 4vw, 3rem);
          border-radius: var(--radius-xl);
          border: 1px solid rgba(20,61,53,.13);
          background:
            linear-gradient(135deg, rgba(255,255,255,.92), rgba(255,224,236,.62)),
            radial-gradient(circle at 85% 18%, rgba(126,200,242,.32), transparent 28%);
          box-shadow: var(--shadow);
          margin-bottom: 1.2rem;
        }
        .hero::after {
          content: "♡";
          position: absolute;
          right: clamp(1rem, 3vw, 2rem);
          top: clamp(.5rem, 2vw, 1rem);
          font-size: clamp(3rem, 12vw, 8rem);
          color: rgba(242,138,178,.22);
          transform: rotate(-12deg);
        }
        .hero-kicker {
          color: var(--blue-deep);
          font-weight: 800;
          letter-spacing: .18em;
          text-transform: uppercase;
          font-size: .75rem;
          margin-bottom: .7rem;
        }
        .hero-subtitle {
          max-width: 760px;
          color: #35544E;
          font-size: clamp(1.02rem, 2vw, 1.25rem);
          line-height: 1.6;
        }

        .soft-card, .card, .letter-card {
          border: 1px solid var(--line);
          background: var(--paper);
          backdrop-filter: blur(14px);
          box-shadow: 0 14px 38px rgba(11,61,92,.10);
          border-radius: var(--radius-lg);
          padding: clamp(1rem, 2.5vw, 1.35rem);
          margin: .75rem 0 1rem;
        }
        .card:hover, .letter-card:hover {
          transform: translateY(-1px);
          box-shadow: 0 18px 44px rgba(11,61,92,.14);
          transition: .18s ease;
        }
        .letter-card {
          background:
            linear-gradient(145deg, rgba(255,255,255,.96), rgba(255,224,236,.72)),
            repeating-linear-gradient(0deg, transparent, transparent 28px, rgba(242,138,178,.08) 29px);
          position: relative;
        }
        .letter-card::before {
          content: "✉";
          position: absolute;
          right: 18px;
          top: 12px;
          color: rgba(242,138,178,.40);
          font-size: 2rem;
        }
        .meta {
          color: var(--muted);
          font-weight: 700;
          letter-spacing: .04em;
          text-transform: uppercase;
          font-size: .78rem;
        }
        .tag {
          display: inline-flex;
          align-items: center;
          padding: .25rem .62rem;
          margin: .22rem .25rem .1rem 0;
          border-radius: 999px;
          background: linear-gradient(135deg, var(--pink-soft), rgba(126,200,242,.22));
          border: 1px solid rgba(242,138,178,.24);
          color: var(--green-deep);
          font-weight: 700;
          font-size: .78rem;
        }
        .chip {
          display: inline-flex;
          align-items: center;
          gap: .4rem;
          padding: .45rem .75rem;
          border-radius: 999px;
          border: 1px solid rgba(255,255,255,.38);
          background: rgba(255,255,255,.12);
          margin: .15rem .15rem .15rem 0;
          font-size: .9rem;
          font-weight: 700;
        }
        .cute-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          gap: 1rem;
          margin: 1rem 0;
        }
        .mini-stat {
          border-radius: 22px;
          background: rgba(255,255,255,.72);
          border: 1px solid var(--line);
          padding: 1rem;
          min-height: 96px;
        }
        .mini-stat strong {
          display: block;
          font-size: 2rem;
          color: var(--blue-deep);
          line-height: 1.1;
        }
        .mini-stat span { color: var(--muted); font-weight: 700; }

        .nav-card-grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 1rem;
          margin: 1rem 0 1.35rem;
        }
        .nav-card {
          display: block;
          text-decoration: none !important;
          color: var(--ink) !important;
          min-height: 122px;
          padding: 1.05rem 1rem;
          border-radius: 24px;
          border: 1px solid var(--line);
          background:
            linear-gradient(145deg, rgba(255,255,255,.84), rgba(255,224,236,.46)),
            radial-gradient(circle at 90% 5%, rgba(126,200,242,.22), transparent 34%);
          box-shadow: 0 14px 32px rgba(11,61,92,.10);
          transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
        }
        .nav-card:hover {
          transform: translateY(-2px);
          border-color: rgba(242,138,178,.45);
          box-shadow: 0 18px 44px rgba(242,138,178,.18);
        }
        .nav-card .nav-card-icon {
          font-size: 1.45rem;
          line-height: 1;
          margin-bottom: .42rem;
        }
        .nav-card strong {
          display: block;
          font-size: clamp(1.75rem, 4vw, 2.35rem);
          color: var(--blue-deep);
          line-height: 1;
          letter-spacing: -.04em;
        }
        .nav-card span {
          display: block;
          color: var(--green-deep);
          font-weight: 850;
          margin-top: .25rem;
        }
        .nav-card small {
          display: block;
          margin-top: .45rem;
          color: var(--muted);
          font-size: .82rem;
          line-height: 1.25;
        }
        .letter-body {
          font-size: clamp(1.08rem, 2vw, 1.28rem);
          line-height: 1.85;
          color: #203F39;
          white-space: pre-wrap;
        }
        .unlock-box {
          border-radius: 20px;
          padding: 1rem;
          background: linear-gradient(135deg, rgba(20,61,53,.08), rgba(242,138,178,.16));
          border: 1px dashed rgba(20,61,53,.28);
          color: var(--green-deep);
          font-weight: 700;
        }
        .stButton > button, .stDownloadButton > button, .stLinkButton > a {
          border-radius: 999px !important;
          border: 1px solid rgba(20,61,53,.18) !important;
          background: linear-gradient(135deg, var(--green-deep), var(--blue-deep)) !important;
          color: white !important;
          font-weight: 800 !important;
          box-shadow: 0 10px 25px rgba(11,61,92,.16);
        }
        .stButton > button:hover, .stDownloadButton > button:hover, .stLinkButton > a:hover {
          border-color: var(--pink) !important;
          box-shadow: 0 12px 30px rgba(242,138,178,.23);
        }
        input, textarea, [data-baseweb="select"] > div {
          border-radius: 16px !important;
        }
        [data-testid="stMetric"] {
          background: rgba(255,255,255,.74);
          border: 1px solid var(--line);
          border-radius: 20px;
          padding: .85rem 1rem;
        }
        .media-caption { color: var(--muted); font-size: .86rem; margin-top: -.4rem; }

        @media (max-width: 760px) {
          .block-container { padding-left: .85rem; padding-right: .85rem; padding-top: .6rem; }
          .hero { border-radius: 24px; padding: 1.2rem; }
          .soft-card, .card, .letter-card { border-radius: 20px; padding: 1rem; }
          .nav-card-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .75rem; }
          .nav-card { min-height: 116px; padding: .95rem .82rem; border-radius: 22px; }
          .nav-card .nav-card-icon { font-size: 1.25rem; }
          .nav-card small { font-size: .76rem; }
          .stButton > button, .stDownloadButton > button, .stLinkButton > a { width: 100%; }
        }

        @media (min-width: 761px) and (max-width: 1050px) {
          .nav-card-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str | None = None, kicker: str | None = None) -> None:
    st.markdown(
        f"""
        <section class="hero">
          <div class="hero-kicker">{html.escape(kicker or 'presente privado')}</div>
          <h1>{html.escape(title)}</h1>
          {f'<div class="hero-subtitle">{html.escape(subtitle)}</div>' if subtitle else ''}
        </section>
        """,
        unsafe_allow_html=True,
    )


def card(title: str, body: str | None = None, meta: str | None = None, tags: Iterable[str] | None = None, letter: bool = False) -> None:
    klass = "letter-card" if letter else "card"
    st.markdown(f"<div class='{klass}'>", unsafe_allow_html=True)
    if meta:
        st.markdown(f"<div class='meta'>{html.escape(meta)}</div>", unsafe_allow_html=True)
    st.markdown(f"### {html.escape(title)}")
    if body:
        st.write(body)
    if tags:
        st.markdown(tags_html(tags), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def tags_html(tags: Iterable[str] | None) -> str:
    if not tags:
        return ""
    return "".join(f"<span class='tag'>#{html.escape(str(tag))}</span>" for tag in tags if str(tag).strip())


def chip(label: str) -> str:
    return f"<span class='chip'>{html.escape(label)}</span>"


def fmt_date(value: str | date | None) -> str:
    if not value:
        return "sem data"
    try:
        if isinstance(value, date):
            dt = value
        else:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return str(value)


def parse_datetime(value: str | datetime | None) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def fmt_datetime(value: str | datetime | None) -> str:
    dt = parse_datetime(value)
    if not dt:
        return "sem data"
    return dt.strftime("%d/%m/%Y às %H:%M")


def is_unlocked(unlock_at: str | datetime | None) -> bool:
    dt = parse_datetime(unlock_at)
    if not dt:
        return True
    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    return now >= dt


def render_stats(stats: dict[str, int]) -> None:
    st.markdown("<div class='cute-grid'>" + "".join(
        f"<div class='mini-stat'><strong>{value}</strong><span>{html.escape(label)}</span></div>" for label, value in stats.items()
    ) + "</div>", unsafe_allow_html=True)


def render_nav_cards(cards: list[dict[str, object]]) -> None:
    """Renderiza navegação como botões Streamlit.

    Evita links HTML com href, porque eles recarregam a página inteira e podem
    derrubar a sessão do Streamlit. Os botões alteram st.query_params no servidor
    e preservam st.session_state.
    """
    rows = [cards[i : i + 2] for i in range(0, len(cards), 2)]
    for row_index, row in enumerate(rows):
        cols = st.columns(2, gap="medium")
        for col_index, card in enumerate(row):
            label = str(card.get("label") or "")
            value = str(card.get("value") or 0)
            icon = str(card.get("icon") or "♡")
            hint = str(card.get("hint") or "Abrir")
            href = str(card.get("href") or "?view=home")
            view = href.split("view=", 1)[1].split("&", 1)[0] if "view=" in href else "home"
            with cols[col_index]:
                if st.button(
                    f"{icon}  {value}\n\n{label}\n{hint}",
                    key=f"nav_card_{row_index}_{col_index}_{view}_{label}",
                    use_container_width=True,
                ):
                    st.query_params["view"] = view
                    if "letter" in st.query_params and view != "open_when":
                        st.query_params.pop("letter", None)
                    st.rerun()


def _media_url_items(client, items: list[dict]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for item in items:
        url = storage.signed_url(client, item["storage_path"])
        if not url:
            continue
        result.append(
            {
                "type": str(item.get("type") or ""),
                "url": url,
                "caption": str(item.get("caption") or ""),
                "mime": str(item.get("mime_type") or ""),
            }
        )
    return result


def _render_media_carousel(url_items: list[dict[str, str]], height: int = 430) -> None:
    payload = json.dumps(url_items, ensure_ascii=False)
    carousel_html = f"""
<!doctype html>
<html>
<head>
<meta charset='utf-8' />
<style>
  html, body {{ margin:0; padding:0; background: transparent; }}
  .wrap {{
    position: relative; width: 100%; height: {height}px; overflow: hidden;
    border-radius: 24px; background: linear-gradient(135deg,#fff7f2,#edf8fb,#ffe4ef);
    border: 1px solid rgba(20,61,53,.16); box-sizing: border-box;
  }}
  .stage {{ width:100%; height:100%; display:flex; align-items:center; justify-content:center; }}
  img, video {{ width:100%; height:100%; object-fit:contain; display:block; background: rgba(255,255,255,.35); }}
  .nav {{
    position:absolute; top:50%; transform:translateY(-50%); width:44px; height:44px;
    border-radius:999px; border:1px solid rgba(20,61,53,.16); background:rgba(255,255,255,.86);
    color:#143D35; font-size:26px; cursor:pointer; display:flex; align-items:center; justify-content:center;
    box-shadow:0 8px 24px rgba(11,61,92,.14); user-select:none;
  }}
  .prev {{ left: 12px; }} .next {{ right: 12px; }}
  .caption {{
    position:absolute; left:16px; right:16px; bottom:12px; padding:.5rem .75rem;
    background:rgba(255,255,255,.82); border:1px solid rgba(20,61,53,.12); border-radius:999px;
    color:#143D35; font: 600 14px system-ui, -apple-system, Segoe UI, sans-serif;
    overflow:hidden; white-space:nowrap; text-overflow:ellipsis;
  }}
  .dots {{ position:absolute; top:12px; left:0; right:0; text-align:center; }}
  .dot {{ display:inline-block; width:8px; height:8px; margin:0 4px; border-radius:99px; background:rgba(20,61,53,.25); }}
  .dot.active {{ width:22px; background:#F28AB2; }}
  @media(max-width: 640px) {{ .wrap {{ height: 310px; border-radius: 20px; }} .nav {{ width:38px; height:38px; font-size:22px; }} }}
</style>
</head>
<body>
<div class='wrap'>
  <div class='stage' id='stage'></div>
  <button class='nav prev' onclick='prev()' aria-label='Mídia anterior'>‹</button>
  <button class='nav next' onclick='next(true)' aria-label='Próxima mídia'>›</button>
  <div class='dots' id='dots'></div>
  <div class='caption' id='caption'></div>
</div>
<script>
const items = {payload};
let index = 0;
let timer = null;
const stage = document.getElementById('stage');
const caption = document.getElementById('caption');
const dots = document.getElementById('dots');
function clearTimer() {{ if (timer) {{ clearTimeout(timer); timer = null; }} }}
function buildDots() {{ dots.innerHTML = items.map((_, i) => `<span class="dot ${{i===index?'active':''}}"></span>`).join(''); }}
function show() {{
  clearTimer();
  const item = items[index];
  stage.innerHTML = '';
  let el;
  if (item.type === 'video') {{
    el = document.createElement('video');
    el.src = item.url; el.controls = true; el.playsInline = true; el.preload = 'metadata';
    el.onended = () => next(false);
  }} else {{
    el = document.createElement('img');
    el.src = item.url; el.alt = item.caption || 'memória';
    timer = setTimeout(() => next(false), 4200);
  }}
  stage.appendChild(el);
  caption.textContent = item.caption || `${{index + 1}} de ${{items.length}}`;
  buildDots();
}}
function next(manual) {{ index = (index + 1) % items.length; show(); }}
function prev() {{ index = (index - 1 + items.length) % items.length; show(); }}
show();
</script>
</body>
</html>
"""
    components.html(carousel_html, height=height + 8, scrolling=False)


def render_media_gallery(client, media: list[dict], max_items: int | None = None) -> None:
    items = media[:max_items] if max_items else media
    if not items:
        return

    visual = [m for m in items if m.get("type") in {"image", "video"}]
    audio = [m for m in items if m.get("type") == "audio"]

    visual_urls = _media_url_items(client, visual)
    if len(visual_urls) > 1:
        _render_media_carousel(visual_urls)
    elif len(visual_urls) == 1:
        item = visual_urls[0]
        if item["type"] == "image":
            st.image(item["url"], caption=item.get("caption") or None, use_container_width=True)
        elif item["type"] == "video":
            st.video(item["url"])
            if item.get("caption"):
                st.caption(item["caption"])

    for item in audio:
        url = storage.signed_url(client, item["storage_path"])
        if url:
            st.audio(url)
            if item.get("caption"):
                st.caption(item["caption"])
