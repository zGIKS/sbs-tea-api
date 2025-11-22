from __future__ import annotations

import json
from datetime import date, datetime
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from ..domain.entities import CurrencyRates, RateRow, ScrapeResult

BASE_URL = "https://www.sbs.gob.pe/app/pp/EstadisticasSAEEPortal/Paginas/TIActivaTipoCreditoEmpresa.aspx"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; sbs-tea-scraper/0.1; +https://github.com)",
    "Accept-Language": "es-PE,es;q=0.9,en;q=0.8",
}
MAX_ATTEMPTS = 5


class SbsTeaScraper:
    def __init__(self, entity: str = "B") -> None:
        self.entity = entity
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def fetch_rates(self, target_date: Optional[date] = None) -> ScrapeResult:
        html = self._load_page()
        current_date = self._extract_date(html)

        if target_date and current_date and target_date != current_date:
            html = self._post_for_date(html, target_date)
            current_date = self._extract_date(html)

        soup = BeautifulSoup(html, "html.parser")
        data_date = current_date or date.today()
        note = self._extract_note(soup)

        currencies = {
            "MN": self._parse_grid(soup, "ctl00_cphContent_rpgActualMn", "MN"),
            "USD": self._parse_grid(soup, "ctl00_cphContent_rpgActualMex", "USD"),
        }

        return ScrapeResult(data_date=data_date, note=note, currencies=currencies)

    def _load_page(self) -> str:
        url = f"{BASE_URL}?tip={self.entity}"
        last_html = ""
        last_status = None

        for _ in range(MAX_ATTEMPTS):
            response = self.session.get(url, timeout=30)
            last_status = response.status_code
            last_html = response.text
            if "__VIEWSTATE" in last_html:
                return last_html

        raise RuntimeError(
            f"No se pudo obtener la pagina completa de la SBS (ultimo estado HTTP {last_status})."
        )

    def _post_for_date(self, html: str, target_date: date) -> str:
        soup = BeautifulSoup(html, "html.parser")
        payload = self._build_payload(soup, target_date, button="btnConsultar")

        response = self.session.post(
            f"{BASE_URL}?tip={self.entity}",
            data=payload,
            timeout=30,
            headers={"Referer": f"{BASE_URL}?tip={self.entity}", **DEFAULT_HEADERS},
        )
        response.raise_for_status()

        if "__VIEWSTATE" not in response.text:
            raise RuntimeError("La solicitud para la fecha indicada no devolvio datos.")

        return response.text

    def _build_payload(
        self,
        soup: BeautifulSoup,
        target_date: Optional[date],
        *,
        button: str,
    ) -> Dict[str, str]:
        payload: Dict[str, str] = {}

        for input_tag in soup.find_all("input"):
            name = input_tag.get("name")
            if not name:
                continue

            input_type = (input_tag.get("type") or "").lower()
            if input_type == "submit":
                continue

            payload[name] = input_tag.get("value", "")

        if target_date:
            display_date = target_date.strftime("%d/%m/%Y")
            iso_date = target_date.strftime("%Y-%m-%d")
            telerik_date = f"{iso_date}-00-00-00"

            payload["ctl00$cphContent$rdpDate"] = iso_date
            payload["ctl00$cphContent$rdpDate$dateInput"] = display_date
            payload["ctl00_cphContent_rdpDate_calendar_AD"] = (
                f"[[1000,1,1],[2099,12,30],[{target_date.year},{target_date.month},{target_date.day}]]"
            )
            # ClientState JSON requerido por Telerik RadDatePicker
            payload["ctl00_cphContent_rdpDate_dateInput_ClientState"] = json.dumps({
                "enabled": True,
                "emptyMessage": "",
                "validationText": telerik_date,
                "valueAsString": telerik_date,
                "minDateStr": "1000-01-01-00-00-00",
                "maxDateStr": "2099-12-30-00-00-00",
                "lastSetTextBoxValue": display_date,
            })

        payload["__EVENTTARGET"] = payload.get("__EVENTTARGET", "")
        payload["__EVENTARGUMENT"] = payload.get("__EVENTARGUMENT", "")
        payload[f"ctl00$cphContent${button}"] = "Exportar" if button == "btnExportar" else "Consultar"

        return payload

    def _extract_date(self, html: str) -> Optional[date]:
        soup = BeautifulSoup(html, "html.parser")
        picker_value = soup.find("input", {"name": "ctl00$cphContent$rdpDate$dateInput"})
        iso_value = soup.find("input", {"name": "ctl00$cphContent$rdpDate"})

        for candidate, pattern in (
            (picker_value, "%d/%m/%Y"),
            (iso_value, "%Y-%m-%d"),
        ):
            if candidate and candidate.get("value"):
                try:
                    return datetime.strptime(candidate["value"], pattern).date()
                except ValueError:
                    continue
        return None

    def _extract_note(self, soup: BeautifulSoup) -> Optional[str]:
        full_text = soup.get_text("\n")
        marker = "Nota:"
        if marker not in full_text:
            return None

        after = full_text.split(marker, 1)[1].strip()
        lines = after.split("\n\n", 1)
        note_body = lines[0].replace("\n", " ").strip()
        if not note_body:
            return None
        return f"{marker} {note_body}"

    def _parse_grid(self, soup: BeautifulSoup, grid_id: str, currency_code: str) -> CurrencyRates:
        grid = soup.find("div", id=grid_id)
        if grid is None:
            raise RuntimeError(f"No se encontro la tabla {grid_id}.")

        data_table = grid.find("table", id=lambda value: value and value.endswith("DataZone_DT"))
        if data_table is None:
            raise RuntimeError(f"No se encontro la seccion de datos para {grid_id}.")

        header_cells = data_table.find("thead").find_all("th")
        banks = [cell.get_text(strip=True) for cell in header_cells]

        # Row headers include group titles in bold and detail rows. We prefix detail rows
        # with the last seen group to avoid ambiguous labels (e.g., multiple "Prestamos a mas de 360 dias").
        row_labels = []
        current_group: Optional[str] = None
        for td in grid.select("td.rpgRowHeaderField"):
            text = td.get_text(strip=True)
            is_group = td.find("b") is not None
            if is_group:
                current_group = text
                row_labels.append(text)
            else:
                label = f"{current_group} - {text}" if current_group else text
                row_labels.append(label)

        body_rows = data_table.find("tbody").find_all("tr")

        if len(row_labels) != len(body_rows):
            raise RuntimeError("No coincide la cantidad de filas de encabezado y datos.")

        parsed_rows: List[RateRow] = []
        for label, row in zip(row_labels, body_rows):
            values = [self._parse_value(td.get_text(strip=True)) for td in row.find_all("td")]
            parsed_rows.append(RateRow(credit_type=label, rates=dict(zip(banks, values))))

        return CurrencyRates(currency=currency_code, banks=banks, rows=parsed_rows)

    @staticmethod
    def _parse_value(text: str) -> Optional[float]:
        normalized = text.strip().lower()
        if not normalized or normalized in {"-", "s.i."}:
            return None

        normalized = normalized.replace(",", ".")
        try:
            return float(normalized)
        except ValueError:
            return None