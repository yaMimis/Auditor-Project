# infra/ — o ambiente como código (Terraform)

Descreve com Terraform o mesmo ambiente do `docker-compose.yml`: rede, volumes, banco (PostgreSQL + pgvector), API e painel. Usa o provider **Docker** e roda **no próprio computador**: não precisa de conta em nuvem nem gera custo. É a base para levar o projeto a uma nuvem depois, trocando o provider.

O dia a dia continua pelo `.\iniciar.ps1` ou pelo `docker compose`. O Terraform é uma alternativa de implantação, não um passo obrigatório.

## Como usar

Pré-requisitos: [Terraform](https://developer.hashicorp.com/terraform/install) ≥ 1.6 e Docker Desktop ligado.

1. Pare o ambiente do compose (usa as mesmas portas): `docker compose down`
2. Construa a imagem da aplicação (uma vez): `docker compose build api`
3. Na pasta `infra/`:
   ```
   terraform init
   $env:TF_VAR_google_api_key = "<chave do Gemini>"   # opcional; sem ela o parecer sai pelo template
   terraform apply
   ```
   No Linux/macOS, acrescente `-var 'docker_host=unix:///var/run/docker.sock'` (e use `export TF_VAR_google_api_key=...`).
4. Abra os endereços que o `terraform apply` mostra no fim (painel em http://localhost:8501).
5. Para remover tudo: `terraform destroy` (apaga também o volume do banco deste ambiente).

## Observações

- Os containers e volumes têm o prefixo `auditor_tf_`, para não se misturar com os do compose.
- O banco começa vazio, como no compose: o esquema de `db/` roda sozinho na 1ª criação; as cargas e a indexação das normas seguem o README da raiz, apontando para a porta 5432.
- A chave do Gemini nunca vai para arquivo: só pela variável de ambiente `TF_VAR_google_api_key`. Os arquivos de estado (`*.tfstate`) ficam fora do Git, pois podem conter a chave.
