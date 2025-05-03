# telegram-bot-base

Este paquete proporciona una estructura común y utilidades compartidas para bots de Telegram, incluyendo:

- Configuración de logging con archivos separados para errores e info/warnings.
- Envío automático de errores recientes a un canal o usuario.
- `main.py` reutilizable para simplificar la estructura de bots.
- Manejador de errores global con `error_callback`.

## Instalación

### Desde ruta local

```bash
pip install -e /ruta/a/telegram_bot_base
