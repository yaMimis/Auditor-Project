"""O que todas as páginas do painel usam: endereço da API, chamadas HTTP (com os erros em português),
os dados do lote em cache, a navegação entre páginas e o md() que injeta HTML.
"""
from datetime import timedelta, timezone
from pathlib import Path
import json
import os

import requests
import streamlit as st

from src.app.components import compact, esc


BR_TIMEZONE = timezone(timedelta(hours=-3))
API_BASE = os.getenv("API_URL", "http://localhost:8000")
TIMEOUT_S = 30  # cobre o modelo + a busca nas normas + LLM (20 s) + queda para o template
QUERY_TIMEOUT_S = 5  # leituras rápidas (decisões)
# Fotos opcionais (ver src/app/imagens/LEIA-ME.md): capa.jpg na Home e uma por integrante no Sobre.
IMAGES_DIR = Path(__file__).with_name("imagens")


def md(block: str) -> None:
    st.markdown(compact(block), unsafe_allow_html=True)


# Páginas do menu do topo. Botões (e não st.tabs) porque o painel troca de página sozinho:
# abrir um contrato vai direto para a Análise.
# Nomes curtos: os 7 cabem inteiros no menu mesmo em tela de notebook (o título de cada página diz o resto).
PAGES = {"home": "Início", "contratos": "Contratos", "analise": "Análise",
         "lab": "Laboratório", "auditoria": "Auditoria", "registro": "Registro", "sobre": "Sobre"}


def go_to(page: str) -> None:
    st.session_state.page = page


@st.cache_data(ttl=20, show_spinner=False)
def api_status() -> dict | None:
    try:
        r = requests.get(f"{API_BASE}/", timeout=3)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException:
        return None


def post_api(route: str, payload: dict) -> tuple[dict | None, str | None]:
    """POST na API. Devolve (resposta, erro) com mensagem amigável para a tela."""
    url = f"{API_BASE}{route}"
    try:
        r = requests.post(url, json=payload, timeout=TIMEOUT_S)
    except requests.exceptions.Timeout:
        return None, f"A API não respondeu em {TIMEOUT_S} s ({url})."
    except requests.exceptions.ConnectionError:
        return None, f"Não foi possível conectar à API em {API_BASE}. Confira se o serviço 'api' está no ar."
    if r.status_code in (404, 422, 503):
        detail = api_error_detail(r)
        if r.status_code == 422 and not isinstance(detail, str):
            return None, "A API recusou os dados enviados (formato inválido). Detalhe: " + r.text[:400]
        return None, detail or "Serviço indisponível na API."
    if not r.ok:
        return None, f"A API respondeu com erro {r.status_code}: {r.text[:300]}"
    try:
        data = r.json()
    except json.JSONDecodeError:
        return None, "A resposta da API não pôde ser interpretada."
    if not isinstance(data, dict):
        return None, "A API retornou uma estrutura diferente da esperada."
    return data, None


def api_error_detail(r) -> str | list | None:
    try:
        return r.json().get("detail")
    except (json.JSONDecodeError, AttributeError):
        return None


def get_api(route: str, params: dict | None = None,
            timeout: float = QUERY_TIMEOUT_S) -> tuple[list | dict | None, str | None]:
    """GET na API (leituras rápidas por padrão). Devolve (dados, erro)."""
    try:
        r = requests.get(f"{API_BASE}{route}", params=params, timeout=timeout)
    except requests.exceptions.RequestException:
        return None, f"Não foi possível conectar à API em {API_BASE}."
    if not r.ok:
        return None, str(api_error_detail(r) or f"A API respondeu com erro {r.status_code}.")
    try:
        return r.json(), None
    except json.JSONDecodeError:
        return None, "A resposta da API não pôde ser interpretada."


def get_list(route: str, params: dict | None = None) -> tuple[list[dict], str | None]:
    """Como get_api, mas garante uma lista (vazia se a resposta vier em outro formato)."""
    data, error_msg = get_api(route, params)
    if error_msg is None and not isinstance(data, list):
        return [], "A API devolveu um formato inesperado."
    return data or [], error_msg


def store_result(resultado: dict, context: dict) -> None:
    st.session_state.audit_last_result = resultado
    st.session_state.audit_last_context = context
    item = {k: resultado.get(k) for k in ("contrato_id", "pd", "faixa", "juro_cobrado", "juro_justo",
                                         "juro_justo_min", "juro_justo_max", "situacao_preco")}
    history = [h for h in st.session_state.history if h["contrato_id"] != item["contrato_id"]]
    st.session_state.history = [item] + history


BATCH_FILE = "carteira_auditoria.csv"  # o lote fica com a API (docs/resultados/); o painel só pede


@st.cache_data(ttl=60, show_spinner=False)
def portfolio_overview(year_min: int | None = None, year_max: int | None = None,
                       country: str | None = None, band: str | None = None) -> tuple[dict | None, str | None]:
    """Panorama da carteira (GET /portfolio/overview). Devolve (dados, erro)."""
    params = {k: v for k, v in {"year_min": year_min, "year_max": year_max, "country": country,
                                "band": band}.items() if v is not None}
    data, error_msg = get_api("/portfolio/overview", params, timeout=TIMEOUT_S)
    return (data, None) if isinstance(data, dict) else (None, error_msg or "resposta inesperada da API")


@st.cache_data(ttl=60, show_spinner=False)
def contract_listing(situation: str | None, limit: int) -> tuple[dict | None, str | None]:
    """Contratos do lote (GET /contracts), do mais distante para o mais próximo da margem."""
    params = {"limit": limit, **({"situation": situation} if situation else {})}
    data, error_msg = get_api("/contracts", params, timeout=TIMEOUT_S)
    return (data, None) if isinstance(data, dict) else (None, error_msg or "resposta inesperada da API")


@st.cache_data(ttl=300, max_entries=8, show_spinner="Preparando a exportação...")
def listing_csv(situation: str | None) -> bytes | None:
    """CSV da lista completa (GET /contracts/export). Só roda quando o analista pede."""
    try:
        r = requests.get(f"{API_BASE}/contracts/export", params={"situation": situation} if situation else None,
                         timeout=TIMEOUT_S)
    except requests.exceptions.RequestException:
        return None
    return r.content if r.ok else None


def api_status_line() -> None:
    """Uma linha com o estado da API, do modelo e do banco (topo de Contratos e Análise)."""
    status = api_status()
    if status is None:
        md(f'<span class="ap-status"><i class="ap-dot" style="background:#d9825b"></i>'
           f'API fora do ar ({esc(API_BASE)}): as telas voltam quando ela voltar. Confira o Docker.</span>')
        return
    if not status.get("modelo_carregavel", True):
        md('<span class="ap-status"><i class="ap-dot" style="background:#e8a462"></i>'
           'API no ar, mas o arquivo do modelo não está em modelos_salvos/: a Análise usa o lote.</span>')
    else:
        md(f'<span class="ap-status"><i class="ap-dot" style="background:#8cc7a1"></i>API no ar · modelo carregado'
           f' ({esc(status.get("versao_modelo") or "versão não informada")})</span>')
    if not status.get("genai_configurada", True):
        md('<span class="ap-status"><i class="ap-dot" style="background:#e8a462"></i>'
           'GenAI sem chave configurada: o parecer sai pelo template de reserva.</span>')
    if not status.get("banco_disponivel", False):
        md('<span class="ap-status"><i class="ap-dot" style="background:#e8a462"></i>'
           'Banco indisponível: a Análise usa o lote e nenhuma decisão é registrada até ele voltar.</span>')
