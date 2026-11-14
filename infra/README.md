# infra/ — o Auditor na Google Cloud com Terraform

O Terraform cria na Google Cloud (GCP) uma máquina virtual Ubuntu que, ao ligar, instala o Docker, clona este repositório e sobe o mesmo `docker-compose.yml` do dia a dia: banco (PostgreSQL + pgvector), API e painel. Nada do código da aplicação muda.

Não é preciso Docker no computador de quem roda o Terraform: o Docker roda dentro da VM. O dia a dia continua pelo `.\iniciar.ps1`; a nuvem é para a demo e para mostrar a infraestrutura como código.

## O que é criado (5 recursos)

| Recurso                                                          | Para quê                                                                                                     |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Rede `auditor-rede`                                            | Rede própria. Rede nova não aceita conexão de fora até uma regra liberar                                  |
| Sub-rede `auditor-subrede`                                     | O pedaço da rede, em São Paulo, onde a VM se conecta                                                        |
| IP fixo `auditor-ip`                                           | Endereço do painel e da API                                                                                  |
| Firewall `auditor-firewall`                                    | Abre só 22 (SSH), 8000 (API) e 8501 (painel), e só para `ips_liberados`. O banco (5432) não fica exposto |
| VM `auditor-vm` `e2-medium` (2 vCPUs, 4 GB) com Ubuntu 24.04 | Roda o Docker Compose                                                                                         |

Na Azure eram 8 recursos: a GCP não tem grupo de recursos (o projeto faz esse papel) nem placa de rede separada (o firewall se liga à VM por etiqueta).

## O que vai para a nuvem e por qual caminho

| O quê                                              | Como chega na VM                                                                                                            |
| --------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Código                                             | A VM clona o repositório (público) no primeiro boot                                                                       |
| Chave do Gemini e chave do grupo                    | Variáveis `TF_VAR_...` → `.env` da VM                                                                                 |
| Esquema do banco (`db/01` a `05`)               | Roda sozinho na 1ª criação do volume do Postgres                                                                         |
| Normas no pgvector                                  | A VM indexa sozinha no primeiro boot                                                                                        |
| Modelo `pacote_prever_v1.joblib`                  | Fora do Git: vai por `scp` (passo 14)                                                                                     |
| CSVs de Euribor, Selic e taxa do BC                 | Fora do Git: vão por `scp` junto com o modelo e o `completar.sh` carrega no banco                                      |
| Base da Bondora (`LoanData_Bondora.csv`, ~150 MB) | Fora do Git: vai por `scp` (passo 14) e o `completar.sh` carrega no banco; sem ela, a busca de contratos não acha nada |

## Arquivos

- `versions.tf`: usa o plugin da Google Cloud (login pelo `gcloud`).
- `variables.tf`: as configurações (projeto, região, tamanho, IPs, segredos).
- `main.tf`: os recursos.
- `cloud-init.yaml`: o que a VM faz no primeiro boot (`montar.sh`) e o passo final (`completar.sh`).
- `outputs.tf`: endereços e comandos prontos que aparecem no fim.
- `terraform.tfvars.example`: modelo das respostas; o `terraform.tfvars` real fica fora do Git.

## Passo a passo (PowerShell, Windows)

Os passos 1 a 11 não gastam crédito. O gasto começa no 12, e o 16 desliga tudo.

### Conta (uma vez, quem tem o cartão)

1. Em `cloud.google.com/free`, clique em **Começar gratuitamente** e cadastre o cartão. São US$ 300 por 90 dias. A cobrança só acontece se alguém clicar em **Ativar conta completa / Upgrade**: **ninguém clica nisso**.
2. No console: **Faturamento → Orçamentos e alertas → Criar orçamento** de US$ 20, com alerta por e-mail em 50%, 90% e 100%.
3. Para outra pessoa do grupo rodar o Terraform, dê a ela o papel **Editor** no projeto (IAM e administrador → Conceder acesso), com o Gmail dela.

### Preparar (uma vez, quem vai rodar o Terraform)

