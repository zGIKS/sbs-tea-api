## sbs-tea

Scraper en Python para obtener las tasas de interes activas (TEA) que publica la SBS para bancos (`tip=B`). Usa `uv` para manejar el entorno y extrae ambas tablas (MN y USD) en una sola corrida.

### Requisitos

- Python 3.11+
- `uv` instalado

### Ejecucion

Instala las dependencias (opcional con `uv sync`) y ejecuta:

```bash
uv run python main.py
```

Parametros utiles:

- `--date YYYY-MM-DD` o `DD/MM/YYYY` para consultar una fecha especifica. Si se omite, se usa la mas reciente que devuelve la pagina.
- `--currency mn|usd|both` para elegir la tabla.
- `--format json|table` para escoger el formato de salida.
- `--filter "<texto>"` para limitar filas por el tipo de credito.
- `--only-date` para imprimir solo la fecha detectada y terminar.

Ejemplos:

```bash
# Salida JSON con ambas monedas, fecha mas reciente
uv run python main.py --format json

# Tabla solo en soles y filtrada al segmento Corporativos
uv run python main.py --currency mn --format table --filter Corporativos

# Consultar una fecha puntual
uv run python main.py --date 2024-06-30 --format json
```

### Detalles de scraping

La pagina usa un reto de Incapsula; el scraper hace varios GET con la misma sesion hasta obtener el `__VIEWSTATE` y luego postea para cambiar fecha si se indica. Las tablas se leen del HTML renderizado con BeautifulSoup.
