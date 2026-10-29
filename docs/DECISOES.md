
# DECISOES.md — Modelo de risco e juro justo

Responsável: Samuel · Atualizado: 29/10/2026

## 1. Alvo

default = 1 se data_default preenchida; senão 0.

## 2. Contratos usados

- Coortes maduras: 2009–2016, só encerrados (status = 'Repaid' ou default = 1).
- Total: 30.210 contratos, default 56%.
- Fora: Eslováquia (294 contratos, só 2014: insuficiente) e reestruturados.
- Sem rebalanceamento (defaults são maioria).

## 3. Colunas proibidas como variável

- COLUNAS_LISTA_NEGRA (carga_bondora.py) + parcela_mensal.
- COLUNAS_SO_AUDITORIA: genero, idade [+ estado_civil, n_dependentes, se aprovado].
- Identificadores: loan_id, numero, cliente_id.
  Garantido por teste automático.

## 4. Divisão

- Treino/validação: 2009–2015 → 20.011 contratos, default 52,4%. GroupKFold por cliente.
- Teste: 2016, sem clientes que aparecem no treino (1.874 removidos)
  → 7.311 contratos (EE 3.642, ES 2.226, FI 1.443), default 67,1%.
- Metade dos contratos é de clientes repetidos → divisão por cliente obrigatória.

## 5. Modelo

- Baseline: regressão logística.
- Principal: XGBoost regularizado + early stopping.
- Calibração no final (isotônica/sigmoide).
- País entra como variável.
- Comparar com pd_bondora (só comparação).

## 6. Métricas

- Ordenação: AUC, KS.
- Preço: Brier + curva de calibração (prioridade).
- Avaliar também por país.

## 7. Juro justo

- Fluxo de caixa: PD → taxa mensal; amortização; desconto.
- Custo do dinheiro: Euribor do mês de concessão (piso 0).
- LGD: lgd_bondora ou calculada com defaults antigos.
- Custos e margem: calibrados p/ média justo = média cobrado.
- Sensibilidade: margem ±1 pp; LGD ±10 pp.
- juro_aa vem em % → dividir por 100.

## 8. Regra de achado

- dentro_da_margem | acima_do_justo | abaixo_do_justo | revisao_manual.
- Fora da margem só se diferença > incerteza (IC 95% bootstrap).
- revisao_manual: fora da faixa de treino.

## 9. Formato do prever()

contrato_id, pd, pd_ic95, faixa, juro_cobrado, juro_justo,
juro_justo_ic, diferenca_pp, situacao, motivos[], fora_da_faixa_de_treino,
versao_modelo. Mudança só com aviso ao grupo.

## 10. Observações dos dados

- 2009–2012: só Estônia. Espanha e Finlândia entram em 2013–2014.
- Default por país: EE 42%, ES 78%, FI 73%.
- O salto de inadimplência a partir de 2014 vem em boa parte da entrada de ES e FI.
- Teste mais arriscado que o treino (só clientes novos + mais ES/FI):
  esperar perda de calibração; avaliar por país.

## 11. Pendências

- [X] Anos das coortes maduras
- [ ] Marcos: parcela_mensal na lista negra; sal obrigatório; Euribor até 01/11
- [ ] Grupo: estado_civil/n_dependentes em so_auditoria?
- [ ] Maria e Yasmin: aprovar JSON do prever()
