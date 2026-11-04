"""
Contratos de dados da frente de GenAI (fonte da verdade do FORMATO_JSON.md, seção 6).

EntradaPrever valida o que chega do prever(); RespostaLLM é o que o LLM devolve;
Parecer é o que gerar_parecer() entrega para a tela.
conferir_parecer() confere o que o LLM escreveu (REGRAS_PARECER.md, seção 9).
motivos_permitidos() tira gênero, idade e país dos motivos (REGRAS_PARECER.md, seção 4).

Teste rápido (na pasta raiz):
    python genai/src/checagem.py
"""
import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ChaveNumero = Literal["pd", "juro_cobrado", "juro_justo", "juro_justo_min", "juro_justo_max"]


# ---------- Entrada (do prever) ----------

class Motivo(BaseModel):
    model_config = ConfigDict(extra="ignore")  # descarta valor e peso
    variavel: str
    rotulo: str
    efeito: Literal["aumenta_risco", "reduz_risco"]


class EntradaPrever(BaseModel):
    model_config = ConfigDict(extra="ignore")  # descarta pd_ic95, diferenca_pp etc.
    contrato_id: str
    versao_modelo: str
    pd: float | None = Field(default=None, ge=0, le=1)
    faixa: Literal["A", "B", "C", "D", "E"] | None = None
    juro_cobrado: float
    juro_justo: float | None = None
    juro_justo_min: float | None = None
    juro_justo_max: float | None = None
    situacao_preco: Literal["acima_do_justo", "abaixo_do_justo", "dentro_da_margem", "revisao_manual"]
    motivos: list[Motivo] = []
    alerta_dados: bool = False

    @model_validator(mode="after")
    def exige_numeros_fora_da_revisao_manual(self):
        if self.situacao_preco != "revisao_manual":
            obrigatorios = ("pd", "faixa", "juro_justo", "juro_justo_min", "juro_justo_max")
            faltando = [c for c in obrigatorios if getattr(self, c) is None]
            if faltando:
                raise ValueError(f"campos nulos fora de revisao_manual: {faltando}")
        return self

    @property
    def vai_para_revisao_manual(self) -> bool:
        return self.situacao_preco == "revisao_manual" or self.alerta_dados


# ---------- Saída (para a tela) ----------

class Fonte(BaseModel):
    norma: str
    artigo: str
    trecho_id: str


class RespostaLLM(BaseModel):
    """O que o LLM devolve (saída estruturada)."""
    resumo: str
    pontos_de_atencao: list[str] = Field(max_length=3)
    recomendacao_texto: str
    fontes: list[Fonte]
    numeros_citados: dict[ChaveNumero, float]


class Parecer(RespostaLLM):
    """O que gerar_parecer() devolve para a tela."""
    contrato_id: str
    recomendacao: Literal["manter_preco", "revisar_preco", "encaminhar_compliance", "revisao_manual"]
    origem: Literal["llm", "template"]
    versao_prompt: str
    gerado_em: datetime


# ---------- Conferência do parecer (REGRAS_PARECER.md, seção 9) ----------

UNIDADE_JURO = "ao ano"  # decisão 3: se o grupo mudar para "ao mês", muda só aqui
TOLERANCIA_PP = 0.051     # o texto usa 1 casa decimal: 16,2% vale para 0.162 e 0.1624

# Número com "%" (aceita "18,4%", "18.4 %") ou número com vírgula decimal ("0,184", "8,7 p.p.").
# Números inteiros sem % ("art. 6º", "Lei nº 8.078", "Resolução 4.881") são ignorados.
PADRAO_NUMERO = re.compile(r"(\d+(?:[.,]\d+)?)\s*%|(\d+,\d+)")

# Seção 3: palavras que afirmam conclusão jurídica (só o compliance pode concluir).
# Atenção: "discriminar"/"discriminando" (= detalhar, Res. 5.004 art. 3º) é permitido.
PALAVRAS_PROIBIDAS = re.compile(
    r"\b(ilega(?:l\w*|is)|il[ií]cit\w+|irregular\w*|crim(?:e|es|inos\w*)|fraud\w+|"
    r"viola(?:m|r|ç(?:ão|ões))?|violou|violad[oa]s?|abusiv\w+|"
    r"discriminaç(?:ão|ões)|discriminat[óo]ri\w+)\b",
    re.IGNORECASE,
)

# Seção 4: gênero, idade e país nunca aparecem no parecer.
ATRIBUTOS_SENSIVEIS = re.compile(
    r"\b(g[eê]neros?|sexo|idades?|et[áa]ri[oa]s?|idos[oa]s?|pa[ií]s|pa[ií]ses|nacionalidade|estrangeir[oa]s?)\b",
    re.IGNORECASE)
VARIAVEIS_SENSIVEIS = {"age", "gender", "sex", "country", "nationality",
                       "idade", "genero", "sexo", "pais", "nacionalidade"}

