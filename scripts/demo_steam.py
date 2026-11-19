#!/usr/bin/env python3
"""Demo: valida que la API publica de Steam (cc=bo) devuelva precios en USD
y que se parezcan a los de SteamDB. No usa claves ni login."""
import json, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone

CC = "bo"
URL = "https://store.steampowered.com/api/appdetails?appids={ids}&cc={cc}&filters=price_overview"

def get(url, intentos=3):
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "KM-GameVault/0.1"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            print(f"HTTP {e.code} (intento {i+1})", file=sys.stderr)
            if e.code == 429:
                time.sleep(30 * (i + 1))
            else:
                time.sleep(5)
        except Exception as e:
            print(f"Error: {e} (intento {i+1})", file=sys.stderr)
            time.sleep(5)
    return None

def main():
    src = json.load(open("data/demo_appids.json", encoding="utf-8"))
    items = src["items"]
    ids = ",".join(str(x["a"]) for x in items)
    data = get(URL.format(ids=ids, cc=CC))
    if data is None:
        print("FALLO: Steam no respondio.")
        sys.exit(1)

    out = {"fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"), "cc": CC, "items": {}}
    print(f"{'Juego':32} {'Esperado':>9} {'Steam':>9} {'Mon':>4} {'Desc':>5}  Estado")
    print("-" * 78)
    ok = 0
    for x in items:
        a = str(x["a"])
        d = (data.get(a) or {})
        po = (d.get("data") or {})
        po = po.get("price_overview") if isinstance(po, dict) else None
        if not po:
            print(f"{x['n'][:32]:32} {x['esperado']:>9.2f} {'--':>9} {'--':>4} {'--':>5}  sin precio")
            continue
        cur = po["final"] / 100
        ini = po["initial"] / 100
        out["items"][a] = {"cur": cur, "ini": ini, "d": po["discount_percent"], "mon": po["currency"]}
        dif = abs(cur - x["esperado"])
        estado = "igual" if dif < 0.01 else f"dif {cur - x['esperado']:+.2f}"
        if po["currency"] == "USD":
            ok += 1
        print(f"{x['n'][:32]:32} {x['esperado']:>9.2f} {cur:>9.2f} {po['currency']:>4} {po['discount_percent']:>4}%  {estado}")
    print("-" * 78)
    print(f"Con precio en USD: {ok}/{len(items)}")
    json.dump(out, open("data/demo_resultado.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)

if __name__ == "__main__":
    main()
