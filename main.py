from fastapi import FastAPI, HTTPException
import httpx

app = FastAPI(title="SMART AGRI-MARKET AI Backend")

@app.get('/api/v1/health')
def health():
    return {'status': 'ok'}

@app.get('/api/v1/weather/current')
async def current(latitude: float, longitude: float):
    url = 'https://api.open-meteo.com/v1/forecast'
    params = {'latitude': latitude, 'longitude': longitude, 'current': 'temperature_2m,relative_humidity_2m,wind_speed_10m'}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()['current']
        return {'temperature': data['temperature_2m'], 'humidity': data['relative_humidity_2m'], 'windSpeed': data['wind_speed_10m'], 'description': 'હાલનું હવામાન'}
    except Exception as exc:
        raise HTTPException(status_code=502, detail='Weather provider unavailable') from exc