MAXIMO_FRASES_RESUMO = 2
# Uma frase termina em . ! ou ? seguido de espaço e letra maiúscula ("art. 6º" não quebra).
FIM_DE_FRASE = re.compile(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ])")
# Abreviações jurídicas ("inc. III", "Res. CMN") não terminam frase.
ABREVIACOES = re.compile(r"\b(arts?|incs?|res|par|dra?|sra?|n[ºo])\.\s", re.IGNORECASE)


def motivo_e_sensivel(motivo: Motivo) -> bool:
    """True se o motivo fala de gênero, idade ou país (em português ou no nome técnico)."""
    partes_da_variavel = set(re.split(r"[^a-z]+", motivo.variavel.lower()))
    return bool(ATRIBUTOS_SENSIVEIS.search(motivo.rotulo) or partes_da_variavel & VARIAVEIS_SENSIVEIS)


def motivos_permitidos(entrada: EntradaPrever) -> list[Motivo]:
    """Motivos que podem ir para o parecer e para o LLM."""
    return [m for m in entrada.motivos if not motivo_e_sensivel(m)]


def contar_frases(texto: str) -> int:
    texto = ABREVIACOES.sub(r"\1._", texto.strip())  # "inc. III" vira "inc._III" só para contar
    return len([f for f in FIM_DE_FRASE.split(texto) if f])


def formatar_percentual(valor: float) -> str:
    """0.184 -> '18,4%'"""
    return f"{valor * 100:.1f}%".replace(".", ",")


def formatar_juro(valor: float) -> str:
    """0.249 -> '24,9% ao ano'"""
    return f"{formatar_percentual(valor)} {UNIDADE_JURO}"


def extrair_numeros(texto: str) -> list[float]:
    """Devolve os números do texto que precisam vir do prever(), em pontos percentuais."""
    numeros = []
    for com_porcento, com_virgula in PADRAO_NUMERO.findall(texto):
        bruto = com_porcento or com_virgula
        numeros.append(float(bruto.replace(",", ".")))
    return numeros


def conferir_parecer(resposta: RespostaLLM, entrada: EntradaPrever,
                     trechos_recuperados: list[str]) -> list[str]:
    """Confere o que o LLM escreveu. Lista vazia = aprovado; senão, usar o template."""
    problemas = []

    # 1. numeros_citados: só campos que vieram do prever(), com o valor exato.
    for chave, valor in resposta.numeros_citados.items():
        original = getattr(entrada, chave)
        if original is None:
            problemas.append(f"numeros_citados.{chave}: o campo veio nulo do prever()")
        elif abs(valor - original) > 1e-9:
            problemas.append(f"numeros_citados.{chave}: {valor} diferente do prever() ({original})")

    # 2. Todo número escrito no texto precisa ser um dos numeros_citados.
    permitidos = [round(v * 100, 1) for v in resposta.numeros_citados.values()]
    textos = [resposta.resumo, *resposta.pontos_de_atencao, resposta.recomendacao_texto]
    for texto in textos:
        for numero in extrair_numeros(texto):
            if not any(abs(numero - p) <= TOLERANCIA_PP for p in permitidos):
                problemas.append(f"número {numero} no texto não vem do prever(): \"{texto[:60]}...\"")

    # 3. Toda fonte citada precisa estar entre os trechos que a busca devolveu.
    for fonte in resposta.fontes:
        if fonte.trecho_id not in trechos_recuperados:
            problemas.append(f"fonte {fonte.trecho_id} não está entre os trechos recuperados")

    # 4. Vocabulário e 5. atributos sensíveis, em todos os textos.
    for texto in textos:
        for achado in PALAVRAS_PROIBIDAS.findall(texto):
            problemas.append(f"palavra proibida \"{achado}\" no texto")
        for achado in ATRIBUTOS_SENSIVEIS.findall(texto):
            problemas.append(f"atributo sensível \"{achado}\" no texto")

    # 6. Tamanho: resumo com até 2 frases (o limite de 3 pontos já vem do RespostaLLM).
    frases = contar_frases(resposta.resumo)
    if frases > MAXIMO_FRASES_RESUMO:
        problemas.append(f"resumo com {frases} frases (máximo {MAXIMO_FRASES_RESUMO})")

    return problemas


if __name__ == "__main__":
    import json
    from pathlib import Path

    from pydantic import ValidationError

    exemplos = json.loads(Path("docs/exemplos_prever.json").read_text(encoding="utf-8"))
    validos = 0
    for exemplo in exemplos:
        try:
            entrada = EntradaPrever.model_validate(exemplo)
        except ValidationError as erro:
            print(f"ERRO {exemplo.get('contrato_id', '?')}: {erro.error_count()} problema(s)")
            for problema in erro.errors()[:3]:
                campo = ".".join(str(parte) for parte in problema["loc"])
                print(f"     - {campo}: {problema['msg']}")
            continue
        validos += 1
        print(f"OK   {entrada.contrato_id:<10} {entrada.situacao_preco:<17} "
              f"revisão manual: {entrada.vai_para_revisao_manual}")
    print(f"\n{validos} de {len(exemplos)} exemplos do prever() validados contra o contrato.")