"""
Scoring de leads.
"""

import re
from typing import Dict, List, Optional


def parse_rating(rating: Optional[str]) -> Optional[float]:
    """Convierte rating textual a float."""
    if not rating:
        return None
    rating_str = str(rating).strip().replace(",", ".")
    match = re.search(r"\d+(?:\.\d+)?", rating_str)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def score_lead(lead: Dict[str, str]) -> Dict[str, str]:
    """
    Reglas:
    - WhatsApp SI = 3
    - WhatsApp PROBABLE = 2
    - Tiene website = +1
    - Rating >= 4 = +1
    """
    scored = dict(lead)
    score = 0

    whatsapp = str(scored.get("whatsapp") or "").upper()
    if whatsapp == "SI":
        score += 3
    elif whatsapp == "PROBABLE":
        score += 2

    website = scored.get("website")
    if website and str(website).upper() != "N/A":
        score += 1

    rating_num = parse_rating(scored.get("rating"))
    if rating_num is not None and rating_num >= 4.0:
        score += 1

    scored["score"] = score
    return scored


def score_leads(leads: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Aplica score a una lista de leads."""
    return [score_lead(lead) for lead in leads]
