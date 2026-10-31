import difflib
from datetime import datetime, timezone
from urllib.parse import urlparse

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from bs4 import BeautifulSoup

from database import (
    add_site, delete_site, get_changes, get_dashboard_stats,
    get_latest_snapshot, get_site, get_sites, get_snapshots, get_snapshot_pair,
    initialize_database, save_snapshot
)

st.set_page_config(page_title="Rastro | Web Change Intelligence", page_icon="◉", layout="wide")

st.markdown("""
<style>
    .stApp { background: #0b0d14; color: #e8eaf2; }
    [data-testid="stSidebar"] { background: #10131d; }
    .block-container { padding-top: 2rem; max-width: 1400px; }
    div[data-testid="stMetric"] { background: #141927; border: 1px solid #242c40; padding: 16px; border-radius: 12px; }
    .hero { padding: 24px 26px; border: 1px solid #293149; border-radius: 16px;
            background: linear-gradient(120deg, #171c2d, #111522); margin-bottom: 22px; }
    .muted { color: #9aa4bb; }
    .tag { color: #b8a6ff; font-weight: 700; letter-spacing: .12em; font-size: .75rem; }
    .stButton > button { border-radius: 9px; }
</style>
""", unsafe_allow_html=True)

initialize_database()

def normalize_url(url: str) -> str:
    url = url.strip()
    if not urlparse(url).scheme:
        url = "https://" + url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Informe um endereço HTTP ou HTTPS válido.")
    return url

def extract_page(url: str):
    headers = {"User-Agent": "RastroBot/1.0 (+personal website change monitor)"}
    response = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
    response.raise_for_status()
    if len(response.content) > 5_000_000:
        raise ValueError("A página excede o limite de 5 MB para esta versão.")
    content_type = response.headers.get("Content-Type", "")
    if "html" not in content_type.lower():
        raise ValueError(f"O endereço não retornou HTML (Content-Type: {content_type or 'desconhecido'}).")
    soup = BeautifulSoup(response.text, "html.parser")
    for element in soup(["script", "style", "noscript", "svg", "canvas", "iframe"]):
        element.decompose()
    text = "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())
    title = soup.title.get_text(" ", strip=True) if soup.title else url
    return title[:250], text[:500_000], response.url

def check_site(site):
    try:
        title, content, final_url = extract_page(site["url"])
        previous = get_latest_snapshot(site["id"])
        changed = previous is not None and previous["content"] != content
        added, removed = [], []
        if changed:
            old_lines = previous["content"].splitlines()
            new_lines = content.splitlines()
            diff = list(difflib.unified_diff(old_lines, new_lines, lineterm="", n=1))
            added = [line[1:] for line in diff if line.startswith("+") and not line.startswith("+++")]
            removed = [line[1:] for line in diff if line.startswith("-") and not line.startswith("---")]
        save_snapshot(site["id"], title, content, changed, len(added), len(removed))
        return True, changed, f"Verificação concluída: {final_url}", added, removed
    except requests.RequestException as exc:
        return False, False, f"Falha na requisição: {exc}", [], []
    except Exception as exc:
        return False, False, str(exc), [], []

def short(text, limit=100):
    return text if len(text) <= limit else text[:limit] + "…"

# Sidebar
with st.sidebar:
    st.markdown("## ◉ RASTRO")
    st.caption("WEB CHANGE INTELLIGENCE")
    page = st.radio("NAVEGAÇÃO", ["Visão geral", "Monitoramentos", "Histórico", "Sobre o projeto"])
    st.divider()
    st.caption("MVP local · Python + SQLite")
    st.caption("As verificações são iniciadas manualmente nesta versão.")

