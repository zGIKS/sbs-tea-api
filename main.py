import argparse
import json
from datetime import datetime, date
from typing import Iterable, List

from sbs_tea.scraper import SbsTeaScraper, ScrapeResult


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
        description="Scraping de TEA bancarias desde la web de la SBS (tip=B)."
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
        help="Formato de salida.",
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
        help="Imprime solo la fecha detectada (ISO) y termina.",
    )

    args = parser.parse_args()
    scraper = SbsTeaScraper()
    result = scraper.fetch_rates(args.date)

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
