"""
JERCOL TECHNOLOGIES - Flujo modular de Busqueda de Leads

USO:
    python main.py
"""

from core.collector_maps import collector_maps
from core.exporter import exportar_desde_db
from core.normalizer import has_valid_phone, normalize_leads
from core.scorer import score_leads
from core.storage import get_top_leads, init_db, save_leads


# CONFIG - editar antes de correr
TIPO_NEGOCIO = "restaurantes"
CIUDAD = "Monteria Colombia"
MAX_RESULTS = 20
ARCHIVO = "leads_jercol_rest.xlsx"
DB_PATH = "leads.db"
FUENTE = "maps"


def main() -> None:
    print("=" * 60)
    print("  JERCOL TECHNOLOGIES - Pipeline Modular de Leads")
    print("=" * 60)
    print(f"  Tipo negocio: {TIPO_NEGOCIO}")
    print(f"  Ciudad:       {CIUDAD}")
    print(f"  Max results:  {MAX_RESULTS}")
    print(f"  DB:           {DB_PATH}")
    print(f"  Excel:        {ARCHIVO}")
    print("=" * 60)

    print("\n[1/6] Inicializando base de datos...")
    init_db(DB_PATH)

    print("[2/6] Recolectando leads desde Google Maps...")
    leads = collector_maps(tipo_negocio=TIPO_NEGOCIO, ciudad=CIUDAD, max_results=MAX_RESULTS)

    print("[3/6] Normalizando leads...")
    leads_normalizados = normalize_leads(leads, ciudad_default=CIUDAD)

    for lead in leads_normalizados:
        lead["ciudad"] = CIUDAD

    leads_validos = [lead for lead in leads_normalizados if has_valid_phone(lead.get("telefono"))]
    descartados = len(leads_normalizados) - len(leads_validos)
    if descartados:
        print(f"  Leads ignorados por telefono invalido: {descartados}")

    print("[4/6] Calculando score...")
    leads_scored = score_leads(leads_validos)

    print("[5/6] Guardando en SQLite...")
    resultado = save_leads(leads_scored, fuente=FUENTE, db_path=DB_PATH)
    print(f"  Insertados: {resultado['inserted']}")
    print(f"  Ignorados por duplicado: {resultado['ignored']}")

    print("[6/6] Exportando a Excel desde SQLite...")
    exportar_desde_db(
        archivo=ARCHIVO,
        tipo_negocio=TIPO_NEGOCIO,
        ciudad=CIUDAD,
        db_path=DB_PATH,
        fuente=FUENTE,
    )

    top_leads = get_top_leads(limit=20, db_path=DB_PATH)
    print("\nTOP LEADS PARA CONTACTAR:\n")
    if not top_leads:
        print("No hay leads pendientes por contactar.")
    else:
        for index, lead in enumerate(top_leads, start=1):
            nombre = lead.get("nombre", "N/A")
            telefono = lead.get("telefono", "N/A")
            score = lead.get("score", 0)
            print(f"{index}. {nombre} - {telefono} - {score}")

    print("\nProceso completado.")
    print("=" * 60)


if __name__ == "__main__":
    main()
