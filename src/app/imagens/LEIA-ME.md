# Imagens do painel

Fotos opcionais. Sem elas, o painel usa a imagem padrão da Home e as iniciais de cada integrante.

| Arquivo | Onde aparece | Tamanho sugerido |
|---|---|---|
| `capa.jpg` | Fundo do topo da Home (fica escurecida para o texto aparecer) | 2000 × 1000 px, paisagem |
| `equipe/yasmin.jpg` | Cartão da Yasmin na página Sobre | 600 × 600 px |
| `equipe/marcos.jpg` | Cartão do Marcos | 600 × 600 px |
| `equipe/samuel.jpg` | Cartão do Samuel | 600 × 600 px |
| `equipe/maria.jpg` | Cartão da M. Vitória | 600 × 600 px |

- Aceita `.jpg`, `.jpeg`, `.png` ou `.webp`, com esses nomes (sem acento e em minúsculas).
- Prefira arquivos com menos de 500 KB: a imagem vai embutida na página.
- Os nomes dos arquivos das fotos estão na lista `TEAM` de `src/app/main.py` (último item de cada linha); a capa, em `render_home()`.
- Depois de colocar ou trocar uma foto: `docker compose up -d --build streamlit` e F5 no navegador.
- Use fotos que cada integrante autorizou: o repositório é público.
