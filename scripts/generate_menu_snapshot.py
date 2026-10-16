#!/usr/bin/env python3
"""Refresh the crawlable menu snapshot from the published Google Sheets CSV."""
from __future__ import annotations

import csv
import html
import re
import sys
from collections import OrderedDict
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
START = "<!-- MENU_SNAPSHOT_START -->"
END = "<!-- MENU_SNAPSHOT_END -->"


def fail(message: str) -> None:
    raise SystemExit(message)


def field_index(headers: list[str], *needles: str) -> int:
    for i, header in enumerate(headers):
        if any(needle in header for needle in needles):
            return i
    return -1


def value(row: list[str], index: int) -> str:
    return row[index].strip() if 0 <= index < len(row) else ""


def safe(text: str) -> str:
    return html.escape(text, quote=True)


def price_text(raw: str) -> str:
    cleaned = raw.replace("€", "").replace(" ", "").replace(",", ".")
    try:
        amount = float(cleaned)
        if amount < 0:
            return "Prezzo da verificare"
        return f"€{amount:.2f}".replace(".", ",")
    except ValueError:
        return f"€{raw}" if raw else "Prezzo da verificare"


def main() -> None:
    source = INDEX.read_text(encoding="utf-8")
    match = re.search(r"\bCSV\s*:\s*['\"]([^'\"]+)['\"]", source)
    if not match:
        fail("URL del foglio Google non trovato in CONFIG.CSV")
    url = match.group(1)

    request = Request(url, headers={"User-Agent": "PizzeriaFilipponeMenuSnapshot/1.0"})
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8-sig")
    except Exception as exc:
        fail(f"Impossibile leggere il CSV pubblico del menu: {exc}")

    try:
        rows = list(csv.reader(raw.splitlines()))
    except csv.Error as exc:
        fail(f"CSV del menu non valido: {exc}")
    if len(rows) < 2:
        fail("Il CSV del menu non contiene righe di prodotti")

    headers = [header.strip().lower() for header in rows[0]]
    columns = {
        "name": field_index(headers, "nome"),
        "category": field_index(headers, "categoria"),
        "ingredients": field_index(headers, "ingred"),
        "allergens": field_index(headers, "allerg"),
        "price": field_index(headers, "prezzo", "€"),
    }
    if columns["name"] < 0 or columns["price"] < 0:
        fail("Nel CSV non sono state trovate le colonne Nome e Prezzo")

    groups: OrderedDict[str, list[tuple[str, str, str, str]]] = OrderedDict()
    for row in rows[1:]:
        name = value(row, columns["name"])
        if not name:
            continue
        category = value(row, columns["category"]) or "Altro"
        ingredients = value(row, columns["ingredients"])
        allergens = value(row, columns["allergens"])
        price = price_text(value(row, columns["price"]))
        groups.setdefault(category, []).append((name, ingredients, allergens, price))
    if not groups:
        fail("Nessun prodotto valido trovato nel CSV")

    sections: list[str] = []
    for category, products in groups.items():
        cards: list[str] = []
        for name, ingredients, allergens, price in products:
            details = []
            if ingredients:
                details.append(f'<p class="snapshot-detail">{safe(ingredients)}</p>')
            if allergens:
                details.append(
                    f'<p class="snapshot-detail snapshot-allergens"><strong>Allergeni:</strong> {safe(allergens)}</p>'
                )
            cards.append(
                '<li><article><div class="snapshot-heading">'
                f'<h3>{safe(name)}</h3><span class="snapshot-price">{safe(price)}</span>'
                '</div>' + "".join(details) + '</article></li>'
            )
        sections.append(
            f'<section aria-label="{safe(category)}"><h2>{safe(category)}</h2>'
            '<ul>' + "".join(cards) + '</ul></section>'
        )

    snapshot = (
        '<div data-menu-snapshot class="menu-snapshot" aria-label="Menu della Pizzeria Filippone">'
        + "".join(sections) + '</div>'
    )
    if START not in source or END not in source:
        fail("Segnaposto HTML del menu non trovato")
    before, remainder = source.split(START, 1)
    _, after = remainder.split(END, 1)
    rendered = before + START + "\n    " + snapshot + "\n    " + END + after

    # Remove the development-only Tailwind Play CDN and its inline config.
    rendered, removed = re.subn(
        r'\s*<script src="https://cdn\.tailwindcss\.com"></script>\s*<script>.*?tailwind\.config\s*=\s*\{.*?\n\s*\};\s*</script>',
        "",
        rendered,
        count=1,
        flags=re.DOTALL,
    )
    if not removed:
        # Already compiled HTML is valid on subsequent scheduled refreshes.
        if "cdn.tailwindcss.com" in rendered:
            fail("Non è stato possibile rimuovere la configurazione Tailwind CDN")

    INDEX.write_text(rendered, encoding="utf-8")
    print(f"Menu statico aggiornato: {sum(map(len, groups.values()))} prodotti in {len(groups)} categorie.")


if __name__ == "__main__":
    main()
