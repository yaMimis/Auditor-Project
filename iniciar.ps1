# iniciar.ps1 - sobe o ambiente completo do Auditor de Preco Justo (banco, API e painel).
#
# Uso (PowerShell, na raiz do projeto):
#     .\iniciar.ps1            sobe tudo; constroi a imagem so se ela ainda nao existir
#     .\iniciar.ps1 -Build     reconstroi a imagem antes (mudou codigo ou requirements)
#     .\iniciar.ps1 -Parar     para tudo (os dados do banco continuam no volume)
#     .\iniciar.ps1 -SemNavegador   nao abre o navegador no final
# Se o Windows bloquear o script, rode antes, na mesma janela:
#     Set-ExecutionPolicy Bypass -Scope Process
#
# PARA RODAR A INTERFACE
# cd C:\caminho\do\Auditor-Project
# git pull
# .\iniciar.ps1
# CASO GIT PULL TRAGA ALGUMA ATT, APLICAR:
# .\iniciar.ps1 -Build
# PARA FINALIZAR
# .\iniciar.ps1 -Parar



param(
    [switch]$Build,
    [switch]$Parar,
    [switch]$SemNavegador
)

# "Continue": avisos que o docker escreve no stderr nao derrubam o script;
# cada passo confere o resultado pelo $LASTEXITCODE.
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot
$IMAGEM = "auditor-preco-justo:latest"
$inicio = Get-Date

function Aviso($texto) { Write-Host "[aviso] $texto" -ForegroundColor Yellow }
function Passo($texto) { Write-Host "`n== $texto" -ForegroundColor Cyan }
function Ok($texto)    { Write-Host "[ok] $texto" -ForegroundColor Green }
function Parar($texto) { Write-Host "[erro] $texto" -ForegroundColor Red; exit 1 }

function Saude($container) {
    $s = docker inspect -f "{{.State.Health.Status}}" $container 2>$null
    return "$s".Trim()
}

# 0. Docker instalado e ligado?
docker info *> $null
if ($LASTEXITCODE -ne 0) { Parar "O Docker nao esta rodando. Abra o Docker Desktop e rode o script de novo." }

if ($Parar) {
    docker compose down
    Ok "Ambiente parado. Os dados do banco continuam guardados."
    exit 0
}

# 1. .env (fica fora do Git): cria um modelo se nao existir, sem sobrescrever o seu
Passo "1/6 Conferindo o .env e o modelo"
if (-not (Test-Path ".env")) {
    @"
CLIENTE_ID_SAL=TROQUE_PELA_CHAVE_DO_GRUPO
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/auditor_db
GOOGLE_API_KEY=TROQUE_PELA_CHAVE_DO_GEMINI
"@ | Set-Content -Path ".env" -Encoding ascii
    Aviso "Criei um .env modelo. Preencha CLIENTE_ID_SAL (chave do grupo) e GOOGLE_API_KEY (peca a Maria)."
}
$env_txt = Get-Content ".env" -Raw
if ($env_txt -notmatch "(?m)^GOOGLE_API_KEY=\S+" -or $env_txt -match "TROQUE_PELA_CHAVE_DO_GEMINI") {
    Aviso "GOOGLE_API_KEY nao preenchida: o parecer vai sair pelo template de reserva (sem IA)."
} else { Ok ".env com a chave do Gemini" }

