import argparse
import json
from datetime import datetime, date
from typing import Iterable, List

from sbs_tea.application import ScrapeService
from sbs_tea.domain import ScrapeResult
from sbs_tea.infrastructure import SbsTeaScraper


def _parse_date_arg(value: str) -> date:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise argparse.ArgumentTypeError("Usa el formato YYYY-MM-DD o DD/MM/YYYY.")


def _filter_rows(rows, credit_filter: str):
    if not credit_filter:
        return rows
    needle = credit_filter.lower()
    return [row for row in rows if needle in row.credit_type.lower()]


def _print_table(result: ScrapeResult, currencies: Iterable[str], credit_filter: str) -> None:
    for code in currencies:
        if code not in result.currencies:
            continue

        currency = result.currencies[code]
        rows = _filter_rows(currency.rows, credit_filter)
        print(f"{code} - fecha de referencia: {result.data_date.isoformat()}")
        if not rows:
            print("  (sin filas que coincidan con el filtro)")
            continue

        for row in rows:
            pieces = []
            for bank in currency.banks:
                value = row.rates.get(bank)
                pieces.append(f"{bank}: {value:.2f}" if isinstance(value, float) else f"{bank}: -")
            joined = "; ".join(pieces)
            print(f"- {row.credit_type}: {joined}")
        print()

    if result.note:
        print(result.note)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Herramienta para obtener TEA bancarias desde la SBS. Modo API inicia servidor FastAPI; modo CLI ejecuta scraping directo."
    )
    parser.add_argument(
        "--mode",
        choices=["api", "cli"],
        default="api",
        help="Modo de ejecución: api (servidor FastAPI) o cli (scraping directo).",
    )
    parser.add_argument(
        "--date",
        type=_parse_date_arg,
        help="Fecha a consultar (YYYY-MM-DD o DD/MM/YYYY). Por defecto usa la ultima disponible.",
    )
    parser.add_argument(
        "--currency",
        choices=["mn", "usd", "both"],
        default="both",
        help="Elige MN, USD o both para obtener ambas tablas.",
    )
    parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="json",
        help="Formato de salida (solo en modo cli).",
    )
    parser.add_argument(
        "--filter",
        dest="credit_filter",
        default="",
        help="Texto para filtrar filas por tipo de credito (opcional).",
    )
    parser.add_argument(
        "--only-date",
        action="store_true",
        help="Imprime solo la fecha detectada (ISO) y termina (solo en modo cli).",
    )

    args = parser.parse_args()

    if args.mode == "api":
        import uvicorn
        print("Iniciando servidor FastAPI...")
        print("Documentación disponible en: http://localhost:8182/docs")
        print("API endpoints: http://localhost:8182/api/v1/rates, http://localhost:8182/api/v1/date")
        uvicorn.run("api:app", host="0.0.0.0", port=8182, reload=True)
    else:
        service = ScrapeService(SbsTeaScraper())
        result = service.fetch_rates(args.date)

        if args.only_date:
            print(result.data_date.isoformat())
            return

        currency_map = {"mn": ["MN"], "usd": ["USD"], "both": ["MN", "USD"]}
        selected_currencies: List[str] = currency_map[args.currency]

        if args.format == "json":
            payload = result.to_dict(
                currency_filter=selected_currencies, credit_filter=args.credit_filter or None
            )
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            _print_table(result, selected_currencies, args.credit_filter)


if __name__ == "__main__":
    main()
