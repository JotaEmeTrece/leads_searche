"""
JERCOL TECHNOLOGIES - Collector de Google Maps
"""

import random
import re
import time
from typing import Dict, List, Optional, Set, Tuple

from playwright.sync_api import Page, sync_playwright


def delay(rango: Tuple[float, float] = (1.0, 2.5)) -> None:
    """Pausa aleatoria para simular comportamiento humano."""
    time.sleep(random.uniform(*rango))


def es_celular_colombiano(telefono: str) -> bool:
    """Detecta si un numero es celular colombiano (empieza con 3)."""
    if not telefono:
        return False
    limpio = re.sub(r"[\s\-\(\)\+]", "", telefono)
    return bool(re.match(r"^(57)?3\d{9}$", limpio))


def extraer_detalle_negocio(page: Page) -> Dict[str, str]:
    """
    Extrae los datos esenciales del panel lateral en Google Maps.
    Enfoque simplificado: nombre, direccion y telefono.
    """
    delay((0.8, 1.8))

    datos = {
        "nombre": "N/A",
        "direccion": "N/A",
        "telefono": "N/A",
        "ciudad": "N/A",
        # Compatibilidad de estructura para pipeline actual.
        "categoria": "N/A",
        "website": "N/A",
        "rating": "N/A",
        "resenas": "N/A",
        "whatsapp": "NO DETECTADO",
        "notas": "",
    }

    try:
        html = page.content()

        # 1) Telefono primero (dato primario de captacion)
        try:
            tel_patterns = [
                'button[data-tooltip*="Copiar numero"]',
                'button[aria-label*="telefono"]',
                'button[aria-label*="Telefono"]',
                '[data-item-id*="phone"]',
            ]
            for pattern in tel_patterns:
                try:
                    el = page.locator(pattern).first
                    label = el.get_attribute("aria-label", timeout=2000)
                    if label:
                        tel = re.search(r"[\+\d][\d\s\-\(\)]{7,}", label)
                        if tel:
                            datos["telefono"] = tel.group().strip()
                            break
                except Exception:
                    continue

            if datos["telefono"] == "N/A":
                tel_match = re.search(r"\+?57[\s\-]?[3][0-9]{9}", html)
                if tel_match:
                    datos["telefono"] = tel_match.group().strip()
                else:
                    tel_match2 = re.search(r"3[0-9]{9}", html)
                    if tel_match2:
                        datos["telefono"] = tel_match2.group().strip()
        except Exception:
            pass

        # 2) Nombre despues de telefono
        try:
            nombre = page.locator("h1").first.inner_text(timeout=5000)
            datos["nombre"] = nombre.strip()
        except Exception:
            pass

        # 3) Direccion como dato secundario
        try:
            dir_patterns = [
                '[data-item-id*="address"]',
                'button[aria-label*="direcci"]',
                '[data-tooltip*="direcci"]',
            ]
            for pattern in dir_patterns:
                try:
                    el = page.locator(pattern).first
                    label = el.get_attribute("aria-label", timeout=2000)
                    if label and len(label) > 5:
                        datos["direccion"] = label.replace("Direccion: ", "").replace("Dirección: ", "").strip()
                        break
                except Exception:
                    continue
        except Exception:
            pass

    except Exception as error:
        print(f"    Error extrayendo detalle: {error}")

    return datos


def normalizar_telefono(valor: str) -> Optional[str]:
    """Normaliza telefono a solo digitos para comparacion y persistencia."""
    if not valor or valor == "N/A":
        return None
    limpio = re.sub(r"\D", "", str(valor))
    return limpio or None


def determinar_whatsapp_por_telefono(telefono: str) -> str:
    """Clasificacion local usando solo el telefono."""
    if es_celular_colombiano(telefono):
        return "PROBABLE"
    return "NO DETECTADO"


