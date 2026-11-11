# Rodar o Auditor em qualquer PC da equipe

## Docker e Terraform: para que serve cada um

| | Docker Compose (`iniciar.bat`) | Terraform (`infra/`) |
| --- | --- | --- |
| O que faz | sobe banco, API e painel **no seu PC** | cria **uma máquina na Google Cloud** que roda o mesmo Docker Compose |
| Quando usar | no dia a dia, nos testes e como plano B da demo | para mostrar o sistema na nuvem e a "infraestrutura como código" |
| Custo | nenhum | gasta o crédito grátis da Google enquanto a máquina existir |
| Guia | este arquivo | [`infra/README.md`](../infra/README.md) |

**Quem roda a aplicação é sempre o Docker.** O `docker-compose.yml` descreve os 3 containers.
O Terraform não substitui o Docker: ele cria o *computador* (rede, IP, firewall e VM) onde o Docker vai rodar.
Em uma frase: **"Docker empacota a aplicação; Terraform cria a infraestrutura onde ela roda."**

## 1. Uma vez por PC

| O quê | De onde |
| --- | --- |
| Docker Desktop | docker.com → *Download Docker Desktop* (Windows: aceite o WSL 2). Abra e espere ficar verde. |
| Git | git-scm.com |
| Projeto | `git clone https://github.com/yaMimis/Auditor-Project.git` |
| `.env` | peça à Yasmin (tem a `GOOGLE_API_KEY` e a `CLIENTE_ID_SAL`). Nunca vai para o GitHub. |
| `modelos_salvos\pacote_prever_v1.joblib` | peça ao Samuel (Drive) |
| 4 CSVs de custo do dinheiro em `data\raw\` | peça ao Marcos (Drive), nomes abaixo |

Os 4 CSVs (são pequenos, séries mensais do Banco Central e do Banco Central Europeu):

- `ECB_Euribor_Serie-Mensal-12-Meses_csv.csv` (ou sem o `_csv`)
- `ECB_Euribor_Serie-Mensal-3-Meses.csv`
- `BC-Selic_Acumulada_Mes_Anuzalizada_base252.csv`
- `bcdata_sgs_20742.csv` (ou `bcdata.sgs.20742.csv`): a taxa média do crédito pessoal, que vira a "referência de mercado" no parecer

Na primeira vez, o `iniciar` carrega esses arquivos no banco sozinho. Os mesmos 4 arquivos vão para a nuvem (passo 14 do `infra/README.md`).

Os arquivos da aba "Auditoria da carteira" (`docs\resultados\`, gerados pelo Samuel) já vêm com o `git clone`.

A base grande do Bondora (`LoanData`) **não** é necessária para rodar o sistema. Ela só serve para refazer
os dados e o modelo (passos 2 a 5 do README).

## 2. Todo dia

**Clique duplo no `iniciar.bat`** (ou `.\iniciar.ps1` no PowerShell). Ele:

1. confere se o Docker está ligado e se as portas 5432, 8000 e 8501 estão livres;
2. confere o `.env` e o modelo;
3. sobe o banco e aplica a tabela de decisões;
4. constrói a imagem só se ela não existir;
5. indexa as normas e carrega a referência do BC, se faltarem;
6. sobe API e painel e abre http://localhost:8501.

| Situação | Comando |
| --- | --- |
| Subir | `iniciar.bat` ou `.\iniciar.ps1` |
| Veio código novo no `git pull` | `.\iniciar.ps1 -Build` |
| Desligar (os dados ficam) | `.\iniciar.ps1 -Parar` |
| Ver o que deu errado | `docker compose logs api --tail 40` |

## 3. Problemas comuns

| Mensagem | O que fazer |
| --- | --- |
| "O Docker não está rodando" | Abra o Docker Desktop e espere ficar verde |
| "A porta X está com o container Y" | `docker stop Y` (o script mostra o comando) e rode de novo |
| "A porta X está ocupada pelo programa Y" | Feche o programa (o script mostra o comando) |
| "Sem a referência de mercado do BC" | Coloque os 4 CSVs em `data\raw\` e rode de novo |
| "não está assinado" / ExecutionPolicy | Use o `iniciar.bat`, ou antes: `Set-ExecutionPolicy Bypass -Scope Process` |
| "Falta modelos_salvos\...joblib" | Peça o arquivo ao Samuel; até lá, use "Caso de exemplo" |
| API demora na 1ª vez | Normal: ela baixa o modelo de busca nas normas (~0,5 GB) uma única vez |
