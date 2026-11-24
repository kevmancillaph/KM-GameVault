#!/usr/bin/env python3
"""Pasa las compras de data/compras.json a library.json.
La pagina agrega entradas a compras.json (cola). Aqui se completan con datos de Steam
(desarrollador, distribuidor, Metacritic, resenas, año) y se anaden a library.json.
Las entradas procesadas se quitan de la cola."""
import json, sys, time, urllib.request, urllib.error
from datetime import date

COLA = "data/compras.json"
LIB = "library.json"
APP = "https://store.steampowered.com/api/appdetails?appids={a}&l=english&filters=basic,developers,publishers,metacritic,release_date"
REV = "https://store.steampowered.com/appreviews/{a}?json=1&language=all&purchase_type=all&num_per_page=0"

def get(url):
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "KM-GameVault/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            print(f"HTTP {e.code}", file=sys.stderr); time.sleep(30 if e.code == 429 else 5)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr); time.sleep(5)
    return None

def anio(txt):
    for t in (txt or "").replace(",", " ").split():
        if t.isdigit() and len(t) == 4: return int(t)
    return None

def completar(c):
    a = c["appid"]
    g = {"id": "s%d" % a, "name": c["name"], "appid": a, "plat": c.get("plat") or "steam", "acq": "Comprado",
         "got": (c.get("date") or date.today().isoformat())[:10], "copies": [], "year": c.get("year"),
         "sc": {}, "mins": 0}
    if c.get("score") is not None: g["sc"]["steam"] = c["score"]
    d = get(APP.format(a=a))
    d = (d or {}).get(str(a), {})
    if d.get("success"):
        d = d["data"]
        g["name"] = d.get("name") or g["name"]
        g["year"] = anio((d.get("release_date") or {}).get("date")) or g["year"]
        if d.get("developers"): g["dev"] = ", ".join(d["developers"])
        if d.get("publishers"): g["pub"] = ", ".join(d["publishers"])
        if (d.get("metacritic") or {}).get("score"): g["sc"]["mc"] = round(d["metacritic"]["score"] / 10, 1)
    time.sleep(2)
    r = get(REV.format(a=a))
    q = (r or {}).get("query_summary") or {}
    if q.get("total_reviews"):
        g["rc"] = q["total_reviews"]
        g["sc"]["steam"] = round(q["total_positive"] / q["total_reviews"] * 10, 1)
    if c.get("hours") is not None: g["dur"] = c["hours"]
    if c.get("wsp") is not None: g["wsp"] = c["wsp"]
    return g

def main():
    try: cola = json.load(open(COLA, encoding="utf-8"))
    except FileNotFoundError: cola = []
    if not cola: print("Cola vacia"); return
    lib = json.load(open(LIB, encoding="utf-8"))
    tengo = {g.get("appid") for g in lib["games"]}
    pendientes = []
    for c in cola:
        if not c.get("appid") or c["appid"] in tengo:
            print("Omitido (sin appid o ya esta):", c.get("name")); continue
        try:
            lib["games"].append(completar(c)); tengo.add(c["appid"]); print("Añadido:", c["name"])
        except Exception as e:
            print("Fallo, queda en cola:", c.get("name"), e, file=sys.stderr); pendientes.append(c)
    json.dump(lib, open(LIB, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump(pendientes, open(COLA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main()
