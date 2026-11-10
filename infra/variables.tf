variable "docker_host" {
  description = "Onde está o Docker. Windows (Docker Desktop): npipe; Linux/macOS: unix:///var/run/docker.sock"
  type        = string
  default     = "npipe:////./pipe/docker_engine"
}

variable "imagem_app" {
  description = "Imagem da aplicação, construída antes com: docker compose build api"
  type        = string
  default     = "auditor-preco-justo:latest"
}

variable "google_api_key" {
  description = "Chave do Gemini para o parecer. Passe por TF_VAR_google_api_key; vazia = template de reserva"
  type        = string
  default     = ""
  sensitive   = true
}

variable "porta_api" {
  type    = number
  default = 8000
}

variable "porta_painel" {
  type    = number
  default = 8501
}

variable "porta_banco" {
  type    = number
  default = 5432
}
