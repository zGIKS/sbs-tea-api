## sbs-tea

Scraper en Python para obtener las tasas de interes activas (TEA) que publica la SBS para bancos (`tip=B`). Usa `uv` para manejar el entorno y extrae ambas tablas (MN y USD) en una sola corrida.

### Requisitos

- Python 3.11+
- `uv` instalado

### Ejecución

Por defecto, ejecuta la API REST con FastAPI. Usa `--mode cli` para scraping directo.

```bash
# Inicia la API (por defecto)
uv run python main.py

# Scraping directo en CLI
uv run python main.py --mode cli --format json
```

#### Modo API

Inicia servidor FastAPI en `http://localhost:8000`.

- Documentación: `http://localhost:8000/docs`
- Endpoints: `GET /rates`, `GET /date`
- `/rates` exige `date=YYYY-MM-DD` (o `DD/MM/YYYY`) y permite `currency=mn|usd|both` y `credit_filter=<texto>`.

Ejemplos:

```bash
# Obtener tasas en JSON
curl "http://localhost:8000/rates?date=2024-06-30"

# Filtrar por moneda y fecha
curl "http://localhost:8000/rates?currency=mn&date=2024-06-30"
```

#### Modo CLI

Parámetros útiles:

- `--date YYYY-MM-DD` o `DD/MM/YYYY` para consultar una fecha específica. Si se omite, se usa la más reciente.
- `--currency mn|usd|both` para elegir la tabla.
- `--format json|table` para escoger el formato de salida.
- `--filter "<texto>"` para limitar filas por el tipo de crédito.
- `--only-date` para imprimir solo la fecha detectada y terminar.

Ejemplos:

```bash
# Salida JSON con ambas monedas, fecha más reciente
uv run python main.py --mode cli --format json

# Tabla solo en soles y filtrada al segmento Corporativos
uv run python main.py --mode cli --currency mn --format table --filter Corporativos

# Consultar una fecha puntual
uv run python main.py --mode cli --date 2024-06-30 --format json
```

### Detalles de scraping

La página usa un reto de Incapsula; el scraper hace varios GET con la misma sesión hasta obtener el `__VIEWSTATE` y luego postea para cambiar fecha si se indica. Las tablas se leen del HTML renderizado con BeautifulSoup.
