# Qualidade dos dados · Auditor de Preço Justo

Gerado em 2026-11-04 a partir do banco. As regras estão em `src/dados/validacao.py` e as decisões sobre os dados, em `DATA.md`.

## Resumo

- Contratos: 179.235; clientes distintos: 85.087.
- Regras de **erro** violadas: 0. Erro quebra o contrato dos dados (chaves, domínios, datas, faixas, contagens) e falha o teste.
- Regras de **alerta** com ocorrências: 12. Alerta é ocorrência conhecida, registrada sem falhar.
- Base de modelagem (`vw_base_modelagem`): treino 20.011; teste 7.311; fora_cliente_repetido 2.594.

## Erros

Nenhum erro.

## Alertas

| Tabela | Coluna | Regra violada | Linhas | % da tabela | Exemplo (`loan_id`) | O que fazer |
| --- | --- | --- | --- | --- | --- | --- |
| cliente | `idade` | greater_than_or_equal_to(18) | 53 | 0,03% | `4c3bc355-383e-493f-aaab-9d3d017b3cf4` | Marcar. Excluir ou manter ainda é decisão aberta (DATA.md, seção 7). |
| cliente | `renda_total` | greater_than(0) | 64 | 0,04% | `4c3bc355-383e-493f-aaab-9d3d017b3cf4` | Marcar. Excluir ou manter ainda é decisão aberta (DATA.md, seção 7). |
| emprestimo | (várias colunas) | Current nao tem data_default | 163 | 0,09% | `4e1d7ef9-6348-4bcb-9907-8ab6395bc5d9` | Registrar. Conferir se são contratos reestruturados. |
| emprestimo | (várias colunas) | Repaid nao tem saldo_principal | 4 | 0,00% | `e846f28d-18c0-4626-8eff-a124010d6c55` | Registrar. |
| emprestimo | (várias colunas) | valor_concedido <= valor_solicitado | 208 | 0,12% | `621eef09-2715-49cd-9c88-9c1f01231eaf` | Registrar. |
| emprestimo | (várias colunas) | vencimento original = concessao + prazo (tolerancia de 2 meses) | 133 | 0,07% | `bcb7c866-68ed-4f89-9dae-049d1ffe664f` | Registrar. Não afeta a base de modelagem. |
| emprestimo | `parcela_mensal` | greater_than(0) | 3.627 | 2,02% | `5d5f1420-6fce-4de7-8f17-9bcc00c80560` | Registrar. A coluna está na lista negra. |
| emprestimo | `perda_esperada_bondora` | in_range(0, 1) | 1 | 0,00% | `6cdb6abc-9686-40d0-a11e-a376012f4458` | Registrar. |
| emprestimo | `prazo_meses` | greater_than_or_equal_to(3) | 221 | 0,12% | `01594183-1c98-454e-bb45-9bb801594f50` | Registrar. Atenção ao fluxo de caixa de prazos muito curtos. |
| emprestimo | `saldo_principal` | greater_than_or_equal_to(0) | 5 | 0,00% | `168f8a4f-d119-419d-8386-9d66007bb47b` | Registrar. |
| historico_credito | `caixa_livre` | greater_than_or_equal_to(0) | 23 | 0,01% | `de9c60ba-c104-4def-a703-9eb400c37d1d` | Registrar. |
| historico_credito | `divida_renda` | less_than_or_equal_to(100) | 2 | 0,00% | `31ac4814-f1ac-4316-b32f-9edd00f336b7` | Registrar. |

## Achados que não são regra

### Proporção de mulheres por ano e país

Entre os contratos com gênero 0 ou 1. Quedas abruptas e voltas ao nível anterior indicam problema de codificação, e não mudança da clientela (DATA.md, seção 7).

| Ano | EE | ES | FI |
| --- | --- | --- | --- |
| 2013 | 48% | 16% | 45% |
| 2014 | 47% | 32% | 45% |
| 2015 | 46% | 33% | 42% |
| 2016 | 45% | 35% | 45% |
| 2017 | 26% | 8% | 21% |
| 2018 | 9% | 13% | 23% |
| 2019 | 34% | 3% | 41% |
| 2020 | 51% | 4% | 51% |
| 2021 | 49% | – | 44% |

### Zeros no lugar de vazio

% de contratos com valor exatamente zero. Colunas que passam a ter 100% de zeros deixam de ser informação (DATA.md, seção 6).

| Ano | `divida_renda` | `caixa_livre` | `renda_empregador_principal` | `pagamentos_anteriores` | `quitacoes_antecipadas_valor` |
| --- | --- | --- | --- | --- | --- |
| 2013 | 1% | 1% | 6% | 81% | 100% |
| 2014 | 0% | 0% | 6% | 84% | 99% |
| 2015 | 0% | 0% | 6% | 64% | 77% |
| 2016 | 0% | 0% | 7% | 62% | 93% |
| 2017 | 70% | 70% | 72% | 43% | 94% |
| 2018 | 100% | 100% | 100% | 11% | 89% |
| 2019 | 100% | 100% | 100% | 0% | 0% |
| 2020 | 100% | 100% | 100% | 0% | 0% |
| 2021 | 100% | 100% | 100% | 0% | 0% |

### Colunas em branco depois de 2017

% de contratos sem valor (inclui o código -1, que a carga troca por vazio).

| Ano | `finalidade` | `situacao_emprego` | `area_ocupacao` | `experiencia_trabalho` |
| --- | --- | --- | --- | --- |
| 2013 | 0% | 1% | 0% | 0% |
| 2014 | 0% | 0% | 1% | 0% |
| 2015 | 0% | 0% | 0% | 0% |
| 2016 | 0% | 0% | 0% | 0% |
| 2017 | 70% | 70% | 70% | 70% |
| 2018 | 100% | 100% | 100% | 100% |
| 2019 | 100% | 100% | 100% | 100% |
| 2020 | 100% | 100% | 100% | 100% |
| 2021 | 100% | 100% | 100% | 100% |

## Como reproduzir

```
python src/dados/validacao.py                  # só as regras
python src/dados/relatorio_qualidade.py         # regras e este relatório
```
