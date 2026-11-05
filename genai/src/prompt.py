"""
Monta as mensagens enviadas ao LLM a partir do prompt versionado
(genai/prompts/parecer_v1.md) e da saída do prever().

O que vai para o LLM (FORMATO_JSON.md, seção 4): números já formatados, faixa,
situação do preço, recomendação já escolhida, motivos pelo rótulo e os trechos
de normas recuperados. NÃO vai: contrato_id, versao_modelo, campos extras,
motivos sensíveis (gênero, idade, país) e a média do BC.

Teste rápido (na pasta raiz):
    python -m genai.src.prompt
"""
from pathlib import Path

from genai.src.checagem import (EntradaPrever, formatar_juro, formatar_percentual,
                                motivos_permitidos)

PASTA_PROMPTS = Path(__file__).resolve().parent.parent / "prompts"
VERSAO_PROMPT = "parecer_v1"

SITUACOES = {
    "acima_do_justo": "acima do juro justo, além da margem de incerteza",
    "abaixo_do_justo": "abaixo do juro justo, além da margem de incerteza",
    "dentro_da_margem": "dentro da margem do juro justo",
}
RECOMENDACOES = {
    "revisar_preco": "revisar o preço",
    "manter_preco": "manter o preço",
}
EFEITOS = {"aumenta_risco": "aumenta o risco", "reduz_risco": "reduz o risco"}


def carregar_prompt(versao: str = VERSAO_PROMPT) -> tuple[str, str]:
    """Devolve (mensagem do sistema, mensagem do usuário com os campos entre chaves)."""
    texto = (PASTA_PROMPTS / f"{versao}.md").read_text(encoding="utf-8")
    secoes = {}
    for bloco in texto.split("\n## ")[1:]:
        titulo, _, corpo = bloco.partition("\n")
        secoes[titulo.strip()] = corpo.strip()
    return secoes["Mensagem do sistema"], secoes["Mensagem do usuário"]


def _numeros(entrada: EntradaPrever) -> str:
    linhas = [
        ("chance de não pagar", "pd", formatar_percentual(entrada.pd)),
        ("juro cobrado", "juro_cobrado", formatar_juro(entrada.juro_cobrado)),
        ("juro justo (valor central)", "juro_justo", formatar_juro(entrada.juro_justo)),
        ("limite inferior da margem do juro justo", "juro_justo_min", formatar_juro(entrada.juro_justo_min)),
        ("limite superior da margem do juro justo", "juro_justo_max", formatar_juro(entrada.juro_justo_max)),
    ]
    return "\n".join(f"- {nome}: {texto} ({chave}: {getattr(entrada, chave)})"
                     for nome, chave, texto in linhas)


def _fatores(entrada: EntradaPrever) -> str:
    permitidos = motivos_permitidos(entrada)
    if not permitidos:
        return "(nenhum fator informado)"
    return "\n".join(f"- {m.rotulo} ({EFEITOS[m.efeito]})" for m in permitidos)


def _trechos(trechos: list[dict]) -> str:
    if not trechos:
        return "(nenhum trecho encontrado)"
    return "\n\n".join(f"[trecho_id: {t['trecho_id']} | norma: {t['norma']} | artigo: {t['artigo']}]\n{t['texto']}"
                       for t in trechos)


def montar_mensagens(entrada: EntradaPrever, recomendacao: str, trechos: list[dict],
                     versao: str = VERSAO_PROMPT) -> tuple[str, str]:
    """Devolve (sistema, usuário) prontos para o LLM. Não serve para revisão manual."""
    if entrada.vai_para_revisao_manual:
        raise ValueError("revisão manual não chama o LLM: use o template")
    sistema, usuario = carregar_prompt(versao)
    usuario = usuario.format(
        situacao=SITUACOES[entrada.situacao_preco],
        recomendacao=RECOMENDACOES[recomendacao],
        faixa=entrada.faixa,
        numeros=_numeros(entrada),
        fatores=_fatores(entrada),
        trechos=_trechos(trechos),
    )
    return sistema, usuario


if __name__ == "__main__":
    exemplo = EntradaPrever.model_validate({
        "contrato_id": "EXEMPLO-1", "versao_modelo": "exemplo",
        "pd": 0.184, "faixa": "C", "juro_cobrado": 0.249,
        "juro_justo": 0.162, "juro_justo_min": 0.141, "juro_justo_max": 0.183,
        "situacao_preco": "acima_do_justo",
        "motivos": [{"variavel": "divida_sobre_renda", "rotulo": "dívidas em relação à renda",
                     "efeito": "aumenta_risco"}],
    })
    trecho = {"trecho_id": "cdc-art6-1", "norma": "CDC", "artigo": "Art. 6º",
              "texto": "Art. 6º São direitos básicos do consumidor: (...) III - a informação adequada e clara..."}
    _, usuario = montar_mensagens(exemplo, "revisar_preco", [trecho])
    print(usuario)