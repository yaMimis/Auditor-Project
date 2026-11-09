"""
Template de reserva do parecer (REGRAS_PARECER.md, seções 7 e 8).

Monta o parecer SEM IA, só com os números do prever(). É usado quando:
- o caso é de revisão manual (o LLM nem é chamado);
- o LLM falha, demora mais de 20 s, devolve JSON inválido
  ou a conferência (checagem.py) recusa o parecer.

Teste rápido (na pasta raiz):
    python -m genai.src.template
"""
from datetime import datetime, timedelta, timezone

from genai.src.checagem import (EntradaPrever, Parecer, casas_decimais, formatar_juro,
                               formatar_percentual, montar_contexto_mercado, motivos_permitidos)

VERSAO_TEMPLATE = "template_v1"
DECISAO = "A decisão final é do analista."
FUSO = timezone(timedelta(hours=-3))  # horário de Brasília (sem horário de verão desde 2019)


def escolher_recomendacao(entrada: EntradaPrever) -> str:
    """Tabela da seção 7 do REGRAS_PARECER.md (a ordem importa)."""
    if entrada.vai_para_revisao_manual:
        return "revisao_manual"
    if entrada.situacao_preco in ("acima_do_justo", "abaixo_do_justo"):
        return "revisar_preco"
    return "manter_preco"


def _fatores(entrada: EntradaPrever) -> str | None:
    """'Principais fatores do risco: prazo do empréstimo (aumenta o risco), ...'"""
    permitidos = motivos_permitidos(entrada)  # sem gênero, idade e país (seção 4)
    if not permitidos:
        return None
    efeito = {"aumenta_risco": "aumenta o risco", "reduz_risco": "reduz o risco"}
    lista = ", ".join(f"{m.rotulo} ({efeito[m.efeito]})" for m in permitidos[:3])
    return f"Principais fatores do risco: {lista}."


def _textos(entrada: EntradaPrever) -> tuple[str, list[str], str, list[str]]:
    """Devolve (resumo, pontos_de_atencao, recomendacao_texto, chaves dos números usados)."""
    casas = casas_decimais(entrada)
    cobrado = formatar_juro(entrada.juro_cobrado, casas)

    if entrada.vai_para_revisao_manual:
        return (
            "Os dados deste contrato estão fora da faixa conhecida pelo modelo. "
            "Não é possível estimar o risco e o juro justo com segurança.",
            [f"O juro cobrado é de {cobrado}, mas não há juro justo calculado para comparar."],
            f"Recomenda-se análise manual do contrato. {DECISAO}",
            ["juro_cobrado"],
        )

    risco = f"Risco faixa {entrada.faixa} (chance de não pagar de {formatar_percentual(entrada.pd)})."
    margem = (f"de {formatar_percentual(entrada.juro_justo_min, casas)} a "
              f"{formatar_juro(entrada.juro_justo_max, casas)}, "
              f"com valor central de {formatar_juro(entrada.juro_justo, casas)}")
    fatores = _fatores(entrada)
    todas = ["pd", "juro_cobrado", "juro_justo", "juro_justo_min", "juro_justo_max"]

    if entrada.situacao_preco == "acima_do_justo":
        pontos = [f"O juro cobrado, de {cobrado}, está acima da margem do juro justo estimado: {margem}.",
                  "A diferença não é explicada pelo risco estimado pelo modelo. "
                  "É um indício a investigar, não uma conclusão."]
        return (
            f"{risco} O juro cobrado está acima do juro justo, além da margem de incerteza.",
            pontos + ([fatores] if fatores else []),
            "Recomenda-se revisar o preço deste contrato. Se a política de preço não justificar "
            f"a diferença, recomenda-se encaminhar ao compliance. {DECISAO}",
            todas,
        )

    if entrada.situacao_preco == "abaixo_do_justo":
        pontos = [f"O juro cobrado, de {cobrado}, está abaixo da margem do juro justo estimado: {margem}.",
                  "Esse preço pode não cobrir a perda esperada. "
                  "É um ponto de atenção para o banco, não uma falha do cliente."]
        return (
            f"{risco} O juro cobrado está abaixo do necessário para cobrir esse risco.",
            pontos + ([fatores] if fatores else []),
            f"Recomenda-se revisar a política de preço para contratos com este perfil de risco. {DECISAO}",
            todas,
        )

    # dentro_da_margem
    pontos = [f"O juro cobrado, de {cobrado}, está dentro da margem do juro justo estimado: {margem}."]
    return (
        f"{risco} O juro cobrado está dentro da margem esperada para esse risco.",
        pontos + ([fatores] if fatores else []),
        f"Recomenda-se manter o preço. {DECISAO}",
        todas,
    )


def montar_template(entrada: EntradaPrever, agora: datetime | None = None) -> Parecer:
    """Parecer completo, sem IA, com origem 'template' e fontes vazias.

    `agora` serve para os testes usarem uma hora fixa; no uso normal, fica vazio.
    """
    resumo, pontos, recomendacao_texto, chaves = _textos(entrada)
    return Parecer(
        contrato_id=entrada.contrato_id,
        resumo=resumo,
        pontos_de_atencao=pontos,
        recomendacao=escolher_recomendacao(entrada),
        recomendacao_texto=recomendacao_texto,
        fontes=[],
        numeros_citados={chave: getattr(entrada, chave) for chave in chaves},
        origem="template",
        versao_prompt=VERSAO_TEMPLATE,
        gerado_em=agora or datetime.now(FUSO),
        contexto_mercado=montar_contexto_mercado(entrada),
    )


if __name__ == "__main__":
    exemplo = EntradaPrever.model_validate({
        "contrato_id": "EXEMPLO-1", "versao_modelo": "exemplo",
        "pd": 0.184, "faixa": "C", "juro_cobrado": 0.249,
        "juro_justo": 0.162, "juro_justo_min": 0.141, "juro_justo_max": 0.183,
        "situacao_preco": "acima_do_justo",
        "motivos": [{"variavel": "divida_sobre_renda", "rotulo": "dívidas em relação à renda",
                     "efeito": "aumenta_risco"},
                    {"variavel": "prazo_meses", "rotulo": "prazo do empréstimo",
                     "efeito": "aumenta_risco"}],
    })
    print(montar_template(exemplo).model_dump_json(indent=2))