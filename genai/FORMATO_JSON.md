# FORMATO_JSON.md — Contrato de dados do parecer (GenAI)

**Projeto:** Auditor de Preço Justo · **Frente:** IA Generativa (Maria) · **Versão:** 1.0 · **Data:** 29/10/2026
**Status:** proposta, aguardando aprovação por escrito de Samuel (entrada) e Yasmin (saída).

## 1. Finalidade

Este documento define os dois formatos de dados da frente de GenAI:

- **Entrada:** o que a função `gerar_parecer()` recebe do `prever()` (Samuel).
- **Saída:** o que `gerar_parecer()` devolve para o painel em Streamlit (Yasmin).

O fluxo é: `prever()` → `gerar_parecer(saida_prever) -> dict` → painel do analista.
A função **sempre** devolve o formato de saída abaixo, venha o parecer do LLM ou do template de reserva.

A fonte da verdade do formato são os modelos pydantic em `genai/src/checagem.py` (seção 6). Este documento os explica.

As regras de conteúdo do parecer (linguagem, ética, números, normas) estão em `REGRAS_PARECER.md`.

---

## 2. Unidades e convenções

| Item | No JSON | No texto do parecer |
|---|---|---|
| Probabilidade de inadimplência (`pd`) | fração de 0 a 1 (ex.: `0.184`) | percentual com vírgula e uma casa (ex.: "18,4%") |
| Juros | fração **ao ano** (ex.: `0.249`) | percentual ao ano com vírgula e uma casa (ex.: "24,9% ao ano") |
| Faixa de risco | letra de `A` a `E` | "faixa C" |
| Datas e horas | ISO 8601 (ex.: `2026-11-05T14:30:00-03:00`) | não aparecem no texto |

A conversão dos números para o texto é feita **pelo código**, não pelo LLM (ver `REGRAS_PARECER.md`, seção 5).

---

## 3. Entrada: saída do `prever()`

> **A confirmar com o Samuel.** Esta é a lista do que o parecer precisa. Se o formato do `prever()` já estiver definido, basta mapear os nomes.

```json
{
  "contrato_id": "BO-483449",
  "versao_modelo": "v1",
  "pd": 0.184,
  "faixa": "C",
  "juro_cobrado": 0.249,
  "juro_justo": 0.162,
  "juro_justo_min": 0.141,
  "juro_justo_max": 0.183,
  "situacao_preco": "acima_do_justo",
  "motivos": [
    {"variavel": "divida_sobre_renda", "efeito": "aumenta_risco"},
    {"variavel": "tempo_no_emprego", "efeito": "reduz_risco"}
  ],
  "alerta_dados": false
}
```

| Campo | Tipo | Significado |
|---|---|---|
| `contrato_id` | texto | Identificador do contrato. **Não é enviado ao LLM.** |
| `versao_modelo` | texto | Versão do modelo de risco. **Não é enviada ao LLM.** |
| `pd` | número (0 a 1) | Chance de o cliente não pagar. |
| `faixa` | `A` a `E` | Faixa de risco. |
| `juro_cobrado` | número (fração ao ano) | Juro que o contrato realmente cobra. |
| `juro_justo` | número (fração ao ano) | Juro justo calculado por fluxo de caixa para esse risco. |
| `juro_justo_min`, `juro_justo_max` | número (fração ao ano) | Limites da margem de incerteza do juro justo. |
| `situacao_preco` | `acima_do_justo`, `abaixo_do_justo` ou `dentro_da_margem` | Calculada pelo Samuel: só é "acima" ou "abaixo" quando o juro cobrado sai da margem de incerteza. |
| `motivos` | lista | Principais fatores do risco (SHAP), com o efeito `aumenta_risco` ou `reduz_risco`. |
| `alerta_dados` | verdadeiro/falso | `true` quando os dados do contrato estão fora da faixa conhecida pelo modelo. |

**Nunca fazem parte da entrada:** `UserName` ou qualquer identificador do cliente, gênero, idade e país.

---

## 4. O que o LLM recebe

O código monta o pedido ao LLM com:

- as regras de `REGRAS_PARECER.md`;
- os números **já formatados para o texto** (ex.: `"juro_cobrado": "24,9% ao ano"`);
- `faixa`, `situacao_preco`, a recomendação já escolhida pelo código e os `motivos` com nomes legíveis;
- os 3 a 5 trechos de normas recuperados no pgvector, cada um com `norma`, `artigo` e `trecho_id`.

O LLM **não** recebe `contrato_id`, `versao_modelo` nem dados pessoais.

---

## 5. Saída: o parecer

### 5.1 Exemplo: juro acima do justo

