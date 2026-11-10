# Infraestrutura do Auditor de Preço Justo como código.
# Descreve o mesmo ambiente do docker-compose.yml (banco, API e painel) com o provider
# Docker do Terraform, rodando no próprio computador. Para a nuvem, troca-se o provider
# e os recursos de container mantendo a mesma estrutura.

locals {
  raiz         = abspath("${path.module}/..")
  url_do_banco = "postgresql://postgres:postgres@auditor_tf_postgres:5432/auditor_db"
}

resource "docker_network" "auditor" {
  name = "auditor_tf_rede"
}

resource "docker_volume" "dados_banco" {
  name = "auditor_tf_postgres_data"
}

resource "docker_volume" "cache_modelos" {
  name = "auditor_tf_cache_modelos_hf"
}

resource "docker_image" "postgres" {
  name         = "pgvector/pgvector:pg16"
  keep_locally = true
}

# Construída antes pelo compose (o Dockerfile usa recursos do BuildKit).
resource "docker_image" "app" {
  name         = var.imagem_app
  keep_locally = true
}

resource "docker_container" "postgres" {
  name    = "auditor_tf_postgres"
  image   = docker_image.postgres.image_id
  restart = "unless-stopped"
  env     = ["POSTGRES_USER=postgres", "POSTGRES_PASSWORD=postgres", "POSTGRES_DB=auditor_db"]

  networks_advanced {
    name = docker_network.auditor.name
  }
  ports {
    internal = 5432
    external = 5433
  }
  volumes {
    volume_name    = docker_volume.dados_banco.name
    container_path = "/var/lib/postgresql/data"
  }
  volumes {
    host_path      = "${local.raiz}/db"
    container_path = "/docker-entrypoint-initdb.d"
    read_only      = true
  }
  healthcheck {
    test     = ["CMD-SHELL", "pg_isready -U postgres -d auditor_db"]
    interval = "5s"
    timeout  = "5s"
    retries  = 20
  }
  wait = true
}

resource "docker_container" "api" {
  name    = "auditor_tf_api"
  image   = docker_image.app.image_id
  restart = "unless-stopped"
  env = compact([
    "DATABASE_URL=${local.url_do_banco}",
    var.google_api_key == "" ? "" : "GOOGLE_API_KEY=${var.google_api_key}",
  ])

  networks_advanced {
    name    = docker_network.auditor.name
    aliases = ["api"]
  }
  ports {
    internal = 8000
    external = var.porta_api
  }
  volumes {
    host_path      = "${local.raiz}/modelos_salvos"
    container_path = "/app/modelos_salvos"
    read_only      = true
  }
  volumes {
    volume_name    = docker_volume.cache_modelos.name
    container_path = "/root/.cache/huggingface"
  }
  depends_on = [docker_container.postgres]
}

resource "docker_container" "painel" {
  name    = "auditor_tf_streamlit"
  image   = docker_image.app.image_id
  restart = "unless-stopped"
  command = ["streamlit", "run", "src/app/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
  env     = ["API_URL=http://api:8000"]

  networks_advanced {
    name = docker_network.auditor.name
  }
  ports {
    internal = 8501
    external = var.porta_painel
  }
  volumes {
    host_path      = "${local.raiz}/docs/resultados"
    container_path = "/app/docs/resultados"
    read_only      = true
  }
  depends_on = [docker_container.api]
}
