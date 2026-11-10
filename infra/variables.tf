# variables.tf
# As "perguntas" que o Terraform faz. As respostas ficam em terraform.tfvars
# (fora do Git). As que têm "default" já vêm respondidas e só mudam se precisar.

variable "projeto_id" {
  description = "ID do projeto na GCP (gcloud config get-value project)"
  type        = string
}

variable "ips_liberados" {
  description = "Quem pode acessar painel, API e SSH, no formato CIDR. Ex.: [\"200.100.50.25/32\"]"
  type        = list(string)
}

variable "regiao" {
  description = "Região da GCP. southamerica-east1 = São Paulo (menor latência na demo)."
  type        = string
  default     = "southamerica-east1"
}

variable "zona" {
  description = "Zona dentro da região (a, b ou c). Se der ZONE_RESOURCE_POOL_EXHAUSTED, troque a letra."
  type        = string
  default     = "southamerica-east1-b"
}

variable "prefixo" {
  description = "Começo do nome de todos os recursos, para achá-los fácil no console"
  type        = string
  default     = "auditor"
}

variable "tipo_maquina" {
  description = "Tamanho da VM. e2-medium = 2 vCPUs e 4 GB de RAM (a e2-micro gratuita não aguenta o PyTorch)."
  type        = string
  default     = "e2-medium"
}

variable "tamanho_disco_gb" {
  description = "Disco da VM. As imagens Docker com bibliotecas de ML ocupam espaço."
  type        = number
  default     = 64
}

variable "usuario" {
  description = "Usuário Linux criado na VM (é o que vai no ssh e no scp)"
  type        = string
  default     = "auditor"
}

variable "caminho_chave_publica" {
  description = "Arquivo .pub da chave SSH criada com ssh-keygen"
  type        = string
  default     = "~/.ssh/auditor_gcp.pub"
}

variable "repositorio_git" {
  description = "Repositório clonado pela VM (é público, então não precisa de senha)"
  type        = string
  default     = "https://github.com/yaMimis/Auditor-Project.git"
}

variable "ramo_git" {
  description = "Ramo que a VM vai rodar"
  type        = string
  default     = "main"
}

variable "google_api_key" {
  description = "Chave do Gemini para o parecer. Passe por TF_VAR_google_api_key; vazia = template de reserva"
  type        = string
  default     = ""
  sensitive   = true # o Terraform não mostra o valor na tela
}

variable "cliente_id_sal" {
  description = "Chave de pseudonimização do grupo. Passe por TF_VAR_cliente_id_sal (opcional na VM)"
  type        = string
  default     = ""
  sensitive   = true
}
