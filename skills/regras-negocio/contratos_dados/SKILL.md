---
name: auditor-contratos-dados
description: Use sempre que um formato atravessar frentes no Auditor de Preço Justo — saída do prever(), entrada e saída do parecer, entrada e saída da API, arquivos do lote da carteira e registro de decisões. Define campos, tipos, unidades, nulos e como mudar uma versão.
---

# Contratos de dados entre as frentes

> Leia antes: `boas-praticas-python` (unidades e como mudar contrato). Envie **sempre** junto com o setor em que a IA vai trabalhar. Fonte da verdade: modelos pydantic em `genai/src/checagem.py`; documento: `genai/FORMATO_JSON.md` (v1.4, Maria).

## Objetivo

Cada frente trabalha sozinha sabendo **exatamente** o que recebe e o que entrega. Mudança de formato = **nova versão + aviso a todas as frentes**.

## Unidades

- PD e juros **em fração** (0.249 = 24,9% a.a.), juros **nominais ao ano**. Exceção: `juro_aa` (banco) e `interest_cobrado` (API) em %.
- Datas ISO 8601; `gerado_em` com fuso −03:00.
- Texto para pessoas ("24,9% ao ano", "18,4%") é formatado **pelo código**, com vírgula e 1 casa.

## 1. Saída do `prever()` (Samuel → Maria, API, painel)

```json
{
  "contrato_id": "BO-483449",
  "versao_modelo": "xgboost_v2",
  "pd": 0.184,
  "pd_ic95": null,
  "faixa": "C",
  "juro_cobrado": 0.249,
  "juro_justo": 0.162,
  "juro_justo_min": 0.141,
  "juro_justo_max": 0.183,
  "diferenca_pp": 8.7,
  "situacao_preco": "acima_do_justo",
  "motivos": [
    {"variavel": "divida_sobre_renda", "rotulo": "dívidas em relação à renda",
     "efeito": "aumenta_risco", "valor": 0.48, "peso": 0.31}
  ],
  "alerta_dados": false
}
```

- `situacao_preco ∈ {acima_do_justo, abaixo_do_justo, dentro_da_margem, revisao_manual}`; `faixa ∈ {A,…,E}`.
- **Revisão manual:** `pd`, `pd_ic95`, `faixa`, `juro_justo`, `juro_justo_min`, `juro_justo_max`, `diferenca_pp` = `null`; `motivos = []`; `alerta_dados = true`. Fora da revisão manual, `pd`, `faixa` e os três juros justos são obrigatórios.
- **Extras** ignorados pela GenAI (`extra="ignore"`): `pd_ic95`, `diferenca_pp`, `valor` e `peso` dos motivos, `juro_pares_mediana`.
- **[EM ANDAMENTO] (Samuel)** `juro_pares_mediana: float | null` — segunda opinião; não altera a situação.
- Exemplos: `docs/exemplos_prever.json` (ilustrativos, 1 por situação) e `docs/casos_de_teste.json` (reais, 2 por situação, gerados por `casos_de_teste()`).

## 2. Modelos pydantic (`genai/src/checagem.py`)

```python
ChaveNumero = Literal["pd", "juro_cobrado", "juro_justo", "juro_justo_min", "juro_justo_max"]

class Motivo(BaseModel):            # extra="ignore"
    variavel: str
    rotulo: str
    efeito: Literal["aumenta_risco", "reduz_risco"]

class EntradaPrever(BaseModel):     # extra="ignore"
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
    # validador: fora de revisao_manual, pd, faixa e juros justos são obrigatórios
    # propriedade vai_para_revisao_manual = situacao_preco == "revisao_manual" or alerta_dados

class Fonte(BaseModel):
    norma: str
    artigo: str        # "art. 6º, III"
    trecho_id: str     # "cdc-art6-1"

class RespostaLLM(BaseModel):       # o que o LLM devolve (saída estruturada)
    resumo: str
    pontos_de_atencao: list[str] = Field(max_length=3)
    recomendacao_texto: str
    fontes: list[Fonte]
    numeros_citados: dict[ChaveNumero, float]

class Parecer(RespostaLLM):         # o que gerar_parecer() devolve à tela
    contrato_id: str
    recomendacao: Literal["manter_preco", "revisar_preco", "encaminhar_compliance", "revisao_manual"]
    origem: Literal["llm", "template"]
    versao_prompt: str              # parecer_v1, parecer_v2 … ou template_v1
    gerado_em: datetime
```

## 3. Exemplo de `Parecer`

```json
{
  "contrato_id": "BO-483449",
  "resumo": "Cliente de risco moderado (faixa C, chance de não pagar de 18,4%). Se este contrato fosse de um banco brasileiro, o juro cobrado estaria acima do juro justo estimado para esse risco, mesmo considerando a margem de incerteza.",
  "pontos_de_atencao": [
    "O juro cobrado (24,9% ao ano) está acima da margem do juro justo estimado (14,1% a 18,3% ao ano; valor central 16,2% ao ano).",
    "A diferença não é explicada pelo risco estimado pelo modelo. É um indício a investigar, não uma conclusão."
  ],
  "recomendacao": "revisar_preco",
  "recomendacao_texto": "Recomenda-se revisar o preço deste contrato. Se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.",
  "fontes": [{"norma": "CDC", "artigo": "art. 6º, III", "trecho_id": "cdc-art6-1"}],
  "numeros_citados": {"pd": 0.184, "juro_cobrado": 0.249, "juro_justo": 0.162, "juro_justo_min": 0.141, "juro_justo_max": 0.183},
  "origem": "llm",
  "versao_prompt": "parecer_v1",
  "gerado_em": "2026-11-05T14:30:00-03:00"
}
```

