"""
JERCOL TECHNOLOGIES - Collector de Google Maps
"""

import random
import re
import time
from typing import Dict, List, Tuple

from bs4 import BeautifulSoup
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


def buscar_whatsapp_en_web(page: Page, url: str, delay_visita_web: Tuple[float, float]) -> str:
    """
    Visita la pagina web del negocio y busca senales de WhatsApp.
    Retorna: 'si', 'probable', 'no', 'sin_web' o 'error'
    """
    if not url or url == "N/A":
        return "sin_web"
    try:
        delay(delay_visita_web)
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        delay((1.0, 2.0))
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        texto = html.lower()

        if "wa.me" in texto or "api.whatsapp.com" in texto:
            return "si"
        if "whatsapp" in texto:
            return "si"
        if "whatsapp" in str(soup.find_all("img")).lower():
            return "si"
        return "no"
    except Exception:
        return "error"


def extraer_detalle_negocio(page: Page) -> Dict[str, str]:
    """
    Extrae los datos del panel lateral de un negocio en Google Maps.
    """
    delay((1.5, 3.0))

    datos = {
        "nombre": "N/A",
        "categoria": "N/A",
        "direccion": "N/A",
        "telefono": "N/A",
        "website": "N/A",
        "rating": "N/A",
        "resenas": "N/A",
        "horario": "N/A",
        "notas": "",
    }

    try:
        html = page.content()

        try:
            nombre = page.locator("h1").first.inner_text(timeout=5000)
            datos["nombre"] = nombre.strip()
        except Exception:
            pass

        try:
            rating_el = page.locator('[aria-label*="estrellas"]').first
            rating_text = rating_el.get_attribute("aria-label", timeout=3000)
            if rating_text:
                match = re.search(r"([\d,.]+)\s+estrellas.*?([\d,.]+)\s+rese", rating_text)
                if match:
                    datos["rating"] = match.group(1)
                    datos["resenas"] = match.group(2)
        except Exception:
            pass

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

        try:
            web_patterns = [
                'a[data-item-id*="authority"]',
                'a[aria-label*="sitio web"]',
                'a[aria-label*="Sitio web"]',
            ]
            for pattern in web_patterns:
                try:
                    el = page.locator(pattern).first
                    href = el.get_attribute("href", timeout=2000)
                    if href and href.startswith("http"):
                        datos["website"] = href
                        break
                except Exception:
                    continue
        except Exception:
            pass

        try:
            cat_el = page.locator('button[jsaction*="category"]').first
            datos["categoria"] = cat_el.inner_text(timeout=3000).strip()
        except Exception:
            pass

    except Exception as error:
        print(f"    Error extrayendo detalle: {error}")

    return datos


def determinar_whatsapp(telefono: str, whatsapp_web: str) -> str:
    """Determina el estado de WhatsApp basado en telefono y busqueda web."""
    if whatsapp_web == "si":
        return "SI"
    if es_celular_colombiano(telefono):
        return "PROBABLE"
    if whatsapp_web == "probable":
        return "PROBABLE"
    return "NO DETECTADO"


def collector_maps(
    tipo_negocio: str,
    ciudad: str,
    max_results: int,
    delay_entre_clicks: Tuple[float, float] = (2.0, 4.0),
    delay_entre_scroll: Tuple[float, float] = (1.5, 3.0),
    delay_visita_web: Tuple[float, float] = (2.0, 4.0),
    headless: bool = False,
) -> List[Dict[str, str]]:
    """Realiza scraping en Google Maps y retorna lista de leads."""
    MAX_RESULTS = max(1, int(max_results))
    max_intentos_sin_nuevos = 3

    query = f"{tipo_negocio} en {ciudad}"
    url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"

    print("=" * 60)
    print("  JERCOL TECHNOLOGIES - Buscador de Leads")
    print("=" * 60)
    print(f"  Buscando: {query}")
    print(f"  Objetivo: {MAX_RESULTS} negocios")
    print("=" * 60)

    leads: List[Dict[str, str]] = []

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
        procesados = set()
        intentos_sin_nuevos = 0

        while len(leads) < MAX_RESULTS:
            try:
                items = page.locator('[role="article"]').all()
            except Exception:
                items = []

            nuevos_en_iteracion = 0

            for item in items:
                if len(leads) >= MAX_RESULTS:
                    break

                try:
                    nombre_preview = item.locator('div[class*="fontHeadlineSmall"]').first.inner_text(timeout=2000).strip()
                    if not nombre_preview or nombre_preview in procesados:
                        continue
                    procesados.add(nombre_preview)
                except Exception:
                    continue

                print(f"  [{len(leads) + 1}/{MAX_RESULTS}] Procesando: {nombre_preview[:45]}...")

                try:
                    item.click(timeout=5000)
                    delay(delay_entre_clicks)

                    datos = extraer_detalle_negocio(page)
                    datos["nombre"] = nombre_preview
                    datos["ciudad"] = ciudad

                    wa_web = "sin_web"
                    if datos["website"] != "N/A":
                        print("         Verificando website...")
                        wa_web = buscar_whatsapp_en_web(page, datos["website"], delay_visita_web)
                        page.go_back(wait_until="domcontentloaded", timeout=15000)
                        delay((2.0, 3.5))
                        item.click(timeout=5000)
                        delay((1.5, 2.5))

                    datos["whatsapp"] = determinar_whatsapp(datos["telefono"], wa_web)
                    datos["notas"] = f"Web: {wa_web}" if wa_web not in ("sin_web", "error") else ""

                    leads.append(datos)
                    nuevos_en_iteracion += 1

                    marca = "OK" if datos["whatsapp"] in ("SI", "PROBABLE") else ".."
                    print(f"         {marca} Tel: {datos['telefono']} | WA: {datos['whatsapp']}")
                    print(f"Leads obtenidos: {len(leads)}/{MAX_RESULTS}")

                    try:
                        page.go_back(wait_until="domcontentloaded", timeout=10000)
                        delay((1.5, 2.5))
                    except Exception:
                        page.goto(url, wait_until="networkidle", timeout=20000)
                        delay((3.0, 4.0))

                except Exception as error:
                    print(f"         Error: {error}")
                    try:
                        page.go_back(wait_until="domcontentloaded", timeout=10000)
                        delay((1.5, 2.5))
                    except Exception:
                        pass
                    continue

            if nuevos_en_iteracion == 0:
                intentos_sin_nuevos += 1
                if intentos_sin_nuevos >= max_intentos_sin_nuevos:
                    print("No se encontraron más resultados disponibles.")
                    break
            else:
                intentos_sin_nuevos = 0

            if len(leads) < MAX_RESULTS:
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

        browser.close()

    print(f"\n  Extraccion completada - {len(leads)} negocios encontrados")
    return leads
