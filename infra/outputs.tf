# outputs.tf
# O que aparece no fim do "terraform apply" (e a qualquer momento com "terraform output").
# Os comandos são para rodar no PowerShell, na RAIZ do projeto.
# Para copiar um comando sem aspas extras: terraform output -raw comando_ssh

locals {
  ip    = google_compute_address.ip.address
  chave = "$HOME/.ssh/auditor_gcp"
}

output "ip_publico" {
  description = "Endereço da VM"
  value       = local.ip
}

output "painel_url" {
  description = "Painel do analista (Streamlit)"
  value       = "http://${local.ip}:8501"
}

output "api_url" {
  description = "Documentação da API (FastAPI)"
  value       = "http://${local.ip}:8000/docs"
}

output "comando_ssh" {
  description = "Para entrar na VM"
  value       = "ssh -i ${local.chave} ${var.usuario}@${local.ip}"
}

output "comando_esperar_vm" {
  description = "Espera o primeiro boot terminar (Docker, build da imagem, banco e normas)"
  value       = "ssh -i ${local.chave} ${var.usuario}@${local.ip} 'cloud-init status --wait; sudo docker ps'"
}

output "comando_enviar_arquivos" {
  description = "Envia o modelo e os CSVs de custo do dinheiro, que não estão no Git"
  value       = "scp -i ${local.chave} modelos_salvos/pacote_prever_v1.joblib data/raw/ECB_Euribor_Serie-Mensal-12-Meses_csv.csv data/raw/ECB_Euribor_Serie-Mensal-3-Meses.csv data/raw/BC-Selic_Acumulada_Mes_Anuzalizada_base252.csv data/raw/bcdata_sgs_20742.csv ${var.usuario}@${local.ip}:~/envio/"
}

output "comando_completar" {
  description = "Põe o modelo no lugar, carrega Euribor/Selic/BC no banco e reinicia a API"
  value       = "ssh -i ${local.chave} ${var.usuario}@${local.ip} 'bash ~/completar.sh'"
}
