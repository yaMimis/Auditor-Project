terraform {
  required_version = ">= 1.6"
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

# Docker local: nenhuma conta em nuvem, nenhum custo.
provider "docker" {
  host = var.docker_host
}
