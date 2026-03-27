"""
Persistencia SQLite para leads.
"""

import sqlite3
from datetime import datetime
from typing import Dict, List


def _connect(db_path: str = "leads.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = "leads.db") -> None:
    """Crea la base y tabla principal de leads si no existe."""
    with _connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT,
                telefono TEXT UNIQUE,
                ciudad TEXT,
                categoria TEXT,
                direccion TEXT,
                website TEXT,
                rating TEXT,
                resenas TEXT,
                whatsapp TEXT,
                score INTEGER,
                fuente TEXT,
                contacted INTEGER DEFAULT 0,
                fecha_creacion TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_ciudad ON leads(ciudad)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_fuente ON leads(fuente)")
        conn.commit()


def save_leads(leads: List[Dict[str, str]], fuente: str, db_path: str = "leads.db") -> Dict[str, int]:
    """
    Inserta leads en SQLite.
    Ignora duplicados por telefono (UNIQUE + INSERT OR IGNORE).
    """
    inserted = 0
    ignored = 0
    fecha = datetime.now().isoformat(timespec="seconds")

    with _connect(db_path) as conn:
        for lead in leads:
            telefono = lead.get("telefono")
            if telefono in ("", "N/A", None):
                ignored += 1
                continue

            telefono = str(telefono).strip()
            if not telefono.isdigit():
                ignored += 1
                continue

            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO leads (
                    nombre, telefono, ciudad, categoria, direccion, website,
                    rating, resenas, whatsapp, score, fuente, contacted, fecha_creacion
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lead.get("nombre", "N/A"),
                    telefono,
                    lead.get("ciudad", "N/A"),
                    lead.get("categoria", "N/A"),
                    lead.get("direccion", "N/A"),
                    lead.get("website", "N/A"),
                    lead.get("rating", "N/A"),
                    lead.get("resenas", "N/A"),
                    lead.get("whatsapp", "NO DETECTADO"),
                    int(lead.get("score", 0)),
                    fuente,
                    int(lead.get("contacted", 0)),
                    fecha,
                ),
            )

            if cursor.rowcount == 1:
                inserted += 1
            else:
                ignored += 1

        conn.commit()

    return {"inserted": inserted, "ignored": ignored}


def get_all_leads(db_path: str = "leads.db") -> List[Dict[str, str]]:
    """Retorna todos los leads como lista de diccionarios."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                id, nombre, telefono, ciudad, categoria, direccion, website,
                rating, resenas, whatsapp, score, fuente, contacted, fecha_creacion
            FROM leads
            ORDER BY id ASC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def get_top_leads(limit: int = 20, db_path: str = "leads.db") -> List[Dict[str, str]]:
    """
    Retorna leads listos para contacto:
    - contacted = 0
    - ordenados por score DESC
    - limitados por parametro
    """
    safe_limit = max(1, int(limit))
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                id, nombre, telefono, ciudad, categoria, direccion, website,
                rating, resenas, whatsapp, score, fuente, contacted, fecha_creacion
            FROM leads
            WHERE contacted = 0
            ORDER BY score DESC, id ASC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()

    return [dict(row) for row in rows]


def mark_as_contacted(telefono: str, db_path: str = "leads.db") -> bool:
    """Marca un lead como contactado por telefono. Retorna True si actualizo."""
    if not telefono:
        return False
    telefono_limpio = str(telefono).strip()
    if not telefono_limpio:
        return False

    with _connect(db_path) as conn:
        cursor = conn.execute(
            """
            UPDATE leads
            SET contacted = 1
            WHERE telefono = ?
            """,
            (telefono_limpio,),
        )
        conn.commit()
        return cursor.rowcount > 0
