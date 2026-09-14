import os
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Query


# =========================================================
# APP SETTINGS
# =========================================================

app = FastAPI(
    title="SMART AGRI-MARKET AI Backend"
)


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
        "status": "ok",
        "service": "SMART AGRI-MARKET AI Backend",
    }


# =========================================================
# CURRENT WEATHER API
# =========================================================

@app.get("/api/v1/weather/current")
async def current_weather(
    latitude: float,
    longitude: float,
):
    weather_url = (
        "https://api.open-meteo.com/v1/forecast"
    )

    weather_params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "wind_speed_10m"
        ),
    }

    try:
        async with httpx.AsyncClient(
            timeout=30
        ) as client:

            response = await client.get(
                weather_url,
                params=weather_params,
            )

            response.raise_for_status()

            weather_payload = response.json()

        current_data = weather_payload.get(
            "current"
        )

        if not current_data:
            raise HTTPException(
                status_code=502,
                detail="Weather current data not found",
            )

        return {
            "temperature": current_data.get(
                "temperature_2m"
            ),
            "humidity": current_data.get(
                "relative_humidity_2m"
            ),
            "windSpeed": current_data.get(
                "wind_speed_10m"
            ),
            "description": "હાલનું હવામાન",
        }

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": (
                    "Weather provider returned an error"
                ),
                "provider_status": (
                    exc.response.status_code
                ),
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
                    "Unable to connect to weather provider"
                ),
                "error_type": type(exc).__name__,
                "error": repr(exc),
            },
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": (
                    "Invalid weather response received"
                ),
                "error": repr(exc),
            },
        ) from exc


# =========================================================
# MANDI PRICE API
# =========================================================

@app.get("/api/v1/market/mandi")
async def mandi_prices(
    state: str = Query(
        default="Gujarat",
        min_length=1,
    ),
    district: Optional[str] = Query(
        default=None,
    ),
    commodity: Optional[str] = Query(
        default=None,
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=100,
    ),
):
    # -----------------------------------------------------
    # CHECK DATA.GOV.IN API KEY
    # -----------------------------------------------------

    if (
        not DATA_GOV_API_KEY
        or DATA_GOV_API_KEY.startswith("અહીં_")
    ):
        raise HTTPException(
            status_code=503,
            detail=(
                "Mandi API key is not configured. "
                "Add DATA_GOV_API_KEY in Render Environment."
            ),
        )

    # -----------------------------------------------------
    # BUILD API PARAMETERS
    # -----------------------------------------------------

    mandi_params = {
        "api-key": DATA_GOV_API_KEY,
        "format": "json",
        "limit": limit,
        "filters[state]": state,
    }

    if district:
        mandi_params[
            "filters[district]"
        ] = district

    if commodity:
        mandi_params[
            "filters[commodity]"
        ] = commodity

    # -----------------------------------------------------
    # CALL DATA.GOV.IN API
    # -----------------------------------------------------

    try:
        async with httpx.AsyncClient(
            timeout=60
        ) as client:

            response = await client.get(
                DATA_GOV_URL,
                params=mandi_params,
            )

            response.raise_for_status()

            mandi_payload = response.json()

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": (
                    "Mandi data provider returned an error"
                ),
                "provider_status": (
                    exc.response.status_code
                ),
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
                "error_type": type(exc).__name__,
                "error": repr(exc),
                "provider_url": DATA_GOV_URL,
            },
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": (
                    "Invalid mandi response received"
                ),
                "error": repr(exc),
            },
        ) from exc

    # -----------------------------------------------------
    # READ RECORDS
    # -----------------------------------------------------

    records = mandi_payload.get(
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
    # FINAL MANDI RESPONSE
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
