import streamlit as st

# 1. Configuração Inicial da Página (Deve ser a primeira linha)
st.set_page_config(
    page_title="Veritas | Fintech & Legal",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Controlo de Navegação (Filtro de Páginas)
if "pagina_atual" not in st.session_state:
    st.session_state.pagina_atual = "Home"

with st.sidebar:
    st.markdown("<h2 style='font-family: \"Playfair Display\", serif; color: #d4af37;'>VERITAS</h2>", unsafe_allow_html=True)
    st.markdown("Selecione o módulo desejado:")
    
    # Filtro para escolher a página
    pagina_selecionada = st.radio(
        "",
        options=["Home", "Auditoria de Crédito", "Configurações"],
        label_visibility="collapsed"
    )
    st.session_state.pagina_atual = pagina_selecionada

# 3. Injeção de CSS Premium (Estilo Legalor/Fintech)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400&family=DM+Sans:wght@300;400;500;600&display=swap');

    /* Paleta de Cores e Tipografia Base */
    :root {
        --gold: #c89a58;
        --gold-hover: #e4bd7d;
        --dark-bg: #121315;
        --card-bg: #1c1d21;
        --text-light: #f0f2f4;
        --text-muted: #8f9bad;
    }
    
    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }
    
    /* Esconder elementos nativos do Streamlit */
    #MainMenu, header, footer {visibility: hidden;}
    .block-container {padding-top: 0 !important; padding-bottom: 0 !important; max-width: 100% !important;}

    /* --- SESSÃO HERO (TOPO DA PÁGINA) --- */
    .hero-section {
        /* 👇 SUBSTITUA O LINK ABAIXO PELA SUA IMAGEM DE FUNDO (Pode ser link da web ou caminho local base64) 👇 */
        background-image: linear-gradient(to right, rgba(18, 19, 21, 0.95) 20%, rgba(18, 19, 21, 0.6) 100%), 
                          url('https://images.unsplash.com/photo-1589829085413-56de8ae18c73?q=80&w=2000&auto=format&fit=crop');
        background-size: cover;
        background-position: center;
        padding: 8rem 4rem;
        border-bottom: 4px solid var(--gold);
        border-radius: 0 0 24px 24px;
        margin-top: -2rem;
    }
    .hero-title {
        font-family: 'Playfair Display', serif;
        font-size: 4.5rem;
        font-weight: 700;
        color: var(--text-light);
        margin-bottom: 1rem;
        line-height: 1.1;
    }
    .hero-title span {
        color: var(--gold);
        font-style: italic;
    }
    .hero-subtitle {
        font-size: 1.2rem;
        color: var(--text-muted);
        max-width: 600px;
        margin-bottom: 2.5rem;
        line-height: 1.6;
    }

    /* --- BLOCOS DE MÓDULOS --- */
    .modules-section {
        padding: 4rem 2rem;
        text-align: center;
    }
    .section-title {
        font-family: 'Playfair Display', serif;
        font-size: 2.5rem;
        color: var(--text-light);
        margin-bottom: 0.5rem;
    }
    .section-divider {
        width: 60px;
        height: 3px;
        background-color: var(--gold);
        margin: 0 auto 3rem auto;
    }
    
    .module-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 2rem;
        padding: 0 2rem;
    }
    .module-card {
        background-color: var(--card-bg);
        border: 1px solid rgba(200, 154, 88, 0.15);
        border-radius: 16px;
        padding: 2.5rem 2rem;
        text-align: left;
        transition: all 0.3s ease;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    .module-card:hover {
        transform: translateY(-10px);
        border-color: var(--gold);
        box-shadow: 0 15px 40px rgba(200, 154, 88, 0.1);
    }
    .module-icon {
        font-size: 2.5rem;
        color: var(--gold);
        margin-bottom: 1.5rem;
    }
    .module-title {
        font-family: 'Playfair Display', serif;
        font-size: 1.5rem;
        color: var(--text-light);
        margin-bottom: 1rem;
    }

    /* --- SESSÃO EQUIPA (RODAPÉ) --- */
    .team-section {
        background-color: #0b0c0e;
        padding: 5rem 2rem;
        border-radius: 24px 24px 0 0;
        margin-top: 3rem;
        text-align: center;
    }
    .team-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 2rem;
        max-width: 1200px;
        margin: 3rem auto 0 auto;
    }
    .team-member {
        background-color: var(--card-bg);
        border-radius: 16px;
        padding: 2rem 1rem;
        border: 1px solid rgba(255,255,255,0.05);
    }
    .team-photo {
        width: 120px;
        height: 120px;
        border-radius: 50%;
        object-fit: cover;
        border: 3px solid var(--gold);
        margin-bottom: 1rem;
        box-shadow: 0 8px 20px rgba(0,0,0,0.4);
    }
    .team-name {
        font-family: 'Playfair Display', serif;
        font-size: 1.2rem;
        color: var(--text-light);
        margin-bottom: 0.2rem;
    }
    .team-role {
        font-size: 0.85rem;
        color: var(--gold);
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    @media (max-width: 900px) {
        .team-grid { grid-template-columns: repeat(2, 1fr); }
        .hero-title { font-size: 3rem; }
    }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# ROTEADOR DE PÁGINAS
# ==========================================

if st.session_state.pagina_atual == "Home":
    
    # 1. HERO SECTION
    st.markdown("""
        <div class="hero-section">
            <div class="hero-title">Reputação.<br>Respeito. <span>Resultado.</span></div>
            <div class="hero-subtitle">
                Plataforma de inteligência de crédito e conformidade jurídica. Transformamos dados operacionais em evidências claras e acionáveis para decisões precisas.
            </div>
            <!-- Botão ilustrativo no HTML -->
            <div style="display: inline-block; background-color: #c89a58; color: #121315; padding: 12px 32px; border-radius: 8px; font-weight: 600; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Acessar Sistema</div>
        </div>
    """, unsafe_allow_html=True)

    # 2. SEÇÃO DE MÓDULOS
    st.markdown("""
        <div class="modules-section">
            <h2 class="section-title">Áreas de Prática & Módulos</h2>
            <div class="section-divider"></div>
            
            <div class="module-grid">
                <div class="module-card">
                    <div class="module-icon">⚖️</div>
                    <div class="module-title">Risk & Pricing</div>
                    <p style="color: #8f9bad; font-size: 0.95rem; line-height: 1.5;">Auditoria quantitativa de preço justo e avaliação de risco de crédito com modelos explicáveis.</p>
                </div>
                <div class="module-card">
                    <div class="module-icon">📑</div>
                    <div class="module-title">Parecer GenAI</div>
                    <p style="color: #8f9bad; font-size: 0.95rem; line-height: 1.5;">Emissão automatizada de pareceres técnicos baseados no Código de Defesa do Consumidor e LGPD.</p>
                </div>
                <div class="module-card">
                    <div class="module-icon">📊</div>
                    <div class="module-title">Analytics em Lote</div>
                    <p style="color: #8f9bad; font-size: 0.95rem; line-height: 1.5;">Processamento em massa de carteiras de crédito para visão gerencial e identificação de anomalias.</p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 3. SEÇÃO DA EQUIPA (RODAPÉ)
    st.markdown("""
        <div class="team-section">
            <h2 class="section-title">Conheça a Nossa Equipe</h2>
            <div class="section-divider"></div>
            <p style="color: #8f9bad; max-width: 700px; margin: 0 auto; font-size: 1.1rem;">
                Projeto de Fin/Legal Tech desenvolvido para o <b>Bootcamp IA 2026</b>. Unindo engenharia de software, modelagem de dados e inteligência artificial para o setor financeiro.
            </p>
            
            <div class="team-grid">
                <!-- MEMBRO 1 -->
                <div class="team-member">
                    <!-- 👇 SUBSTITUA O LINK ABAIXO PELA FOTO DO INTEGRANTE 1 👇 -->
                    <img src="https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?q=80&w=200&auto=format&fit=crop" alt="Yasmin" class="team-photo">
                    <div class="team-name">Yasmin G.</div>
                    <div class="team-role">Engenharia de Software</div>
                </div>
                
                <!-- MEMBRO 2 -->
                <div class="team-member">
                    <!-- 👇 SUBSTITUA O LINK ABAIXO PELA FOTO DO INTEGRANTE 2 👇 -->
                    <img src="https://images.unsplash.com/photo-1560250097-0b93528c311a?q=80&w=200&auto=format&fit=crop" alt="Marcos" class="team-photo">
                    <div class="team-name">Marcos</div>
                    <div class="team-role">Engenharia de Dados</div>
                </div>
                
                <!-- MEMBRO 3 -->
                <div class="team-member">
                    <!-- 👇 SUBSTITUA O LINK ABAIXO PELA FOTO DO INTEGRANTE 3 👇 -->
                    <img src="https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?q=80&w=200&auto=format&fit=crop" alt="Samuel" class="team-photo">
                    <div class="team-name">Samuel</div>
                    <div class="team-role">Machine Learning</div>
                </div>
                
                <!-- MEMBRO 4 -->
                <div class="team-member">
                    <!-- 👇 SUBSTITUA O LINK ABAIXO PELA FOTO DA INTEGRANTE 4 👇 -->
                    <img src="https://images.unsplash.com/photo-1580489944761-15a19d654956?q=80&w=200&auto=format&fit=crop" alt="M. Vitória" class="team-photo">
                    <div class="team-name">M. Vitória</div>
                    <div class="team-role">GenAI & Banco de Dados</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)


elif st.session_state.pagina_atual == "Auditoria de Crédito":
    # ==========================================
    # AQUI ENTRA O CÓDIGO DA SEMANA PASSADA (O DASHBOARD)
    # ==========================================
    st.markdown("<div style='padding: 2rem;'>", unsafe_allow_html=True)
    st.markdown("<h2 style='font-family: \"Playfair Display\", serif; color: #c89a58;'>Módulo de Auditoria</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #8f9bad;'>Utilize o menu lateral (se aplicável) ou cole aqui a lógica do arquivo main.py antigo (onde tem o botão de Executar auditoria).</p>", unsafe_allow_html=True)
    
    # Exemplo rápido para não deixar vazio:
    st.info("O ambiente de análise corporativa será carregado aqui. Substitua este 'st.info' pelo código do formulário de contrato e dos gráficos ECharts que criámos na semana 1!")
    st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.pagina_atual == "Configurações":
    st.markdown("<div style='padding: 2rem;'><h2 style='font-family: \"Playfair Display\", serif; color: #c89a58;'>Configurações</h2><p>Página em construção.</p></div>", unsafe_allow_html=True)