```json
{
  "contrato_id": "BO-483449",
  "resumo": "Cliente de risco moderado (faixa C, chance de não pagar de 18,4%). Se este contrato fosse de um banco brasileiro, o juro cobrado estaria acima do juro justo para esse risco, mesmo considerando a margem de incerteza.",
  "pontos_de_atencao": [
    "O juro cobrado (24,9% ao ano) está acima da margem do juro justo estimado (14,1% a 18,3% ao ano; valor central 16,2% ao ano).",
    "A diferença não é explicada pelo risco do cliente, que já está considerado no cálculo do juro justo.",
    "O consumidor tem direito a informação clara sobre o preço do crédito, o que reforça a necessidade de justificar a taxa."
  ],
  "recomendacao": "encaminhar_compliance",
  "recomendacao_texto": "Indício de preço acima do justo sem justificativa de risco. Recomenda-se encaminhar ao compliance. A decisão final é do analista.",
  "fontes": [
    {"norma": "CDC", "artigo": "art. 6º, III", "trecho_id": "cdc-006-03"}
  ],
  "numeros_citados": {
    "pd": 0.184,
    "juro_cobrado": 0.249,
    "juro_justo": 0.162,
    "juro_justo_min": 0.141,
    "juro_justo_max": 0.183
  },
  "origem": "llm",
  "versao_prompt": "parecer_v1",
  "gerado_em": "2026-11-05T14:30:00-03:00"
}
```

### 5.2 Exemplo: juro abaixo do justo

```json
{
  "contrato_id": "BO-512870",
  "resumo": "Cliente de risco alto (faixa D, chance de não pagar de 31,0%). Se este contrato fosse de um banco brasileiro, o juro cobrado estaria abaixo do necessário para cobrir esse risco.",
  "pontos_de_atencao": [
    "O juro cobrado (19,0% ao ano) está abaixo da margem do juro justo estimado (24,0% a 30,0% ao ano; valor central 27,0% ao ano).",
    "Esse preço pode não cobrir a perda esperada. É um ponto de atenção para o banco, não uma falha do cliente."
  ],
  "recomendacao": "revisar_preco",
  "recomendacao_texto": "Recomenda-se revisar a política de preço para contratos com este perfil de risco. A decisão final é do analista.",
  "fontes": [],
  "numeros_citados": {
    "pd": 0.31,
    "juro_cobrado": 0.19,
    "juro_justo": 0.27,
    "juro_justo_min": 0.24,
    "juro_justo_max": 0.30
  },
  "origem": "llm",
  "versao_prompt": "parecer_v1",
  "gerado_em": "2026-11-05T14:31:00-03:00"
}
```

> Os números, contratos e trechos dos exemplos são ilustrativos. O `trecho_id` real só existe depois da indexação das normas (02/11).

### 5.3 Campos

| Campo | Tipo | Quem preenche | Regra |
|---|---|---|---|
| `contrato_id` | texto | código | Copiado da entrada. |
| `resumo` | texto | LLM | Até 2 frases, linguagem simples. |
| `pontos_de_atencao` | lista de textos | LLM | De 0 a 3 itens. Vazia quando `dentro_da_margem` e não houver ponto relevante. |
| `recomendacao` | `manter_preco`, `revisar_preco`, `encaminhar_compliance` ou `revisao_manual` | código | Escolhida pela tabela de `REGRAS_PARECER.md`, seção 7. |
| `recomendacao_texto` | texto | LLM | Explica a próxima ação; sempre lembra que a decisão é do analista. |
| `fontes` | lista de `{norma, artigo, trecho_id}` | LLM | Só trechos recuperados no RAG. Pode ser vazia. |
| `numeros_citados` | objeto | LLM | Todo número do texto aparece aqui, com o valor exato da entrada. Chaves permitidas: `pd`, `juro_cobrado`, `juro_justo`, `juro_justo_min`, `juro_justo_max`. |
| `origem` | `llm` ou `template` | código | `template` quando o parecer veio da reserva. |
| `versao_prompt` | texto | código | Ex.: `parecer_v1`, para rastrear qual prompt gerou o parecer. |
| `gerado_em` | data e hora ISO 8601 | código | Momento da geração. |

**Quando não há base normativa:** `fontes` fica vazia, nenhuma norma é citada no texto e a tela mostra "Não encontrei base normativa para este caso."

### 5.4 Formato do `trecho_id`

`<norma>-<artigo com 3 dígitos>-<inciso com 2 dígitos>`, usando `00` quando não houver inciso.
Exemplos: `cdc-006-03` (CDC, art. 6º, III), `lgpd-020-00` (LGPD, art. 20, caput).
Para o Relatório de Economia Bancária, dividido por parágrafo: `reb-spread-<parágrafo com 2 dígitos>` (ex.: `reb-spread-04`).

---

## 6. Modelos pydantic (fonte da verdade)

Ficam em `genai/src/checagem.py`. O LLM responde no formato `RespostaLLM`; o código acrescenta o resto e valida o `Parecer` final.

```python
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ChaveNumero = Literal["pd", "juro_cobrado", "juro_justo", "juro_justo_min", "juro_justo_max"]


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
```

---

## 7. Pendências para aprovação

| Pendência | Com quem |
|---|---|
| Confirmar nomes e tipos dos campos de entrada (seção 3) | Samuel |
| Confirmar a unidade dos juros: o `Interest` do Bondora vem em percentual (ex.: 24,9); definir quem converte para fração | Samuel |
| Lista de nomes legíveis para as variáveis dos `motivos` | Samuel |
| Confirmar que os campos de saída atendem às telas | Yasmin |

## 8. Histórico

| Versão | Data | Mudança |
|---|---|---|
| 1.0 | 29/10/2026 | Primeira versão: entrada, saída, unidades e modelos pydantic. |

Qualquer mudança neste formato só vale com aviso a todo o grupo.