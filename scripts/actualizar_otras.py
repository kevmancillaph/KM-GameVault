#!/usr/bin/env python3
"""Precios actuales en otras tiendas (sin Steam) desde la API de IsThereAnyDeal.
- Clave en la variable de entorno ITAD_KEY (Secret del repo). Nunca se escribe en archivos.
- Lee data/base.json (appids). Escribe data/otras.json y data/itad_ids.json (cache appid -> id ITAD).
- Por juego: alt = precio mas bajo en otra tienda (sin Steam ni Nuuvem), as = tienda, nv = Nuuvem.
- Solo USD. Si algo sale raro, aborta sin guardar."""
import json, os, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone

KEY = os.environ.get("ITAD_KEY", "").strip()
BASE = "https://api.isthereanydeal.com"
COUNTRY = "US"
STEAM = 61
LOTE = 50

def llamar(ruta, params, cuerpo=None, intentos=3):
    q = "&".join(f"{k}={v}" for k, v in {**params, "key": KEY}.items())
    url = f"{BASE}{ruta}?{q}"
    data = json.dumps(cuerpo).encode() if cuerpo is not None else None
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, data=data, method="POST" if data else "GET",
                                         headers={"Content-Type": "application/json", "User-Agent": "KM-GameVault/1.0"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            print(f"HTTP {e.code} en {ruta} (intento {i+1})", file=sys.stderr)
            if e.code in (401, 403):
                return None
            time.sleep(10 * (i + 1))
        except Exception as e:
            print(f"Error en {ruta}: {e} (intento {i+1})", file=sys.stderr)
            time.sleep(5)
    return None

def main():
    if not KEY:
        print("Sin ITAD_KEY: se omite el paso de otras tiendas.")
        return
    base = json.load(open("data/base.json", encoding="utf-8"))
    appids = list(base.keys())
    hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    try:
        ids = json.load(open("data/itad_ids.json", encoding="utf-8"))
    except Exception:
        ids = {}
    faltan = [a for a in appids if a not in ids]
    for i in range(0, len(faltan), 100):
        lote = faltan[i:i + 100]
        r = llamar(f"/lookup/id/shop/{STEAM}/v1", {}, [f"app/{a}" for a in lote])
        if r is None:
            print("ABORTO: fallo la busqueda de IDs.")
            sys.exit(1)
        for a in lote:
            ids[a] = r.get(f"app/{a}")
        time.sleep(1)
    json.dump(ids, open("data/itad_ids.json", "w", encoding="utf-8"), separators=(",", ":"))

    inv = {v: k for k, v in ids.items() if v}
    items, fallos, otra_moneda = {}, 0, 0
    monedas = {}
    lista = list(inv.keys())
    for i in range(0, len(lista), LOTE):
        lote = lista[i:i + LOTE]
        r = llamar("/games/prices/v3", {"country": COUNTRY, "deals": "false", "vouchers": "false"}, lote)
        if r is None:
            fallos += len(lote)
            continue
        for g in r:
            a = inv.get(g.get("id"))
            if not a:
                continue
            alt = nv = None
            for d in g.get("deals", []):
                tienda = (d.get("shop") or {}).get("name") or ""
                p = d.get("price") or {}
                monedas[p.get("currency")] = monedas.get(p.get("currency"), 0) + 1
                if p.get("currency") != "USD":
                    otra_moneda += 1
                    continue
                amt = p.get("amount")
                if amt is None or (d.get("shop") or {}).get("id") == STEAM:
                    continue
                if tienda == "Nuuvem":
                    nv = amt if nv is None or amt < nv else nv
                elif alt is None or amt < alt[0]:
                    alt = (amt, tienda)
            it = {}
            if alt: it["alt"], it["as"] = alt
            if nv is not None: it["nv"] = nv
            items[a] = it
        time.sleep(1)

    print("Monedas vistas:", monedas)
    if fallos > len(lista) * 0.3 or otra_moneda > 0 or not items:
        print(f"ABORTO: {fallos} sin respuesta, {otra_moneda} precios en otra moneda, {len(items)} juegos. No se guarda nada.")
        sys.exit(1)
    json.dump({"fecha": hoy, "pais": COUNTRY, "items": items}, open("data/otras.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    sin_id = len([a for a in appids if not ids.get(a)])
    print(f"{hoy}: {len(items)} juegos con datos, {sin_id} sin ID en ITAD, {fallos} sin respuesta")

if __name__ == "__main__":
    main()
