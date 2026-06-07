# Bot BTC/XRP — Guía de configuración

## 1. Crear API Keys en Kraken

1. Ve a [kraken.com](https://www.kraken.com) e inicia sesión
2. Menú superior derecho → **Security** → **API**
3. Clic en **Create API Key**
4. Configura los permisos:
   - ✅ **Query Funds** (ver balance)
   - ✅ **Query Open Orders & Trades**
   - ✅ **Create & Modify Orders** (para ejecutar trades)
   - ❌ Dejar todo lo demás en OFF
5. En **IP Whitelist**, agrega la IP de tu servidor/VPS para mayor seguridad
6. Clic en **Generate Key**
7. Copia el **API Key** y el **Private Key** — solo se muestran una vez

---

## 2. Configurar el bot

```bash
# Clonar / ir al directorio
cd trading_bot

# Crear el archivo de credenciales
copy .env.example .env
```

Edita `.env` y reemplaza los valores:
```
KRAKEN_API_KEY=tu_api_key_aqui
KRAKEN_API_SECRET=tu_api_secret_aqui
```

---

## 3. Probar en modo paper (simulación, SIN dinero real)

En `config.yaml` asegúrate de tener:
```yaml
paper_mode: true
```

Luego ejecuta:
```bash
docker compose up --build
```

El bot mostrará trades simulados en los logs. **Prueba al menos 24 horas** antes de activar modo live.

---

## 4. Activar trading real

Cuando estés listo:
1. En `config.yaml` cambia: `paper_mode: false`
2. Verifica que tienes USD en tu cuenta Kraken
3. Reinicia el bot: `docker compose restart`

---

## 5. Comandos útiles

```bash
# Iniciar bot en background
docker compose up -d --build

# Ver logs en tiempo real
docker compose logs -f

# Detener bot
docker compose down

# Ver últimas 100 líneas del log
docker compose logs --tail=100
```

---

## 6. Parámetros de riesgo (config.yaml)

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `entry_z` | 2.0 | Z-score para abrir posición. Mayor = más conservador |
| `exit_z` | 0.5 | Z-score para cerrar. Más bajo = salida más rápida |
| `max_position_pct` | 20% | % del portfolio por trade (recomendado ≤ 25%) |
| `max_daily_loss_pct` | 5% | Para el bot si pierdes más del 5% en un día |
| `window` | 60 | Minutos de historial para calcular el spread |

---

## 7. Estructura del proyecto

```
trading_bot/
├── src/
│   ├── bot.py           # Loop principal
│   ├── strategy.py      # Lógica de arbitraje de spread
│   ├── risk_manager.py  # Control de riesgo
│   └── kraken_client.py # API de Kraken
├── logs/                # Logs generados automáticamente
├── config.yaml          # Configuración
├── .env                 # Credenciales (NO subir a git)
├── Dockerfile
└── docker-compose.yml
```

---

## ⚠ Advertencias importantes

- **Trading real conlleva riesgo de pérdida total del capital invertido**
- Comienza siempre en `paper_mode: true` y valida el comportamiento
- No inviertas más de lo que puedas permitirte perder
- El bot limita el riesgo pero no lo elimina
- Monitorea los logs regularmente
