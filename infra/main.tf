# main.tf
# A "lista de compras": tudo o que o Terraform cria na Google Cloud.
# São 6 recursos (8 com painel_publico = true). O "terraform plan" deve mostrar "Plan: 6 to add".
# Não existe "grupo de recursos" como na Azure: o projeto da GCP faz esse papel,
# e o "terraform destroy" apaga todos eles (o projeto continua existindo).

# ips_liberados aceita IPv4 e IPv6 misturados; a GCP exige uma regra de firewall para cada tipo.
locals {
  ips_v4 = [for c in var.ips_liberados : c if !strcontains(c, ":")]
  ips_v6 = [for c in var.ips_liberados : c if strcontains(c, ":")]
}

# 1. Rede própria (VPC). Uma rede nova não aceita nenhuma conexão de fora até
#    que uma regra de firewall libere: por isso a porta do banco (5432) fica fechada.
resource "google_compute_network" "rede" {
  name                    = "${var.prefixo}-rede"
  auto_create_subnetworks = false
}

# 2. Sub-rede: o "pedaço" da rede, na região escolhida, onde a VM se conecta.
#    Dual-stack: além do IPv4, a GCP dá à VM um IPv6 público (quem só sai por IPv6 também acessa).
resource "google_compute_subnetwork" "subrede" {
  name             = "${var.prefixo}-subrede"
  ip_cidr_range    = "10.10.1.0/24"
  region           = var.regiao
  network          = google_compute_network.rede.id
  stack_type       = "IPV4_IPV6"
  ipv6_access_type = "EXTERNAL"
}

# 3. IP público fixo: o endereço que você digita no navegador.
resource "google_compute_address" "ip" {
  name   = "${var.prefixo}-ip"
  region = var.regiao
}

# 4. Firewall: só abre SSH (22), API (8000) e painel (80 e 8501), e só para os IPs liberados.
#    Vale para as VMs com a etiqueta "auditor" (na Azure era a ligação NSG + placa de rede).
#    Uma regra para os IPv4 e outra para os IPv6 (a GCP não mistura os dois na mesma regra).
resource "google_compute_firewall" "entrada" {
  name    = "${var.prefixo}-firewall"
  network = google_compute_network.rede.name

  direction     = "INGRESS"
  source_ranges = local.ips_v4
  target_tags   = [var.prefixo]

  allow {
    protocol = "tcp"
    ports    = ["22", "80", "8000", "8501"]
  }
}

resource "google_compute_firewall" "entrada_ipv6" {
  count   = length(local.ips_v6) > 0 ? 1 : 0
  name    = "${var.prefixo}-firewall-ipv6"
  network = google_compute_network.rede.name

  direction     = "INGRESS"
  source_ranges = local.ips_v6
  target_tags   = [var.prefixo]

  allow {
    protocol = "tcp"
    ports    = ["22", "80", "8000", "8501"]
  }
}

# 4b. Dia da apresentação (painel_publico = true): o painel abre para qualquer endereço, IPv4 e IPv6.
#     Só as portas do painel; SSH (22) e API (8000) seguem nas regras acima. O painel fala com a
#     API por dentro da VM, então a 8000 não precisa ser pública. Não há login no painel.
resource "google_compute_firewall" "painel_publico" {
  count   = var.painel_publico ? 1 : 0
  name    = "${var.prefixo}-painel-publico"
  network = google_compute_network.rede.name

  direction     = "INGRESS"
  source_ranges = ["0.0.0.0/0"]
  target_tags   = [var.prefixo]

  allow {
    protocol = "tcp"
    ports    = ["80", "8501"]
  }
}

resource "google_compute_firewall" "painel_publico_ipv6" {
  count   = var.painel_publico ? 1 : 0
  name    = "${var.prefixo}-painel-publico-ipv6"
  network = google_compute_network.rede.name

  direction     = "INGRESS"
  source_ranges = ["::/0"]
  target_tags   = [var.prefixo]

  allow {
    protocol = "tcp"
    ports    = ["80", "8501"]
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
    stack_type = "IPV4_IPV6"
    access_config {
      nat_ip = google_compute_address.ip.address
    }
    ipv6_access_config {
      network_tier = "PREMIUM" # IPv6 público (a GCP só oferece no nível Premium)
    }
  }

  metadata = {
    # Entrada só por chave SSH (sem senha), para o usuário definido em var.usuario.
    ssh-keys       = "${var.usuario}:${trimspace(file(pathexpand(var.caminho_chave_publica)))}"
    enable-oslogin = "FALSE"

    # Script executado uma única vez, no primeiro boot (o Ubuntu da GCP lê o cloud-init daqui).
    # O replace tira o CRLF que o Git do Windows põe no arquivo (os scripts rodam no bash da VM).
    user-data = replace(templatefile("${path.module}/cloud-init.yaml", {
      usuario        = var.usuario
      repositorio    = var.repositorio_git
      ramo           = var.ramo_git
      google_api_key = var.google_api_key
      cliente_id_sal = var.cliente_id_sal
    }), "\r\n", "\n")
  }
}
