from datetime import date, datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference

from sbs_tea.application import ScrapeService
from sbs_tea.infrastructure import SbsTeaScraper

app = FastAPI(
    title="SBS TEA API",
    description="API para obtener tasas TEA bancarias desde la SBS",
    version="0.1.0",
    docs_url=None,  # Desactiva Swagger UI
    redoc_url=None,
)

# Reemplazar /docs con Scalar para documentación
app.add_route("/docs", get_scalar_api_reference(openapi_url=app.openapi_url), include_in_schema=False)

# Instanciar el servicio
service = ScrapeService(SbsTeaScraper())

# Permitir llamadas desde el front local (Vite y derivados).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def parse_date(date_str: str) -> date:
    if not date_str:
        raise ValueError("Debes indicar una fecha en el query param date.")
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError("Formato de fecha inválido. Usa YYYY-MM-DD o DD/MM/YYYY.")


@app.get("/rates")
def get_rates(
    date_param: str = Query(
        ...,
        alias="date",
        description="Fecha a consultar (YYYY-MM-DD o DD/MM/YYYY). Obligatoria.",
    ),
    currency: str = Query("both", description="Moneda: mn, usd o both."),
    credit_filter: Optional[str] = Query(None, description="Filtro por tipo de crédito."),
):
    try:
        target_date = parse_date(date_param)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    currency_map = {"mn": ["MN"], "usd": ["USD"], "both": ["MN", "USD"]}
    if currency not in currency_map:
        raise HTTPException(status_code=400, detail="Moneda inválida. Usa mn, usd o both.")

    selected_currencies = currency_map[currency]

    result = service.fetch_rates(target_date)

    return result.to_dict(
        currency_filter=selected_currencies,
        credit_filter=credit_filter,
    )


@app.get("/date")
def get_current_date():
    """Obtiene la fecha de referencia actual disponible en la SBS."""
    result = service.fetch_rates()
    return {"date": result.data_date.isoformat()}
