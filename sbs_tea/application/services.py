from datetime import date
from typing import Optional

from ..domain.entities import ScrapeResult
from ..infrastructure.scraper import SbsTeaScraper


class ScrapeService:
    def __init__(self, scraper: SbsTeaScraper):
        self.scraper = scraper

    def fetch_rates(self, target_date: Optional[date] = None) -> ScrapeResult:
        return self.scraper.fetch_rates(target_date)