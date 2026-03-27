"""
Normalizacion de datos de leads.
"""

import re
from typing import Dict, List, Optional
from urllib.parse import urlparse


def normalize_phone(telefono: Optional[str]) -> Optional[str]:
    """Limpia telefono y deja solo digitos."""
    if not telefono:
        return None
    telefono_str = str(telefono).strip()
    if telefono_str.upper() == "N/A":
        return None
    limpio = re.sub(r"\D", "", telefono_str)
    return limpio or None


def has_valid_phone(telefono: Optional[str]) -> bool:
    """Valida que telefono sea solo numeros y no vacio."""
    if not telefono:
        return False
    telefono_str = str(telefono).strip()
    return bool(telefono_str) and telefono_str.isdigit()


def normalize_name(nombre: Optional[str]) -> str:
    """Limpia nombre del negocio."""
    if not nombre:
        return "N/A"
    limpio = str(nombre).strip()
    return limpio or "N/A"


def normalize_website(website: Optional[str]) -> str:
    """Valida website y garantiza formato utilizable o N/A."""
    if not website:
        return "N/A"

    sitio = str(website).strip()
    if not sitio or sitio.upper() == "N/A":
        return "N/A"

    if sitio.startswith(("http://", "https://")):
        parsed = urlparse(sitio)
        if parsed.netloc:
            return sitio
        return "N/A"

    candidato = f"https://{sitio}"
    parsed = urlparse(candidato)
    if parsed.netloc and "." in parsed.netloc:
        return candidato
    return "N/A"


def normalize_lead(lead: Dict[str, str], ciudad_default: Optional[str] = None) -> Dict[str, str]:
    """Normaliza campos clave de un lead y mantiene compatibilidad de estructura."""
    normalized = dict(lead)
    normalized["nombre"] = normalize_name(lead.get("nombre"))
    normalized["telefono"] = normalize_phone(lead.get("telefono"))
    normalized["website"] = normalize_website(lead.get("website"))
    normalized["categoria"] = (lead.get("categoria") or "N/A").strip() if isinstance(lead.get("categoria"), str) else (lead.get("categoria") or "N/A")
    normalized["direccion"] = (lead.get("direccion") or "N/A").strip() if isinstance(lead.get("direccion"), str) else (lead.get("direccion") or "N/A")
    normalized["rating"] = str(lead.get("rating") or "N/A").strip()
    normalized["resenas"] = str(lead.get("resenas") or "N/A").strip()
    normalized["whatsapp"] = str(lead.get("whatsapp") or "NO DETECTADO").strip().upper()
    normalized["ciudad"] = str(lead.get("ciudad") or ciudad_default or "N/A").strip()
    normalized["notas"] = str(lead.get("notas") or "").strip()
    return normalized


def normalize_leads(leads: List[Dict[str, str]], ciudad_default: Optional[str] = None) -> List[Dict[str, str]]:
    """Normaliza una lista de leads."""
    return [normalize_lead(lead, ciudad_default=ciudad_default) for lead in leads]