4. Instalar as ferramentas e reabrir o terminal:
   ```powershell
   winget install Hashicorp.Terraform
   winget install Google.CloudSDK
   terraform -version
   gcloud version
   ```
5. Entrar e escolher o projeto. O ID do projeto aparece no topo do console (ex.: `auditor-preco-justo-4821`):
   ```powershell
   gcloud auth login
   gcloud auth application-default login
   gcloud config set project <ID_DO_PROJETO>
   gcloud services enable compute.googleapis.com
   ```

   O `application-default login` é o login que o Terraform usa; o `services enable` liga a API de VMs (leva um ou dois minutos).
6. Criar a chave SSH da VM (Enter nas perguntas):
   ```powershell
   ssh-keygen -t rsa -b 4096 -f $HOME\.ssh\auditor_gcp
   ```
7. Descobrir o próprio IP e acrescentar `/32` (ex.: `200.100.50.25/32`):
   ```powershell
   Invoke-RestMethod https://api.ipify.org
   ```

### Colocar os arquivos no projeto

8. Criar o ramo:
   ```powershell
   git checkout main
   git pull
   git checkout -b feature/infra-gcp
   ```
9. Trocar o conteúdo da pasta `infra/` por estes arquivos. Apague o `infra/.terraform.lock.hcl` antigo (era do provider Docker); o `terraform init` gera um novo. O `.gitignore` da raiz já tem as linhas do Terraform.
10. Preencher as respostas e passar os segredos pelo terminal (não por arquivo):
    ```powershell
    cd infra
    copy terraform.tfvars.example terraform.tfvars
    notepad terraform.tfvars          # projeto_id e ips_liberados
    $env:TF_VAR_google_api_key = "<chave do Gemini>"
    $env:TF_VAR_cliente_id_sal = "<chave do grupo>"
    ```

    As variáveis `$env:` valem só para aquela janela do PowerShell. Sem a chave do Gemini, o parecer sai pelo template de reserva.

### Ensaio sem custo

11. Conferir a receita:
    ```powershell
    terraform init
    terraform fmt
    terraform validate
    terraform plan
    ```

    Esperado: `Success! The configuration is valid.` e `Plan: 5 to add, 0 to change, 0 to destroy.` A saída do `plan` serve de print para a banca.

### Subir na nuvem

12. Criar os recursos (digitar `yes`). Em 1 a 2 minutos aparecem o IP, os endereços e os comandos prontos:
    ```powershell
    terraform apply
    ```
13. Esperar a VM se montar (15 a 20 minutos: Docker, build da imagem com PyTorch, banco e normas). Na raiz do projeto:
    ```powershell
    cd ..
    terraform -chdir=infra output -raw comando_esperar_vm   # copie e rode o comando que aparece
    ```

    O comando fica parado até o fim e mostra `status: done` e os três containers: `auditor_postgres`, `auditor_api` e `auditor_streamlit`. Se mostrar `status: error`, veja o log com `sudo tail -100 /var/log/cloud-init-output.log` dentro da VM.
14. Enviar o modelo, os CSVs de custo do dinheiro e a base do Bondora (fora do Git) e completar:
    ```powershell
    terraform -chdir=infra output -raw comando_enviar_arquivos   # copie e rode
    terraform -chdir=infra output -raw comando_completar         # copie e rode
    ```

    O `scp` espera os arquivos em `modelos_salvos/` e `data/raw/` com os nomes do projeto. Se algum nome for diferente no seu computador, ajuste o comando. O envio da base do Bondora (~150 MB) leva alguns minutos. O `completar.sh` carrega os contratos (pode levar alguns minutos) e termina mostrando a resposta da API, com `"modelo_carregavel": true` e `"banco_disponivel": true`.
