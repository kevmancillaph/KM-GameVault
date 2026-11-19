#!/usr/bin/env python3
"""Actualiza precios de la lista de deseos desde la API publica de Steam (cc=bo, USD).
- Lee data/base.json: {appid: {low, esp?}}  (low = minimo conocido en USD)
- Escribe data/precios.json y actualiza low en base.json si el precio actual lo baja.
- 'esp' = caso especial (ej. Hitman): se actualiza el precio, nunca el minimo."""
import json, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone

CC = "bo"
LOTE = 25
PAUSA = 3
URL = "https://store.steampowered.com/api/appdetails?appids={ids}&cc={cc}&filters=price_overview"

def get(url, intentos=4):
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "KM-GameVault/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            print(f"HTTP {e.code} (intento {i+1})", file=sys.stderr)
            time.sleep(40 * (i + 1) if e.code == 429 else 5)
        except Exception as e:
            print(f"Error: {e} (intento {i+1})", file=sys.stderr)
            time.sleep(5)
    return None

def main():
    base = json.load(open("data/base.json", encoding="utf-8"))
    ids = list(base.keys())
    hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    items, fallos, nuevos_min, otra_moneda = {}, 0, [], []

    for i in range(0, len(ids), LOTE):
        lote = ids[i:i + LOTE]
        data = get(URL.format(ids=",".join(lote), cc=CC))
        if data is None:
            fallos += len(lote)
            print(f"Lote {i // LOTE + 1}: sin respuesta", file=sys.stderr)
        else:
            for a in lote:
                d = data.get(a) or {}
                inner = d.get("data")
                po = inner.get("price_overview") if isinstance(inner, dict) else None
                if not po:
                    items[a] = {"cur": None}
                    continue
                if po.get("currency") != "USD":
                    otra_moneda.append(a)
                    continue
                cur, ini = po["final"] / 100, po["initial"] / 100
                it = {"cur": cur, "ini": ini, "d": po["discount_percent"]}
                b = base[a]
                if not b.get("esp") and cur > 0 and (b["low"] is None or cur < b["low"]):
                    b["low"] = cur
                    b["lf"] = hoy
                    nuevos_min.append(a)
                items[a] = it
        time.sleep(PAUSA)

    if fallos > len(ids) * 0.3 or otra_moneda:
        print(f"ABORTO: {fallos} sin respuesta, {len(otra_moneda)} en otra moneda. No se guarda nada.")
        sys.exit(1)

    for a, it in items.items():
        if base[a].get("low") is not None:
            it["low"] = base[a]["low"]
        if base[a].get("lf"):
            it["lf"] = base[a]["lf"]
        if base[a].get("esp"):
            it["esp"] = True

    json.dump({"fecha": hoy, "cc": CC, "items": items}, open("data/precios.json", "w", encoding="utf-8"), separators=(",", ":"))
    json.dump(base, open("data/base.json", "w", encoding="utf-8"), indent=0)
    con = sum(1 for v in items.values() if v.get("cur") is not None)
    print(f"{hoy}: {con}/{len(ids)} con precio, {len(nuevos_min)} minimos nuevos, {fallos} sin respuesta")

if __name__ == "__main__":
    main()