if page == "Visão geral":
    st.markdown('<div class="hero"><div class="tag">WEB CHANGE INTELLIGENCE</div><h1 style="margin:.35rem 0">A internet muda.<br>O Rastro percebe.</h1><p class="muted">Monitore páginas, registre versões e descubra exatamente o que mudou.</p></div>', unsafe_allow_html=True)
    stats = get_dashboard_stats()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Páginas monitoradas", stats["sites"])
    c2.metric("Verificações realizadas", stats["checks"])
    c3.metric("Alterações detectadas", stats["changes"])
    c4.metric("Alterações recentes", stats["recent_changes"])
    st.subheader("Atividade recente")
    changes = get_changes(limit=8)
    if changes:
        df = pd.DataFrame(changes)
        df["checked_at"] = pd.to_datetime(df["checked_at"]).dt.strftime("%d/%m/%Y %H:%M")
        st.dataframe(df[["site_name", "url", "checked_at", "added_lines", "removed_lines"]].rename(columns={
            "site_name":"Página", "url":"Endereço", "checked_at":"Detectado em",
            "added_lines":"Linhas adicionadas", "removed_lines":"Linhas removidas"
        }), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma alteração registrada ainda. Adicione uma página e execute a primeira verificação.")
    sites = get_sites()
    if sites:
        st.subheader("Visão de monitoramento")
        snapshots = get_snapshots()
        if snapshots:
            chart = pd.DataFrame(snapshots)
            chart["day"] = pd.to_datetime(chart["checked_at"]).dt.date
            daily = chart.groupby("day").size().reset_index(name="verificações")
            st.plotly_chart(px.bar(daily, x="day", y="verificações", title="Verificações por dia",
                                   template="plotly_dark"), use_container_width=True)

elif page == "Monitoramentos":
    st.title("Monitoramentos")
    st.caption("Cadastre páginas públicas para acompanhar mudanças no conteúdo.")
    with st.form("add_site", clear_on_submit=True):
        url_input = st.text_input("URL da página", placeholder="https://example.com/documentation")
        name_input = st.text_input("Nome (opcional)", placeholder="Documentação do produto")
        submitted = st.form_submit_button("＋ Adicionar página", use_container_width=True)
        if submitted:
            try:
                normalized = normalize_url(url_input)
                add_site(name_input.strip() or urlparse(normalized).netloc, normalized)
                st.success("Página adicionada.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    sites = get_sites()
    if not sites:
        st.info("Você ainda não adicionou páginas.")
    else:
        if st.button("⟳ Verificar todas as páginas", type="primary", use_container_width=True):
            progress = st.progress(0)
            for index, site in enumerate(sites):
                ok, changed, message, added, removed = check_site(site)
                if ok:
                    st.toast(("Alteração encontrada: " if changed else "Sem alterações: ") + site["name"])
                else:
                    st.warning(f"{site['name']}: {message}")
                progress.progress((index + 1) / len(sites))
            st.rerun()
        st.divider()
        for site in sites:
            latest = get_latest_snapshot(site["id"])
            with st.container(border=True):
                left, right = st.columns([5, 1])
                left.markdown(f"**{site['name']}**")
                left.markdown(f"[{site['url']}]({site['url']})")
                left.caption("Última verificação: " + (latest["checked_at"] if latest else "Ainda não verificada"))
                if right.button("Verificar", key=f"check_{site['id']}"):
                    ok, changed, message, added, removed = check_site(site)
                    (st.success if ok else st.error)(message)
                    if changed:
                        st.warning(f"Foram detectadas {len(added)} linhas adicionadas e {len(removed)} removidas.")
                    st.rerun()
                if right.button("Excluir", key=f"delete_{site['id']}"):
                    delete_site(site["id"])
                    st.rerun()

elif page == "Histórico":
    st.title("Histórico de alterações")
    changes = get_changes(limit=200)
    if not changes:
        st.info("O histórico está vazio. As alterações aparecerão aqui depois das verificações.")
    else:
        options = {f"{item['site_name']} · {item['checked_at']}": item for item in changes}
        selected_label = st.selectbox("Selecione um evento", list(options.keys()))
        event = options[selected_label]
        st.markdown(f"**{event['url']}**")
        st.caption(f"Detectado em {event['checked_at']}")
        before, after = st.columns(2)
        before.metric("Linhas removidas", event["removed_lines"])
        after.metric("Linhas adicionadas", event["added_lines"])
        previous, current = st.columns(2)
        previous_snapshot, current_snapshot = get_snapshot_pair(event["site_id"], event["snapshot_id"])
        with previous:
            st.subheader("Conteúdo anterior")
            st.text_area("Versão anterior", previous_snapshot or "Não disponível", height=360, disabled=True)
        with current:
            st.subheader("Conteúdo atual")
            st.text_area("Versão atual", current_snapshot or "Não disponível", height=360, disabled=True)

elif page == "Sobre o projeto":
    st.title("Sobre o Rastro")
    st.markdown("""
    **Rastro** é um projeto de monitoramento de mudanças em páginas web. Ele coleta o texto de páginas HTML,
    armazena snapshots e compara versões para identificar conteúdo adicionado ou removido.

    ### Como funciona
    1. Você cadastra uma URL pública.
    2. O Rastro solicita a página e extrai seu texto.
    3. O conteúdo é salvo como um snapshot no SQLite.
    4. Nas próximas verificações, o sistema compara o conteúdo novo com a versão anterior.
    5. Se houver diferenças, registra o evento no histórico.

    ### Stack
    - **Python:** lógica da aplicação.
    - **Requests + BeautifulSoup:** coleta e extração de conteúdo.
    - **SQLite:** persistência local.
    - **Pandas + Plotly:** análise e visualização.
    - **Streamlit:** interface web.

    ### Limitações desta versão
    - As verificações são manuais; agendamento automático é uma evolução planejada.
    - Páginas que dependem de JavaScript para carregar conteúdo podem não ser lidas corretamente.
    - O sistema compara texto extraído, não diferenças visuais ou alterações no código-fonte.
    - Respeite os termos de uso, políticas de acesso e limites dos sites monitorados.
    """)
