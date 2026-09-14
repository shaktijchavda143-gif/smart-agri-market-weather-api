import os
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Query


app = FastAPI(title="SMART AGRI-MARKET AI Backend")


# =========================================================
# DATA.GOV.IN SETTINGS
# =========================================================

DATA_GOV_API_KEY = os.getenv(
    "DATA_GOV_API_KEY",
    "",
).strip()

DATA_GOV_RESOURCE_ID = os.getenv(
    "DATA_GOV_RESOURCE_ID",
    "9ef84268-d588-465a-a308-a864a43d0070",
).strip()

DATA_GOV_URL = (
    f"https://api.data.gov.in/resource/{DATA_GOV_RESOURCE_ID}"
)


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/api/v1/health")
def health():
    return {
        "status": "ok"
    }


# =========================================================
# CURRENT WEATHER API
# =========================================================

@app.get("/api/v1/weather/current")
async def current(
    latitude: float,
    longitude: float,
):
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "wind_speed_10m"
        ),
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                url,
                params=params,
            )

            response.raise_for_status()

            weather_json = response.json()
            data = weather_json["current"]

        return {
            "temperature": data["temperature_2m"],
            "humidity": data["relative_humidity_2m"],
            "windSpeed": data["wind_speed_10m"],
            "description": "હાલનું હવામાન",
        }

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Weather data provider returned an error",
                "provider_status": exc.response.status_code,
                "provider_response": exc.response.text[:500],
            },
        ) from exc

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Unable to connect to weather data provider",
                "error": str(exc),
            },
        ) from exc

    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Invalid weather data received",
                "error": str(exc),
            },
        ) from exc


# =========================================================
# MANDI PRICE API
# =========================================================

@app.get("/api/v1/market/mandi")
async def mandi_prices(
    state: str = Query(
        "Gujarat",
        min_length=1,
    ),
    district: Optional[str] = Query(
        None
    ),
    commodity: Optional[str] = Query(
        None
    ),
    limit: int = Query(
        100,
        ge=1,
        le=100,
    ),
):
    # -----------------------------------------------------
    # CHECK API KEY
    # -----------------------------------------------------

    if (
        not DATA_GOV_API_KEY
        or DATA_GOV_API_KEY.startswith("અહીં_")
    ):
        raise HTTPException(
            status_code=503,
            detail="Mandi API key is not configured",
        )

    # -----------------------------------------------------
    # DATA.GOV.IN PARAMETERS
    # -----------------------------------------------------

    params = {
        "api-key": DATA_GOV_API_KEY,
        "format": "json",
        "limit": limit,
        "filters[state]": state,
    }

    if district:
        params["filters[district]"] = district

    if commodity:
        params["filters[commodity]"] = commodity

    # -----------------------------------------------------
    # REQUEST TO DATA.GOV.IN
    # -----------------------------------------------------

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                DATA_GOV_URL,
                params=params,
            )

            response.raise_for_status()

            payload = response.json()

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": (
                    "Mandi data provider returned an error"
                ),
                "provider_status": exc.response.status_code,
                "provider_response": (
                    exc.response.text[:500]
                ),
            },
        ) from exc

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": (
                    "Unable to connect to mandi data provider"
                ),
                "error": str(exc),
            },
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": (
                    "Invalid mandi data received"
                ),
                "error": str(exc),
            },
        ) from exc

    # -----------------------------------------------------
    # CONVERT DATA.GOV.IN RECORDS
    # -----------------------------------------------------

    records = payload.get(
        "records",
        [],
    )

    results = []

    for record in records:
        results.append(
            {
                "state": record.get(
                    "state",
                    state,
                ),
                "district": record.get(
                    "district",
                    district or "",
                ),
                "market": record.get(
                    "market",
                    record.get(
                        "market_name",
                        "",
                    ),
                ),
                "commodity": record.get(
                    "commodity",
                    commodity or "",
                ),
                "variety": record.get(
                    "variety",
                    "",
                ),
                "minPrice": record.get(
                    "min_price",
                    record.get(
                        "min",
                        "",
                    ),
                ),
                "maxPrice": record.get(
                    "max_price",
                    record.get(
                        "max",
                        "",
                    ),
                ),
                "modalPrice": record.get(
                    "modal_price",
                    record.get(
                        "modal",
                        "",
                    ),
                ),
                "arrivalDate": record.get(
                    "arrival_date",
                    "",
                ),
            }
        )

    # -----------------------------------------------------
    # FINAL RESPONSE
    # -----------------------------------------------------

    return {
        "count": len(results),
        "filters": {
            "state": state,
            "district": district,
            "commodity": commodity,
        },
        "records": results,
    }
