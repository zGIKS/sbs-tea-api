from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional


@dataclass
class RateRow:
    credit_type: str
    rates: Dict[str, Optional[float]]


@dataclass
class CurrencyRates:
    currency: str
    banks: List[str]
    rows: List[RateRow]


@dataclass
class ScrapeResult:
    data_date: date
    note: Optional[str]
    currencies: Dict[str, CurrencyRates]

    def to_dict(
        self, currency_filter: Optional[List[str]] = None, credit_filter: Optional[str] = None
    ) -> Dict:
        chosen = currency_filter or list(self.currencies.keys())
        credit_filter_lower = credit_filter.lower() if credit_filter else None

        def should_keep(row: RateRow) -> bool:
            if not credit_filter_lower:
                return True
            return credit_filter_lower in row.credit_type.lower()

        currencies = []
        for code in chosen:
            if code not in self.currencies:
                continue
            currency = self.currencies[code]
            filtered_rows = [row for row in currency.rows if should_keep(row)]
            currencies.append(
                {
                    "code": code,
                    "banks": currency.banks,
                    "rows": [
                        {
                            "credit_type": row.credit_type,
                            "rates": row.rates,
                        }
                        for row in filtered_rows
                    ],
                }
            )

        return {
            "date": self.data_date.isoformat(),
            "note": self.note,
            "currencies": currencies,
        }