def volver_a_listado(page: Page, url_busqueda: str) -> None:
    """Intenta regresar al listado sin bloquear el flujo."""
    try:
        page.go_back(wait_until="domcontentloaded", timeout=6000)
        delay((0.8, 1.8))
        return
    except Exception:
        pass

    try:
        page.goto(url_busqueda, wait_until="domcontentloaded", timeout=15000)
        delay((1.5, 2.5))
    except Exception:
        pass


def abrir_ficha_segura(page: Page, item, url_busqueda: str, timeout_ficha_ms: int = 15000) -> bool:
    """
    Abre ficha de negocio y valida carga de panel.
    Si no carga a tiempo, la omite y retorna False.
    """
    try:
        item.click(timeout=5000)
    except Exception:
        return False

    try:
        page.locator("h1").first.wait_for(state="visible", timeout=timeout_ficha_ms)
        delay((0.8, 1.6))
        return True
    except Exception:
        print("         Ficha no cargo a tiempo. Se omite.")
        volver_a_listado(page, url_busqueda)
        return False


def obtener_id_resultado(item) -> Optional[str]:
    """Obtiene un id de resultado lo mas estable posible para evitar reexploracion."""
    try:
        link = item.locator('a[href*="/maps/place/"]').first
        href = link.get_attribute("href", timeout=1000)
        if href:
            return f"href:{href.split('?')[0]}"
    except Exception:
        pass

    try:
        cid = item.evaluate(
            "el => el.getAttribute('data-cid') || el.getAttribute('data-result-index') || el.getAttribute('id') || ''"
        )
        if cid:
            return f"cid:{str(cid).strip()}"
    except Exception:
        pass

    try:
        texto = item.inner_text(timeout=1000).strip()
        if texto:
            return f"text:{texto.splitlines()[0][:120].lower()}"
    except Exception:
        pass

    return None


def hay_fin_de_lista(page: Page) -> bool:
    """Detecta indicador textual de fin de resultados en Google Maps."""
    try:
        html = page.content().lower()
    except Exception:
        return False

    patrones = [
        "has llegado al final de la lista",
        "has reached the end of the list",
        "you've reached the end of the list",
        "no hay más resultados",
        "no more results",
    ]
    return any(p in html for p in patrones)


