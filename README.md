# Amazon MX Watcher

Monitor de **stock y precio** para productos de [amazon.com.mx](https://www.amazon.com.mx), pensado para uso
**personal**. Cuando un producto que te interesa vuelve a tener stock, o baja de un precio objetivo, la
aplicación te avisa (Telegram y/o email) con un enlace directo para que **tú** completes la compra con un clic.

## Por qué no hace la compra automáticamente

Las [Condiciones de Uso](https://www.amazon.com.mx/gp/help/customer/display.html) de Amazon prohíben el uso de
bots, scripts u otros medios automatizados para navegar o realizar pedidos en el sitio. Un checkout
automatizado también requeriría eludir sus sistemas anti-bot (CAPTCHA, huellas de navegador, etc.), lo cual va
más allá de lo que esta herramienta hace. Por eso el flujo es **detectar + notificar**, no **comprar**:

- Reduce el riesgo de que tu cuenta sea suspendida.
- No maneja ni almacena datos de pago.
- Sigue siendo útil: tú decides y confirmas cada compra manualmente.

## Cómo funciona

1. Defines una lista de productos (URL de Amazon MX, y opcionalmente un precio objetivo) en `products.yaml`.
2. Un proceso revisa cada producto cada cierto intervalo (por defecto cada 10 minutos, configurable, con un
   mínimo razonable de 2 minutos para no saturar a Amazon).
3. Si el producto pasa de "sin stock" a "en stock", o su precio cae al precio objetivo o por debajo, se envía
   una notificación con el título, precio y enlace del producto.
4. El estado se guarda en una base SQLite local (`data/state.db`) para no reenviar el mismo aviso una y otra vez.

## Instalación

```bash
git clone https://github.com/Eralquine/amazon-mx-watcher
cd amazon-mx-watcher
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env        # configura tus notificadores
cp products.example.yaml products.yaml   # configura tus productos
```

## Configuración

### Productos (`products.yaml`)

```yaml
poll_interval_seconds: 600  # 10 minutos (mínimo permitido: 120)

products:
  - url: "https://www.amazon.com.mx/dp/B0EXAMPLE1"
    nickname: "Consola X"
    target_price: 8999.00     # opcional; si se omite, solo avisa cuando vuelva a haber stock
    notify_on_restock: true

  - url: "https://www.amazon.com.mx/dp/B0EXAMPLE2"
    nickname: "Tarjeta gráfica"
    target_price: null
    notify_on_restock: true
```

### Notificaciones (`.env`)

Copia `.env.example` a `.env` y llena los valores del canal que quieras usar (puedes activar ambos):

```bash
# Telegram: crea un bot con @BotFather y obtén tu chat_id con @userinfobot
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Email vía SMTP
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM=
SMTP_TO=
```

## Uso

```bash
# Validar que products.yaml y .env estén bien configurados, y revisar una sola vez
python -m amazon_mx_watcher run --once

# Dejarlo corriendo en bucle (Ctrl+C para detener)
python -m amazon_mx_watcher run

# Listar productos configurados
python -m amazon_mx_watcher list

# Agregar un producto desde la línea de comandos
python -m amazon_mx_watcher add "https://www.amazon.com.mx/dp/B0EXAMPLE1" --nickname "Consola X" --target-price 8999
```

### Con Docker

```bash
docker compose up -d
```

## Pruebas

```bash
pip install -e ".[dev]"
pytest
```

## Notas y límites

- Esta herramienta solo lee páginas de producto públicas; no inicia sesión en tu cuenta ni maneja pagos.
- Amazon puede bloquear temporalmente o mostrar un CAPTCHA si detecta demasiadas solicitudes automatizadas.
  Si eso ocurre, aumenta `poll_interval_seconds` o detén el monitor por un tiempo.
- Usa esto de forma responsable y bajo tu propio criterio; no está afiliado a Amazon.

## Licencia

MIT — ver [LICENSE](LICENSE).