**[EM ANDAMENTO] (Maria + Yasmin)** referência de mercado do BC: campo opcional `bc_credito_pessoal_aa` (efetiva, % a.a., da `vw_custo_do_dinheiro`) na entrada e `contexto_mercado: str | null` na saída, com **frase fixa escrita pelo código** (valor convertido para nominal; efetiva entre parênteses). O LLM não recebe o número. Antes de 03/2011 fica vazio. Entra como nova versão do `FORMATO_JSON.md`.

## 4. API (`src/api/schemas.py`) — painel → API → painel

**Entrada `SolicitacaoEmprestimo`** (nomes do formulário, convertidos na API):

| Campo | Tipo | Vira no `prever()` |
|---|---|---|
| `loan_id` | str | `loan_id` |
| `amount` | float > 0, € | `valor_concedido` |
| `income_total` | float ≥ 0, € mensal | `renda_total` |
| `loan_duration` | int 1–120 | `prazo_meses` |
| `country` | "EE" ou "EE(Estônia)" → só a sigla | `pais` |
| `interest_cobrado` | float 0–500, **em %** | `juro_aa` |
| `liabilities_total` | float ≥ 0 ou null, € | `passivos_total` |
| `data_emprestimo` | data; padrão **hoje**; nunca no futuro | `data_emprestimo` (ISO) |
| `gender`, `age` | int ou null | **não** vão ao `prever()` (só registro de auditoria) |

O dicionário enviado ao `prever()` **precisa conter** também, com `None`: `passivos_existentes`, `n_emprestimos_anteriores`, `valor_emprestimos_anteriores`, `novo_cliente`, `tempo_emprego_atual`, `escolaridade`, `tipo_moradia`, `tipo_verificacao` (faltar a chave quebra o `prever()`).

**Saída `RespostaPrever`** = `EntradaPrever` (herdado) + `motivos: list[MotivoPrever]` (com `valor`, `peso`) + `pd_ic95`, `diferenca_pp`, `juro_pares_mediana` + `parecer_ia: Parecer | null`.

## 5. Arquivos do lote da carteira (Samuel → painel), em `docs/resultados/`

**`carteira_auditoria.csv`** — uma linha por contrato pontuado (juros em fração):
- obrigatórias: `contrato_id`, `ano`, `pais`, `pd`, `faixa`, `juro_cobrado`, `juro_justo`, `juro_justo_min`, `juro_justo_max`, `situacao_preco`
- opcionais: `valor_concedido`, `prazo_meses`, `excesso_eur` (acima do justo), `perda_nao_coberta_eur` (abaixo do justo), `rentabilidade_realizada` (encerrados, backtest), `fora_da_auditoria`, `versao_modelo`

**`equidade.json`** — só gênero e idade (país nunca):
```json
[{"atributo": "Gênero", "comparacao": "feminino × masculino (dentro do país)",
  "diferenca_pp": 0.4, "ic95_min": -0.1, "ic95_max": 0.9, "n_grupo_a": 5100, "n_grupo_b": 6200}]
```
Leitura: IC 95% que cruza o zero = "Sem indício"; que não cruza = "Indício · investigar".

## 6. Registro de decisão do analista (painel → banco)

Campos: `registrado_em`, `analista`, `contrato_id`, `situacao_preco`, `pd`, `juro_cobrado`, `juro_justo`, `recomendacao_sistema`, `decisao ∈ {manter_preco, revisar_preco, encaminhar_compliance}`, `nova_taxa_proposta` (só em revisar), `justificativa` (obrigatória), `origem_parecer`, `versao_modelo`, `versao_prompt`. Sem gênero nem idade. **[EM ANDAMENTO] (Marcos)** tabela no banco; hoje o painel guarda na sessão e exporta CSV/JSON.

## Pronto quando

- `tests/modelos/test_contrato_prever.py`, `tests/genai/test_checagem.py` e `tests/api/test_api.py` validam exemplos e casos reais contra os modelos.
- Nenhum outro arquivo define cópia desses modelos.

## Estado dos documentos

- `FORMATO_JSON.md` v1.4: entrada aprovada (Samuel, 30/10); recomendação v1.2 aprovada (Maria, 03/11); **saída aguardando aprovação da Yasmin** (o painel já usa exatamente esses campos).

## Armadilhas

- API com schema próprio divergente (motivos sem `rotulo`, campos não nulos, `juro_risco` inventado): quebra a checagem do parecer.
- `numeros_citados` com valor diferente do `juro_cobrado` da entrada.
- Campo novo adicionado só de um lado do contrato.
