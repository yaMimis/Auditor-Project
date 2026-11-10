# main.tf
# A "lista de compras": tudo o que o Terraform cria na Google Cloud.
# São 5 recursos. O "terraform plan" deve mostrar "Plan: 5 to add".
# Não existe "grupo de recursos" como na Azure: o projeto da GCP faz esse papel,
# e o "terraform destroy" apaga os 5 recursos (o projeto continua existindo).

# 1. Rede própria (VPC). Uma rede nova não aceita nenhuma conexão de fora até
#    que uma regra de firewall libere: por isso a porta do banco (5432) fica fechada.
resource "google_compute_network" "rede" {
  name                    = "${var.prefixo}-rede"
  auto_create_subnetworks = false
}

# 2. Sub-rede: o "pedaço" da rede, na região escolhida, onde a VM se conecta.
resource "google_compute_subnetwork" "subrede" {
  name          = "${var.prefixo}-subrede"
  ip_cidr_range = "10.10.1.0/24"
  region        = var.regiao
  network       = google_compute_network.rede.id
}

# 3. IP público fixo: o endereço que você digita no navegador.
resource "google_compute_address" "ip" {
  name   = "${var.prefixo}-ip"
  region = var.regiao
}

# 4. Firewall: só abre SSH (22), API (8000) e painel (8501), e só para os IPs liberados.
#    Vale para as VMs com a etiqueta "auditor" (na Azure era a ligação NSG + placa de rede).
resource "google_compute_firewall" "entrada" {
  name    = "${var.prefixo}-firewall"
  network = google_compute_network.rede.name

  direction     = "INGRESS"
  source_ranges = var.ips_liberados
  target_tags   = [var.prefixo]

  allow {
    protocol = "tcp"
    ports    = ["22", "8000", "8501"]
  }
}

# 5. A máquina virtual: Ubuntu 24.04 que, ao ligar, roda o cloud-init.yaml
#    (instala Docker, clona o repositório, sobe banco, indexa as normas, sobe API e painel).
resource "google_compute_instance" "vm" {
  name         = "${var.prefixo}-vm"
  machine_type = var.tipo_maquina
  zone         = var.zona
  tags         = [var.prefixo]

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2404-lts-amd64"
      size  = var.tamanho_disco_gb
      type  = "pd-balanced"
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.subrede.id
    access_config {
      nat_ip = google_compute_address.ip.address
    }
  }

  metadata = {
    # Entrada só por chave SSH (sem senha), para o usuário definido em var.usuario.
    ssh-keys       = "${var.usuario}:${trimspace(file(pathexpand(var.caminho_chave_publica)))}"
    enable-oslogin = "FALSE"

    # Script executado uma única vez, no primeiro boot (o Ubuntu da GCP lê o cloud-init daqui).
    user-data = templatefile("${path.module}/cloud-init.yaml", {
      usuario        = var.usuario
      repositorio    = var.repositorio_git
      ramo           = var.ramo_git
      google_api_key = var.google_api_key
      cliente_id_sal = var.cliente_id_sal
    })
  }
}
