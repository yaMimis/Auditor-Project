"""Página Sobre: equipe e onde cada parte do estudo aparece no painel.
"""

import streamlit as st

from src.app.components import esc, html_team_avatar, image_data_uri
from src.app.nucleo import IMAGES_DIR, md


# (iniciais, nome, papel, o que fez, arquivo da foto em src/app/imagens/equipe/ sem a extensão)
TEAM = [
    ("YG", "Yasmin Garcia", "App & Infraestrutura",
     "Docker, API FastAPI, painel Streamlit (Análise, Laboratório e Auditoria), integração contínua e vídeo da demo.",
     "yasmin"),
    ("MA", "Marcos", "Dados & Processo",
     "Carga do Bondora e das séries de juros no PostgreSQL, qualidade dos dados, EDA e BPMN.", "marcos"),
    ("SL", "Samuel", "Modelo & Juro Justo",
     "Modelo de risco calibrado, motivos (SHAP), juro justo com margem de incerteza, equidade e backtest.",
     "samuel"),
    ("MV", "M. Vitória", "GenAI & RAG",
     "Normas e busca (RAG), prompts, parecer com checagem por código e template de reserva.", "maria"),
]
STUDY_MAP = [
    ("Base Bondora no PostgreSQL", "Marcos", "Dados buscados pelo ID; resultado observado (ou o motivo de não haver)"),
    ("XGBoost calibrado + bootstrap", "Samuel", "Risco e intervalo calculados na hora; Laboratório"),
    ("SHAP", "Samuel", "“O que mais pesou”, com o valor do contrato"),
    ("Juro justo por fluxo de caixa", "Samuel", "Precificação; Laboratório"),
    ("Backtest por faixa", "Samuel e Marcos", "Home (retorno real de 2016 por faixa e situação)"),
    ("Equidade agregada", "Samuel", "Auditoria"),
    ("Teste de invariância (gênero e idade trocados)", "Yasmin", "Auditoria: um contrato na hora e 500 em lote"),
    ("Cenários (o modelo de novo com outros valores)", "Yasmin", "Laboratório; taxa testada vira proposta"),
    ("RAG com normas + checagem", "M. Vitória", "Parecer da Análise"),
    ("API, painel, plano B, decisões no banco", "Yasmin", "Todo o fluxo e o Registro"),
]


def render_about_page() -> None:
    md("""
        <div class="section-header">
            <h2>Sobre o Projeto</h2>
            <div class="gold-divider"></div>
            <p>Projeto integrador do <b>Bootcamp IA 2026</b> (segmento BFSI).<br>
            Dados reais do Bondora (2009–2021) como substitutos do comportamento de crédito; análise jurídica hipotética pela lei brasileira.</p>
        </div>
    """)
    md('<div class="team-grid">' + "".join(f"""
        <div class="team-card">
            {html_team_avatar(code, image_data_uri(IMAGES_DIR / "equipe", photo))}
            <div class="team-name">{esc(name_)}</div>
            <div class="team-role">{esc(role)}</div>
            <div class="team-bio">{esc(bio)}</div>
        </div>""" for code, name_, role, bio, photo in TEAM) + "</div>")
    _, area, _ = st.columns([0.35, 5, 0.35])
    with area:
        body = "".join(f"<tr><td>{esc(a)}</td><td>{esc(b)}</td><td>{esc(c)}</td></tr>" for a, b, c in STUDY_MAP)
        md(f"""<div class="ap-card"><div class="ap-card-title">Onde cada parte do estudo aparece funcionando</div>
            <table class="ap-table"><thead><tr><th>Parte do estudo</th><th>Quem fez</th><th>Onde aparece</th></tr></thead>
            <tbody>{body}</tbody></table></div>""")