New-Item -ItemType Directory -Force -Path "modelos_salvos" | Out-Null
if (-not (Test-Path "modelos_salvos\pacote_prever_v1.joblib")) {
    Aviso "Falta modelos_salvos\pacote_prever_v1.joblib (peca ao Samuel): o formulario nao calcula; use 'Caso de exemplo'."
} else { Ok "modelo em modelos_salvos\" }

# 2. Banco: sobe e espera o healthcheck do compose
Passo "2/6 Subindo o banco"
docker compose up -d postgres
if ($LASTEXITCODE -ne 0) {
    Parar "O banco nao subiu. Se a porta 5432 estiver ocupada por um PostgreSQL local, pare o servico dele (services.msc) ou use o docker-compose.override.yml com a porta 5433."
}
$pronto = $false
foreach ($i in 1..30) {
    if ((Saude "auditor_postgres") -eq "healthy") { $pronto = $true; break }
    Start-Sleep -Seconds 2
}
if (-not $pronto) { Parar "O banco nao respondeu em 60 s. Veja: docker logs auditor_postgres --tail 30" }
Ok "banco pronto"

# 3. Tabela de decisoes do analista (pode reaplicar sem problema)
Passo "3/6 Aplicando a tabela de decisoes"
docker cp "db\05_decisoes_analista.sql" auditor_postgres:/tmp/05.sql | Out-Null
docker exec auditor_postgres psql -q -U postgres -d auditor_db -v ON_ERROR_STOP=1 -f /tmp/05.sql *> $null
if ($LASTEXITCODE -ne 0) { Parar "Erro ao aplicar db\05_decisoes_analista.sql. Rode o comando a mao para ver a mensagem." }
Ok "tabela decisao_analista"

$contratos = docker exec auditor_postgres psql -tA -U postgres -d auditor_db -c "SELECT count(*) FROM emprestimo" 2>$null
if ("$contratos".Trim() -eq "0") {
    Aviso "O banco esta sem os contratos (cargas do README, passo 5). O painel funciona, mas sem a referencia de mercado do BC."
}

# 4. Imagem: so constroi se nao existir ou se pedirem -Build
Passo "4/6 Imagem da aplicacao"
docker image inspect $IMAGEM *> $null
if ($Build -or $LASTEXITCODE -ne 0) {
    Write-Host "Construindo a imagem (a primeira vez leva alguns minutos: PyTorch e bibliotecas)..."
    docker compose build api
    if ($LASTEXITCODE -ne 0) { Parar "Erro no build da imagem. Role a tela para ver o motivo." }
    Ok "imagem construida"
} else {
    Ok "imagem ja existe (use -Build se mudou codigo ou requirements)"
}

# 5. Normas do parecer no pgvector (dentro do container: nao precisa de Python local)
Passo "5/6 Normas do parecer"
$trechos = docker exec auditor_postgres psql -tA -U postgres -d auditor_db -c "SELECT count(*) FROM trechos_normas" 2>$null
if ("$trechos".Trim() -match "^[1-9]") {
    Ok "normas ja indexadas ($("$trechos".Trim()) trechos)"
} else {
    docker compose run --rm --no-deps api python genai/src/indexar.py
    if ($LASTEXITCODE -ne 0) { Aviso "Nao consegui indexar as normas: o parecer funciona, mas sai sem fontes." }
    else { Ok "normas indexadas" }
}

# 6. API e painel em segundo plano; espera a API ficar saudavel
Passo "6/6 Subindo a API e o painel"
docker compose up -d api streamlit
if ($LASTEXITCODE -ne 0) { Parar "Erro ao subir a API ou o painel. Veja: docker compose logs api --tail 30" }
Write-Host -NoNewline "Aguardando a API (a primeira subida baixa o modelo de busca nas normas)"
$pronto = $false
foreach ($i in 1..48) {
    $s = Saude "auditor_api"
    if ($s -eq "healthy") { $pronto = $true; break }
    if ($s -eq "unhealthy") { break }
    Write-Host -NoNewline "."
    Start-Sleep -Seconds 5
}
Write-Host ""
if (-not $pronto) { Parar "A API nao ficou pronta. Veja: docker logs auditor_api --tail 40" }

$status = (Invoke-WebRequest -UseBasicParsing http://localhost:8000/ -TimeoutSec 10).Content | ConvertFrom-Json
if ($status.modelo_carregavel) { Ok "modelo carregavel" } else { Aviso "modelo nao encontrado em modelos_salvos\" }
if ($status.banco_disponivel)  { Ok "banco disponivel" }  else { Aviso "a API nao ve o banco ou a tabela de decisoes" }

$min = [math]::Round(((Get-Date) - $inicio).TotalMinutes, 1)
Write-Host "`nPronto em $min min." -ForegroundColor Green
Write-Host "  Painel: http://localhost:8501"
Write-Host "  API:    http://localhost:8000/docs"
Write-Host "  Logs:   docker compose logs -f api streamlit"
Write-Host "  Parar:  .\iniciar.ps1 -Parar"
if (-not $SemNavegador) { Start-Process "http://localhost:8501" }
