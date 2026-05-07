from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import httpx
import os

app = FastAPI(title="Tankpreis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

TANKERKOENIG_KEY = os.getenv("TK_API_KEY", "00000000-0000-0000-0000-000000000002")
TK_BASE = "https://creativecommons.tankerkoenig.de/json"

CITIES = {
    "hilden": (51.1674, 6.9307),
    "düsseldorf": (51.2217, 6.7762),
    "dusseldorf": (51.2217, 6.7762),
    "köln": (50.9333, 6.9500),
    "koln": (50.9333, 6.9500),
    "berlin": (52.5200, 13.4050),
    "münchen": (48.1351, 11.5820),
    "munchen": (48.1351, 11.5820),
    "hamburg": (53.5753, 10.0153),
    "frankfurt": (50.1109, 8.6821),
    "stuttgart": (48.7758, 9.1829),
    "dortmund": (51.5136, 7.4653),
    "essen": (51.4556, 7.0116),
    "bremen": (53.0793, 8.8017),
    "hannover": (52.3759, 9.7320),
    "nürnberg": (49.4521, 11.0767),
    "nurnberg": (49.4521, 11.0767),
    "leipzig": (51.3397, 12.3731),
    "dresden": (51.0504, 13.7373),
    "bonn": (50.7374, 7.0982),
    "münster": (51.9607, 7.6261),
    "munster": (51.9607, 7.6261),
    "karlsruhe": (49.0069, 8.4037),
    "augsburg": (48.3705, 10.8978),
    "wiesbaden": (50.0782, 8.2398),
    "mönchengladbach": (51.1805, 6.4428),
    "monchengladbach": (51.1805, 6.4428),
    "gelsenkirchen": (51.5177, 7.0857),
    "aachen": (50.7762, 6.0838),
    "kiel": (54.3233, 10.1394),
    "freiburg": (47.9990, 7.8421),
    "rostock": (54.0887, 12.1405),
    "oberhausen": (51.4963, 6.8638),
    "erfurt": (50.9787, 11.0328),
    "mainz": (49.9929, 8.2473),
    "kassel": (51.3127, 9.4797),
    "hagen": (51.3671, 7.4634),
    "saarbrücken": (49.2354, 6.9969),
    "saarbrucken": (49.2354, 6.9969),
    "leverkusen": (51.0459, 6.9897),
    "ratingen": (51.2975, 6.8531),
    "solingen": (51.1656, 7.0836),
    "remscheid": (51.1793, 7.1896),
    "wuppertal": (51.2562, 7.1508),
    "bielefeld": (52.0302, 8.5325),
    "bochum": (51.4819, 7.2162),
    "duisburg": (51.4344, 6.7623),
    "krefeld": (51.3388, 6.5853),
    "herne": (51.5386, 7.2237),
    "recklinghausen": (51.6141, 7.1974),
    "bottrop": (51.5236, 6.9298),
    "mannheim": (49.4875, 8.4660),
    "heidelberg": (49.3988, 8.6724),
    "heilbronn": (49.1427, 9.2109),
    "ulm": (48.3984, 9.9917),
    "ingolstadt": (48.7665, 11.4257),
    "regensburg": (49.0134, 12.1016),
    "würzburg": (49.7913, 9.9534),
    "wurzburg": (49.7913, 9.9534),
    "magdeburg": (52.1205, 11.6276),
    "halle": (51.4825, 11.9675),
    "chemnitz": (50.8333, 12.9167),
    "potsdam": (52.3906, 13.0645),
    "lübeck": (53.8655, 10.6866),
    "lubeck": (53.8655, 10.6866),
    "wolfsburg": (52.4227, 10.7865),
    "göttingen": (51.5413, 9.9158),
    "gottingen": (51.5413, 9.9158),
    "braunschweig": (52.2689, 10.5268),
    "osnabrück": (52.2799, 8.0472),
    "osnabruck": (52.2799, 8.0472),
    "oldenburg": (53.1435, 8.2146),
    "flensburg": (54.7836, 9.4321),
    "paderborn": (51.7189, 8.7575),
    "trier": (49.7596, 6.6441),
    "kaiserslautern": (49.4432, 7.7690),
    "schwerin": (53.6355, 11.4012),
    "hilden": (51.1674, 6.9307),
}


@app.get("/")
async def serve_frontend():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"status": "Tankpreis API läuft"}


@app.get("/geocode")
async def geocode(city: str = Query(...)):
    key = city.strip().lower()
    if key in CITIES:
        lat, lng = CITIES[key]
        return {"name": city.strip().title(), "lat": lat, "lng": lng}
    raise HTTPException(404, f"Stadt '{city}' nicht gefunden.")


@app.get("/stations")
async def get_stations(lat: float, lng: float, rad: float = 10.0):
    url = f"{TK_BASE}/list.php?lat={lat}&lng={lng}&rad={rad}&sort=dist&type=all&apikey={TANKERKOENIG_KEY}"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url)
    if r.status_code != 200:
        raise HTTPException(502, "Tankerkönig nicht erreichbar")
    data = r.json()
    if not data.get("ok"):
        raise HTTPException(502, data.get("message", "Tankerkönig Fehler"))

    stations = []
    for s in data.get("stations", []):
        # Preise bereinigen – nur gültige Preise (>1.00 €) behalten
        e10    = s.get("e10")    if s.get("e10",    0) > 1.0 else None
        e5     = s.get("e5")     if s.get("e5",     0) > 1.0 else None
        diesel = s.get("diesel") if s.get("diesel", 0) > 1.0 else None
        lpg    = s.get("lpg")    if s.get("lpg",    0) > 0.5 else None

        # Station aufnehmen wenn mindestens ein Preis vorhanden
        if any([e10, e5, diesel]):
            s["e10"]    = e10
            s["e5"]     = e5
            s["diesel"] = diesel
            s["lpg"]    = lpg
            stations.append(s)

    return {"stations": stations[:10]}


@app.get("/market")
async def get_market():
    result = {"oil": {"price": 64.2, "change": -1.1}, "fx": {"rate": 1.128, "change": 0.003}}
    async with httpx.AsyncClient(timeout=6) as client:
        try:
            r = await client.get("https://query1.finance.yahoo.com/v8/finance/chart/BZ=F?interval=1d&range=2d")
            d = r.json()
            closes = [c for c in d["chart"]["result"][0]["indicators"]["quote"][0]["close"] if c]
            if len(closes) >= 2:
                result["oil"] = {"price": round(closes[-1], 2), "change": round(closes[-1] - closes[-2], 2)}
        except Exception:
            pass
        try:
            r = await client.get("https://query1.finance.yahoo.com/v8/finance/chart/EURUSD=X?interval=1d&range=2d")
            d = r.json()
            closes = [c for c in d["chart"]["result"][0]["indicators"]["quote"][0]["close"] if c]
            if len(closes) >= 2:
                result["fx"] = {"rate": round(closes[-1], 4), "change": round(closes[-1] - closes[-2], 4)}
        except Exception:
            pass
    return result


@app.get("/health")
async def health():
    return {"status": "ok"}
