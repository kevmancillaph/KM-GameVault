import os, json, urllib.request
K=os.environ["ITAD_KEY"]
ids=json.load(open("data/itad_ids.json"))
g=ids["1091500"]  # Cyberpunk
g=g if isinstance(g,str) else g.get("id")
for country in ("US","BO"):
    for deals in ("false","true"):
        u=f"https://api.isthereanydeal.com/games/prices/v3?key={K}&country={country}&deals={deals}&vouchers=false"
        rq=urllib.request.Request(u,data=json.dumps([g]).encode(),headers={"Content-Type":"application/json","User-Agent":"KM-GameVault/1.0"})
        r=json.load(urllib.request.urlopen(rq))
        print(country,deals,[(d["shop"]["name"],d["price"]["amount"],d["price"]["currency"],d.get("cut")) for d in r[0]["deals"]])
