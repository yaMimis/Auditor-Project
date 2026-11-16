"""Imagens: capa e fotos da equipe embutidas na página (funcionam sem internet).
"""
from __future__ import annotations

import base64
from pathlib import Path

from src.app.components.base import esc

__all__ = ["IMAGE_TYPES", "image_data_uri", "html_team_avatar"]


IMAGE_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


def image_data_uri(folder: Path, name: str) -> str | None:
    """A imagem <name>.jpg/.jpeg/.png/.webp da pasta, embutida no HTML (data URI), ou None se não existir.

    Embutida porque o st.markdown não serve arquivos locais; assim funciona também sem internet."""
    for suffix, mime in IMAGE_TYPES.items():
        path_ = Path(folder) / f"{name}{suffix}"
        if path_.exists():
            return f"data:{mime};base64,{base64.b64encode(path_.read_bytes()).decode('ascii')}"
    return None


def html_team_avatar(initials: str, photo_uri: str | None) -> str:
    """Foto do integrante, se houver; senão, as iniciais."""
    if photo_uri:
        return f'<div class="team-avatar team-photo" style="background-image:url(\'{photo_uri}\')"></div>'
    return f'<div class="team-avatar">{esc(initials)}</div>'
