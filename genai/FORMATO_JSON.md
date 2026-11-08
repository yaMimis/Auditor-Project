# FORMATO_JSON.md — Contrato de dados do parecer (GenAI)

**Projeto:** Auditor de Preço Justo · **Frente:** IA Generativa (Maria) · **Versão:** 1.5 · **Data:** 08/11/2026
**Status:** entrada aprovada pelo Samuel em 30/10/2026; recomendação v1.2 (acima do justo → revisar_preco) aprovada pela Maria em 03/11/2026; saída aprovada pela Yasmin em 05/11/2026 (painel usa a seção 5); v1.5 (unidade nominal e referência de mercado do BC) aguardando o grupo.

## 1. Finalidade

Este documento define os dois formatos de dados da frente de GenAI:

- **Entrada:** o que a função `gerar_parecer()` recebe do `prever()` (Samuel).
- **Saída:** o que `gerar_parecer()` devolve para o painel em Streamlit (Yasmin).

O fluxo é: `prever()` → `gerar_parecer(saida_prever) -> dict` → painel do analista.
A função **sempre** devolve o formato de saída abaixo, venha o parecer do LLM ou do template de reserva.

A fonte da verdade do formato são os modelos pydantic em `genai/src/checagem.py` (seção 6). Este documento os explica.

As regras de conteúdo do parecer (linguagem, ética, números, normas) estão em `REGRAS_PARECER.md`.

Exemplos reais da saída do `prever()`: `docs/exemplos_prever.json` (mantido pelo Samuel).

---

## 2. Unidades e convenções

| Item | No JSON | No texto do parecer |
|---|---|---|
| Probabilidade de inadimplência (`pd`) | fração de 0 a 1 (ex.: `0.184`) | percentual com vírgula e uma casa (ex.: "18,4%") |
| Juros | fração **ao ano, nominal** (ex.: `0.249`; a taxa ao mês é o anual ÷ 12, como no Bondora), já convertida pelo `prever()` | percentual com vírgula e uma casa, seguido de "ao ano (nominal)" (ex.: "24,9% ao ano (nominal)") |
| Média do BC (`bc_credito_pessoal_aa`) | **percentual** ao ano, **efetiva** (ex.: `126.2`), como vem da view | só na frase do `contexto_mercado`, convertida para nominal (ex.: "84,5% ao ano (nominal) (126,2% efetiva, como o BC divulga)") |
| Faixa de risco | letra de `A` a `E` | "faixa C" |
| Datas e horas | ISO 8601 (ex.: `2026-11-05T14:30:00-03:00`) | não aparecem no texto |

A conversão dos números para o texto é feita **pelo código**, não pelo LLM (ver `REGRAS_PARECER.md`, seção 5). O `Interest` do Bondora, em percentual, nunca chega à frente de GenAI.

---

## 3. Entrada: saída do `prever()`