15. Testar no navegador: `terraform -chdir=infra output painel_url` deve abrir o painel, e `api_url` deve abrir a documentação da API.
    - **Abrir um contrato pela busca.** No painel, buscar cada ID abaixo e abrir a tela "Análise do contrato". Os números do contrato (PD, faixa, juro justo e situação do preço) são calculados na hora.

      | Caso               | `loan_id`                                           | O que deve aparecer                                                                   |
      | ------------------ | ----------------------------------------------------- | ------------------------------------------------------------------------------------- |
      | 2016, inadimplente | `0010881b-6ca8-43c1-a2cc-a6c000e3159f` (Espanha)    | Desfecho: inadimplente, resultado de −1.590,00 € e principal perdido de 1.590,00 € |
      | 2016, quitado      | `00334763-1d1c-4634-b3a9-a6db00f30214` (Finlândia) | Desfecho: quitado, resultado de +680,03 € e nada de principal perdido                |
      | 2019, sem desfecho | `00011ef9-b8c8-4ecc-b28d-aaa000ec5469` (Espanha)    | "Sem desfecho", com o motivo "concedido depois de 2016"                               |

      Os IDs saem da `vw_desfecho_contrato` (`db/06`) e são sempre os mesmos (`ORDER BY loan_id`; os de 2016 são do teste e não reestruturados):


      ```sql
      SELECT loan_id FROM vw_desfecho_contrato
      WHERE ano = 2016 AND inadimplente = 1 AND conjunto = 'teste' AND NOT reestruturado ORDER BY loan_id LIMIT 1;  -- quitado: inadimplente = 0
      SELECT loan_id FROM vw_desfecho_contrato WHERE ano = 2019 AND NOT tem_desfecho ORDER BY loan_id LIMIT 1;
      ```

      Busca em maiúsculas: buscar `0010881B-6CA8-43C1-A2CC-A6C000E3159F` (o primeiro ID em maiúsculas; vale também digitar um espaço antes ou depois) deve abrir **o mesmo contrato**. Registrar uma decisão nele: na página "Contratos da base", a lista deve mostrar o contrato como já decidido, e a decisão aparece na página "Registro" (o `contrato_id` gravado é o `loan_id` do banco, em minúsculas; `db/07`).

      Pré-requisito: o banco da VM precisa ter os contratos do Bondora, a `vw_desfecho_contrato` (`db/06`) e o gatilho do `db/07`. Se a busca não achar nenhum dos três IDs, confira com `sudo docker exec auditor_postgres psql -U postgres -d auditor_db -c "SELECT COUNT(*) FROM vw_desfecho_contrato"` dentro da VM (esperado: 179.235).

### Desligar e entregar

16. Destruir ao fim de cada teste (digitar `yes`) e conferir no console (Compute Engine → Instâncias de VM) que a `auditor-vm` sumiu:
    ```powershell
    cd infra
    terraform destroy
    ```
17. Commit e PR. O `git status` não pode mostrar `terraform.tfvars` nem `.tfstate`; o novo `.terraform.lock.hcl` vai junto:
    ```powershell
    cd ..
    git add -A infra/
    git status
    git commit -m "Infra: Terraform na Google Cloud (VM com Docker Compose)"
    git push -u origin feature/infra-gcp
    ```

## Cuidados

- **Segredos:** `terraform.tfvars` e `terraform.tfstate` ficam fora do Git. O `.tfstate` guarda a chave do Gemini, porque ela vai para o metadado da VM: quem tem acesso ao projeto também consegue vê-la.
- **Estado em uma máquina só:** o `terraform.tfstate` fica no computador onde o `apply` rodou. O `destroy` precisa sair dele (ou de uma cópia da pasta `infra/` inteira, com o `.tfstate`).
- **IP que muda:** se o IP de quem acessa mudar (outra rede, celular), atualize `ips_liberados` e rode `terraform apply` de novo. Só o firewall muda, a VM fica.
- **Custo:** a VM, o disco e o IP gastam crédito por hora enquanto existirem, mesmo sem uso. Crie perto do uso e destrua logo depois.
- **Fim do trial:** depois de 90 dias ou dos US$ 300, a Google para os recursos e apaga os dados. Nada é cobrado sem o upgrade manual.
- **Zona sem máquina:** se o `apply` der `ZONE_RESOURCE_POOL_EXHAUSTED`, troque a `zona` no `terraform.tfvars` (ex.: `southamerica-east1-a` ou `-c`) e rode de novo.