def collector_maps(
    tipo_negocio: str,
    ciudad: str,
    max_results: int,
    max_attempts: int = 25,
    delay_entre_clicks: Tuple[float, float] = (2.0, 4.0),
    delay_entre_scroll: Tuple[float, float] = (1.5, 3.0),
    headless: bool = False,
    existing_phones: Optional[Set[str]] = None,
) -> List[Dict[str, str]]:
    """Realiza scraping en Google Maps y retorna lista de leads."""
    MAX_RESULTS = max(1, int(max_results))
    MAX_ATTEMPTS = max(1, int(max_attempts))
    max_intentos_sin_items_nuevos = 3

    query = f"{tipo_negocio} en {ciudad}"
    url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"

    print("=" * 60)
    print("  JERCOL TECHNOLOGIES - Buscador de Leads")
    print("=" * 60)
    print(f"  Buscando: {query}")
    print(f"  Objetivo: {MAX_RESULTS} negocios")
    print(f"  Max intentos de exploracion: {MAX_ATTEMPTS}")
    print("=" * 60)

    leads: List[Dict[str, str]] = []
    telefonos_existentes = set(existing_phones or set())
    resultados_explorados: Set[str] = set()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
            ],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1366, "height": 768},
            locale="es-CO",
            timezone_id="America/Bogota",
        )

        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = context.new_page()

        print("\n  Abriendo Google Maps...")
        delay((2.0, 3.0))
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        delay((3.0, 5.0))

        try:
            page.click('button:has-text("Aceptar todo")', timeout=5000)
            delay((1.0, 2.0))
        except Exception:
            pass
        try:
            page.click('button:has-text("Accept all")', timeout=3000)
            delay((1.0, 2.0))
        except Exception:
            pass

        print("  Cargando resultados...\n")
        intentos_exploracion = 0
        intentos_sin_items_nuevos = 0

        while len(leads) < MAX_RESULTS and intentos_exploracion < MAX_ATTEMPTS:
            intentos_exploracion += 1

            try:
                items = page.locator('[role="article"]').all()
            except Exception:
                items = []

            nuevos_items_en_iteracion = 0
            nuevos_en_iteracion = 0

            for item in items:
                if len(leads) >= MAX_RESULTS:
                    break

                item_id = obtener_id_resultado(item)
                if item_id and item_id in resultados_explorados:
                    continue
                if item_id:
                    resultados_explorados.add(item_id)

                try:
                    nombre_preview = item.locator('div[class*="fontHeadlineSmall"]').first.inner_text(timeout=2000).strip()
                except Exception:
                    nombre_preview = "Sin nombre en listado"

                nuevos_items_en_iteracion += 1

                print(f"  [{len(leads) + 1}/{MAX_RESULTS}] Procesando: {nombre_preview[:45]}...")

                try:
                    if not abrir_ficha_segura(page, item, url, timeout_ficha_ms=15000):
                        continue

                    delay(delay_entre_clicks)

                    datos = extraer_detalle_negocio(page)
                    if datos.get("nombre", "N/A") == "N/A" and nombre_preview != "Sin nombre en listado":
                        datos["nombre"] = nombre_preview
                    datos["ciudad"] = ciudad

                    telefono_normalizado = normalizar_telefono(datos["telefono"])
                    if not telefono_normalizado:
                        print("         Sin telefono valido. Se omite.")
                        volver_a_listado(page, url)
                        continue

                    if not es_celular_colombiano(telefono_normalizado):
                        print("         Telefono sin potencial WhatsApp. Se omite.")
                        volver_a_listado(page, url)
                        continue

                    if telefono_normalizado in telefonos_existentes:
                        print("         Ya existe en BD por telefono. Se omite.")
                        volver_a_listado(page, url)
                        continue

                    datos["telefono"] = telefono_normalizado
                    datos["whatsapp"] = determinar_whatsapp_por_telefono(datos["telefono"])
                    datos["notas"] = ""

                    leads.append(datos)
                    telefonos_existentes.add(telefono_normalizado)
                    nuevos_en_iteracion += 1

                    marca = "OK" if datos["whatsapp"] in ("SI", "PROBABLE") else ".."
                    print(f"         {marca} Tel: {datos['telefono']} | WA: {datos['whatsapp']}")
                    print(f"Leads obtenidos: {len(leads)}/{MAX_RESULTS}")

                    volver_a_listado(page, url)

                except Exception as error:
                    print(f"         Error: {error}")
                    volver_a_listado(page, url)
                    continue

            if nuevos_items_en_iteracion == 0:
                intentos_sin_items_nuevos += 1
            else:
                intentos_sin_items_nuevos = 0

            if len(leads) >= MAX_RESULTS:
                break

            if hay_fin_de_lista(page):
                print("No se encontraron más resultados disponibles.")
                break

            if intentos_sin_items_nuevos >= max_intentos_sin_items_nuevos:
                print("No se encontraron más resultados disponibles.")
                break

            if len(leads) < MAX_RESULTS and intentos_exploracion < MAX_ATTEMPTS:
                print("\n  Cargando mas resultados (scroll)...")
                try:
                    panel = page.locator('[role="feed"]').first
                    panel.evaluate("el => el.scrollBy(0, 800)")
                    delay(delay_entre_scroll)
                except Exception:
                    try:
                        page.keyboard.press("End")
                        delay(delay_entre_scroll)
                    except Exception:
                        pass

        if len(leads) < MAX_RESULTS and intentos_exploracion >= MAX_ATTEMPTS:
            print(f"Se alcanzó MAX_ATTEMPTS ({MAX_ATTEMPTS}) sin completar {MAX_RESULTS} leads guardados.")

        browser.close()

    print(f"\n  Extraccion completada - {len(leads)} negocios encontrados")
    return leads
