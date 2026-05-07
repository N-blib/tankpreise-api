from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from urllib.parse import quote
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


@app.get("/")
async def serve_frontend():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"status": "Tankpreis API läuft"}


@app.get("/geocode")
async def geocode(city: str = Query(...)):
    headers = {
        "User-Agent": "TankpreisApp/1.0 (kontakt@tankpreis.app)",
        "Accept-Language": "de,en",
    }
    async with httpx.AsyncClient(timeout=10, headers=headers) as client:
        for q in [f"{city}, Deutschland", city, f"{city}, Germany"]:
            encoded = quote(q)
            url = f"https://nominatim.openstreetmap.org/search?q={encoded}&format=json&limit=3&addressdetails=1&countrycodes=de"
            try:
                r = await client.get(url)
                if r.status_code == 200:
                    data = r.json()
                    if data:
                        addr = data[0].get("address", {})
                        name = (addr.get("city") or addr.get("town") or
                                addr.get("village") or addr.get("municipality") or
                                data[0]["display_name"].split(",")[0])
                        return {
                            "name": name,
                            "lat": float(data[0]["lat"]),
                            "lng": float(data[0]["lon"])
                        }
            except Exception:
                continue
    raise HTTPException(404, f"Stadt '{city}' nicht gefunden")


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
    stations = [s for s in data.get("stations", [])
                if s.get("isOpen") and (s.get("e10", 0) > 1 or s.get("diesel", 0) > 1)]
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
