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
    # CHECK API KEY
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
    # IMPORTANT:
    # Do not send state/district/commodity filters
    # directly to Data.gov.in at this stage.
    # This avoids timeout caused by unknown field names
    # or heavy filtered requests.
    # -----------------------------------------------------

    mandi_params = {
        "api-key": DATA_GOV_API_KEY,
        "format": "json",
        "limit": limit,
    }

    # -----------------------------------------------------
    # CALL DATA.GOV.IN API
    # -----------------------------------------------------

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=30,
                read=120,
                write=30,
                pool=30,
            )
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

    # -----------------------------------------------------
    # LOCAL FILTERING HELPERS
    # -----------------------------------------------------

    requested_state = (
        state.strip().lower()
        if state
        else ""
    )

    requested_district = (
        district.strip().lower()
        if district
        else ""
    )

    requested_commodity = (
        commodity.strip().lower()
        if commodity
        else ""
    )

    # -----------------------------------------------------
    # CONVERT AND FILTER RECORDS
    # -----------------------------------------------------

    for record in records:
        record_state = str(
            record.get(
                "state",
                "",
            )
        ).strip()

        record_district = str(
            record.get(
                "district",
                "",
            )
        ).strip()

        record_market = str(
            record.get(
                "market",
                record.get(
                    "market_name",
                    "",
                ),
            )
        ).strip()

        record_commodity = str(
            record.get(
                "commodity",
                "",
            )
        ).strip()

        record_variety = str(
            record.get(
                "variety",
                "",
            )
        ).strip()

        record_min_price = record.get(
            "min_price",
            record.get(
                "min",
                "",
            ),
        )

        record_max_price = record.get(
            "max_price",
            record.get(
                "max",
                "",
            ),
        )

        record_modal_price = record.get(
            "modal_price",
            record.get(
                "modal",
                "",
            ),
        )

        record_arrival_date = record.get(
            "arrival_date",
            "",
        )

        # State filter
        if requested_state:
            if record_state.lower() != requested_state:
                continue

        # District filter
        if requested_district:
            if (
                requested_district
                not in record_district.lower()
            ):
                continue

        # Commodity filter
        if requested_commodity:
            if (
                requested_commodity
                not in record_commodity.lower()
            ):
                continue

        results.append(
            {
                "state": record_state,
                "district": record_district,
                "market": record_market,
                "commodity": record_commodity,
                "variety": record_variety,
                "minPrice": record_min_price,
                "maxPrice": record_max_price,
                "modalPrice": record_modal_price,
                "arrivalDate": record_arrival_date,
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
        "source": "data.gov.in",
        "resourceId": DATA_GOV_RESOURCE_ID,
    }
