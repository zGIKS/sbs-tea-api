"""Herramientas para extraer TEA bancarias desde la web de la SBS."""

from .scraper import CurrencyRates, RateRow, SbsTeaScraper, ScrapeResult

__all__ = ["CurrencyRates", "RateRow", "SbsTeaScraper", "ScrapeResult"]
