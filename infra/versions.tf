# versions.tf
# "Com quem o Terraform vai conversar": aqui, com a Google Cloud.
# O login vem do "gcloud auth application-default login"; nenhuma senha fica neste arquivo.
# (Substitui o versions.tf antigo, que usava o provider Docker local.)

terraform {
  required_version = ">= 1.6"

  required_providers {
    google = {
      source  = "hashicorp/google" # plugin oficial da Google Cloud
      version = ">= 6.0, < 8.0"    # 6.x ou 7.x (evita surpresas de versão nova)
    }
  }
}

provider "google" {
  project = var.projeto_id
  region  = var.regiao
  zone    = var.zona
}
