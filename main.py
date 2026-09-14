import httpx
from fastapi import FastAPI, HTTPException


# =========================================================
# APP SETTINGS
# =========================================================

app = FastAPI(
    title="SMART AGRI-MARKET AI Backend"
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
            timeout=httpx.Timeout(
                connect=20,
                read=60,
                write=20,
                pool=20,
            )
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
