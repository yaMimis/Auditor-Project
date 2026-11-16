"""Formatação e blocos HTML do painel (sem Streamlit: tudo aqui é testável com pytest).

Regras de exibição (genai/REGRAS_PARECER.md e FORMATO_JSON.md):
- PD e juros chegam em FRAÇÃO (0.249) e são mostrados com vírgula e 1 casa ("24,9%");
- juros são NOMINAIS ao ano (convenção do Bondora; FORMATO_JSON v1.5): rótulo "a.a. nominal";
- campo nulo vira "—" (nunca 0%);
- todo texto vindo da API passa por html.escape antes de entrar no HTML.

O pacote é dividido por página; este __init__ reexporta tudo, então
`from src.app.components import pct` continua funcionando:
- base.py: Formatação brasileira (%, €, p.p.), situações do preço, selos, cartão de número, ícone "i" e ícones de linha.
- analise.py: Blocos da página Análise: cartões, régua, motivos, dados do contrato, precificação, procedência, resultado observado e parecer.
- laboratorio.py: Blocos da página Laboratório: original × cenário e o efeito de cada campo trocado.
- carteira.py: Blocos da página Início: situação do preço por faixa de risco.
- auditoria.py: Blocos da página Auditoria: equidade (gráfico, leitura em português, tabela) e teste de invariância.
- equipe.py: Imagens: capa e fotos da equipe embutidas na página (funcionam sem internet).
"""
from src.app.components.base import *  # noqa: F401,F403
from src.app.components.analise import *  # noqa: F401,F403
from src.app.components.laboratorio import *  # noqa: F401,F403
from src.app.components.carteira import *  # noqa: F401,F403
from src.app.components.auditoria import *  # noqa: F401,F403
from src.app.components.equipe import *  # noqa: F401,F403