### 3.1 Caso normal

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
    {"variavel": "divida_sobre_renda", "rotulo": "dívidas em relação à renda", "efeito": "aumenta_risco"},
    {"variavel": "tempo_emprego_atual", "rotulo": "tempo no emprego atual", "efeito": "reduz_risco"}
  ],
  "alerta_dados": false
}
```

### 3.2 Caso de revisão manual

Quando os dados estão fora da faixa de treino, o `prever()` não estima risco nem juro justo:

```json
{
  "contrato_id": "BO-600112",
  "versao_modelo": "v1",
  "pd": null,
  "faixa": null,
  "juro_cobrado": 0.22,
  "juro_justo": null,
  "juro_justo_min": null,
  "juro_justo_max": null,
  "situacao_preco": "revisao_manual",
  "motivos": [],
  "alerta_dados": true
}
```

Nesse caso o LLM não é chamado: o parecer sai do template de reserva com `recomendacao: "revisao_manual"` (ver seção 5.3).

### 3.3 Campos

| Campo | Tipo | Pode ser `null`? | Significado |
|---|---|---|---|
| `contrato_id` | texto | não | Identificador do contrato. **Não é enviado ao LLM.** |
| `versao_modelo` | texto | não | Versão do modelo de risco. **Não é enviada ao LLM.** |
| `pd` | número (0 a 1) | só em revisão manual | Chance de o cliente não pagar. |
| `faixa` | `A` a `E` | só em revisão manual | Faixa de risco. |
| `juro_cobrado` | número (fração ao ano) | não | Juro que o contrato realmente cobra. |
| `juro_justo` | número (fração ao ano) | só em revisão manual | Juro justo calculado por fluxo de caixa para esse risco. |
| `juro_justo_min`, `juro_justo_max` | número (fração ao ano) | só em revisão manual | Limites da margem de incerteza do juro justo. |
| `situacao_preco` | `acima_do_justo`, `abaixo_do_justo`, `dentro_da_margem` ou `revisao_manual` | não | Calculada pelo Samuel: só é "acima" ou "abaixo" quando o juro cobrado sai da margem de incerteza. |
| `motivos` | lista de `{variavel, rotulo, efeito}` | não (pode ser vazia) | Principais fatores do risco (SHAP). `rotulo` é o nome legível que vai para o texto; `efeito` é `aumenta_risco` ou `reduz_risco`. |
| `alerta_dados` | verdadeiro/falso | não | `true` quando os dados do contrato estão fora da faixa de treino do modelo. Sempre vem junto com `situacao_preco = "revisao_manual"`. |
| `bc_credito_pessoal_aa` | número (% ao ano, **efetiva**) | sim (opcional; vazio antes de 03/2011) | Média do BC (série 20742) no mês da concessão, da `vw_custo_do_dinheiro`. **Não vem do `prever()`**: a API acrescenta. **Nunca é enviada ao LLM**; o código a converte para nominal e escreve o `contexto_mercado`. |

**Campos extras ignorados:** o `prever()` também envia `pd_ic95`, `diferenca_pp` e, em cada motivo, `valor` e `peso`. A frente de GenAI não os usa; o modelo pydantic os descarta.

**Nomes em `variavel`:** seguem as colunas do banco (ex.: `tempo_emprego_atual`) e podem mudar. O texto do parecer usa sempre o `rotulo`.

**Nunca fazem parte da entrada:** `UserName` ou qualquer identificador do cliente, gênero, idade e país. Gênero e idade não são variáveis do modelo; o país é variável do modelo, mas foi retirado da lista de motivos pelo Samuel. Se um `rotulo` trouxer o país entre parênteses (ex.: "score de crédito (Estônia)"), o código retira o país antes de usar o rótulo.

---

## 4. O que o LLM recebe

O código monta o pedido ao LLM com:

- as regras de `REGRAS_PARECER.md`;
- os números **já formatados para o texto** (ex.: `"juro_cobrado": "24,9% ao ano (nominal)"`);
- `faixa`, `situacao_preco`, a recomendação já escolhida pelo código e os **3 principais** `motivos` pelo `rotulo` e pelo `efeito` (sem gênero, idade e país);
- os 3 a 5 trechos de normas recuperados no pgvector, cada um com `norma`, `artigo` e `trecho_id`.

O LLM **não** recebe `contrato_id`, `versao_modelo`, os campos extras, a média do BC (`bc_credito_pessoal_aa`) nem dados pessoais. Em revisão manual, o LLM não recebe nada, porque não é chamado.

---

## 5. Saída: o parecer

### 5.1 Exemplo: juro acima do justo

```json
{
  "contrato_id": "BO-483449",
  "resumo": "Cliente de risco moderado (faixa C, chance de não pagar de 18,4%). Se este contrato fosse de um banco brasileiro, o juro cobrado estaria acima do juro justo estimado para esse risco, mesmo considerando a margem de incerteza.",
  "pontos_de_atencao": [
    "O juro cobrado (24,9% ao ano) está acima da margem do juro justo estimado (14,1% a 18,3% ao ano; valor central 16,2% ao ano).",
    "A diferença não é explicada pelo risco estimado pelo modelo. É um indício a investigar, não uma conclusão.",
    "O consumidor tem direito a informação clara sobre o preço do crédito, o que reforça a necessidade de justificar a taxa."
  ],
  "recomendacao": "revisar_preco",
  "recomendacao_texto": "Recomenda-se revisar o preço deste contrato. Se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.",
  "fontes": [
    {"norma": "CDC", "artigo": "art. 6º, III", "trecho_id": "cdc-art6-1"}
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

### 5.3 Exemplo: revisão manual (template, sem LLM)

```json
{
  "contrato_id": "BO-600112",
  "resumo": "Os dados deste contrato estão fora da faixa conhecida pelo modelo. Não é possível estimar o risco e o juro justo com segurança.",
  "pontos_de_atencao": [
    "O juro cobrado é de 22,0% ao ano, mas não há juro justo calculado para comparar."
  ],
  "recomendacao": "revisao_manual",
  "recomendacao_texto": "Recomenda-se análise manual do contrato. A decisão final é do analista.",
  "fontes": [],
  "numeros_citados": {
    "juro_cobrado": 0.22
  },
  "origem": "template",
  "versao_prompt": "template_v1",
  "gerado_em": "2026-11-05T14:32:00-03:00"
}
```

> Os números e contratos dos exemplos são ilustrativos. Os trecho_id seguem o formato real do índice (seção 5.5).

### 5.4 Campos

| Campo | Tipo | Quem preenche | Regra |
|---|---|---|---|
| `contrato_id` | texto | código | Copiado da entrada. |
| `resumo` | texto | LLM ou template | Até 2 frases, linguagem simples. |
| `pontos_de_atencao` | lista de textos | LLM ou template | De 0 a 3 itens. Vazia quando `dentro_da_margem` e não houver ponto relevante. |
| `recomendacao` | `manter_preco`, `revisar_preco`, `encaminhar_compliance` ou `revisao_manual` | código | Escolhida pela tabela de `REGRAS_PARECER.md`, seção 7. `encaminhar_compliance` não é escolhida automaticamente: fica para a decisão do analista. |
| `recomendacao_texto` | texto | LLM ou template | Explica a próxima ação; sempre lembra que a decisão é do analista. |
| `fontes` | lista de `{norma, artigo, trecho_id}` | LLM | Só trechos recuperados no RAG. Pode ser vazia; sempre vazia no template. |
| `numeros_citados` | objeto | LLM ou template | Todo número do texto aparece aqui, com o valor exato da entrada. Chaves permitidas: `pd`, `juro_cobrado`, `juro_justo`, `juro_justo_min`, `juro_justo_max`. Nunca inclui um campo que veio `null`. |
| `origem` | `llm` ou `template` | código | `template` quando o parecer veio da reserva ou da revisão manual. |
| `versao_prompt` | texto | código | `parecer_v1`, `parecer_v2`... para o LLM; `template_v1` para o template. |
| `gerado_em` | data e hora ISO 8601 | código | Momento da geração (fuso −03:00). |
| `contexto_mercado` | texto ou `null` | código | Frase fixa com a média do BC convertida para nominal e a efetiva entre parênteses: "Referência de mercado: no mês da concessão, a taxa média do crédito pessoal no Brasil era de 84,5% ao ano (nominal) (126,2% efetiva, como o BC divulga). É um dado de contexto do mercado brasileiro, não uma medida do preço justo deste contrato." `null` quando a entrada não traz `bc_credito_pessoal_aa`. Nunca é escrita pelo LLM. |

**Quando não há base normativa:** `fontes` fica vazia, nenhuma norma é citada no texto e a tela mostra "Não encontrei base normativa para este caso."

### 5.5 Formato do `trecho_id`

- **Formato:** `<arquivo da norma>-art<número do artigo>-<parte>`, gerado pelo `genai/src/dividir.py`. Ex.: `cdc-art6-1` (CDC, art. 6º, 1ª parte), `cdc-art54b-1` (CDC, art. 54-B), `lgpd-art20-1` (LGPD, art. 20).
- **Por que "parte" e não inciso:** cada trecho é um artigo inteiro; artigos longos são divididos em partes entre incisos e parágrafos. O inciso aparece no campo `artigo` da fonte (ex.: `"artigo": "art. 6º, III"`), não no `trecho_id`.
- **Relatório de Estabilidade Financeira** (`ref.md`), dividido por parágrafo: `ref-p<parágrafo>-1`. Ex.: `ref-p3-1`. Na fonte, o campo `artigo` traz o parágrafo (ex.: `"artigo": "parágrafo 3"`).

---

## 6. Modelos pydantic (fonte da verdade)

Ficam em `genai/src/checagem.py`. `EntradaPrever` valida o que chega do `prever()`; o LLM responde no formato `RespostaLLM`; o código acrescenta o resto e valida o `Parecer` final.

```python
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
    bc_credito_pessoal_aa: float | None = Field(default=None, ge=0)  # % ao ano efetiva (BC); opcional

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
    contexto_mercado: str | None = None  # frase escrita pelo código, nunca pelo LLM
```

---

## 7. Pendências

| Pendência | Com quem | Situação |
|---|---|---|
| Nomes e tipos dos campos de entrada | Samuel | Resolvida em 30/10: o `prever()` segue a seção 3. |
| Unidade dos juros | Samuel | Resolvida em 30/10: o `prever()` já entrega em fração ao ano. |
| Nomes legíveis dos motivos | Samuel | Resolvida em 30/10: campo `rotulo` em cada motivo. |
| `alerta_dados` e `situacao_preco = "revisao_manual"` sempre vêm juntos? | Samuel | Resolvida em 30/10: sim, sempre juntos. |
| Gênero e idade também ficam fora da lista de motivos, como o país? | Samuel | Resolvida em 30/10: sim; nem entram no modelo. |
| Acima do justo → `revisar_preco` em vez de `encaminhar_compliance` (ver `REGRAS_PARECER.md` v1.2) | Maria | Resolvida em 03/11: aprovada pela Maria. |
| Confirmar que os campos de saída atendem às telas | Yasmin | Resolvida em 05/11: o painel usa os campos da seção 5. |
| Passar `bc_credito_pessoal_aa` da view para o `gerar_parecer()` e mostrar o `contexto_mercado` | Yasmin | Aberta (v1.5). |
| Trocar o rótulo "score de crédito (Estônia)" por um sem o país | Samuel | Aberta. O código já retira o país do rótulo, como proteção. |

## 8. Histórico

| Versão | Data | Mudança |
|---|---|---|
| 1.0 | 29/10/2026 | Primeira versão: entrada, saída, unidades e modelos pydantic. |
| 1.1 | 30/10/2026 | Entrada alinhada com o Samuel: campo `rotulo` nos motivos, `revisao_manual` em `situacao_preco` com campos nulos, campos extras ignorados, país fora dos motivos. Novo exemplo de revisão manual, modelo `EntradaPrever` e `trecho_id` para parágrafos. |
| 1.2 | 31/10/2026 | Exemplo 5.1 com `recomendacao: "revisar_preco"` e texto "não é explicada pelo risco estimado pelo modelo"; `encaminhar_compliance` deixa de ser escolhida automaticamente. Pendências do Samuel fechadas. (Proposta do Samuel, aguardando a Maria.) |
| 1.3 | 03/11/2026 | Proposta da v1.2 aprovada pela Maria. `trecho_id` no formato real do índice (`cdc-art6-1`); seção 5.5 reescrita. |
| 1.4 | 03/11/2026 | REB substituído pelo REF (o REB foi descontinuado em 2025); formato `ref-p<parágrafo>-1` na seção 5.5. |
| 1.5 | 08/11/2026 | Juros nominais ("ao ano (nominal)"; DATA.md v0.7, seção 8). Entrada opcional `bc_credito_pessoal_aa` e saída `contexto_mercado`, frase escrita pelo código com a média do BC convertida para nominal (decisão com Marcos e Samuel, 05–06/11). País retirado dos rótulos. O LLM recebe só os 3 principais motivos (prompt v2). |

Qualquer mudança neste formato só vale com aviso a todo o grupo.
