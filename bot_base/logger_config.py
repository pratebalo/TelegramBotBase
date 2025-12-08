import logging
import os
import re
from telegram.ext import CallbackContext

# Variables internas del módulo
ID_LOGS = ""
THREAD_ID = None
PREFIX = ""
MAX_LENGTH = 4000
FILE_LOGS = "my_logs.log"
LAST_LOG = 0
# Configuración del logger

logger = logging.getLogger("telegram_bot_logger")


def setup_logger(id_logs: str, prefix: str, thread_id: int = None):
    """
    Configura el sistema de logging reutilizable. Solo se configura una vez por proceso.
    """
    global ID_LOGS, THREAD_ID, PREFIX, logger, MAX_LENGTH, LAST_LOG
    ID_LOGS = id_logs
    THREAD_ID = thread_id
    PREFIX = f"{prefix} - "
    MAX_LENGTH = 4095 - len(PREFIX)

    # Logger con nombre propio (evita interferir con el root)
    logger = logging.getLogger("telegram_bot_logger")

    # Evita configuración múltiple
    if getattr(logger, "_custom_logger_initialized", False):
        return
    logger._custom_logger_initialized = True

    # Limpia handlers previos si el proceso no se reinició completamente
    if logger.hasHandlers():
        logger.handlers.clear()

    # Configura el sistema de registro
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')

    # Nivel base
    logger.setLevel(logging.INFO)

    # Manejadores de archivo
    log_handler = logging.FileHandler(FILE_LOGS, encoding="utf-8")

    log_handler.setLevel(logging.INFO)

    # Formato común
    formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
    log_handler.setFormatter(formatter)

    # Añadir handlers
    logger.addHandler(log_handler)

    # Silenciar ruido externo
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('apscheduler').setLevel(logging.WARNING)

    with open(FILE_LOGS, 'r', encoding='utf-8') as f:
        f.seek(0, os.SEEK_END)
        LAST_LOG = f.tell()
    return


async def get_unread_lines(last_pos: int) -> tuple[str, int]:
    """Lee nuevas líneas desde `last_pos` en `file_path` y devuelve el contenido y la nueva posición."""
    with open(FILE_LOGS, 'r', encoding='utf-8') as f:
        f.seek(last_pos)
        new_content = f.read()
        new_pos = f.tell()
    return new_content, new_pos


async def check_logs(context: CallbackContext):
    """
    Monitoriza un fichero de log en busca de 'WARN' o 'ERROR' y envía una notificación.
    Diseñado para ser llamado como un job repetitivo de telegram.ext.JobQueue.
    """
    global LAST_LOG
    try:
        new_content, last_pos = await get_unread_lines(LAST_LOG)
        LAST_LOG = last_pos

        if not new_content:
            return

        # Dividir el contenido nuevo en entradas de log individuales
        # El patrón busca una fecha al inicio de una línea para marcar el comienzo de un nuevo log
        log_entries = re.findall(r'^\d{4}-\d{2}-\d{2} .*?(?=^\d{4}-\d{2}-\d{2} |\Z)', new_content, flags=re.MULTILINE | re.DOTALL)

        # Procesa nuevas entradas de log
        for entry in log_entries:
            if not entry or ("WARN" not in entry and "ERROR" not in entry):
                continue

            clean_entry = entry.strip()
            try:
                await _send_long_message(context, clean_entry)
            except Exception as e:
                logging.error(f"No se pudo enviar el mensaje del bot sobre defaulterapp.log: {e}")

    except FileNotFoundError:
        logging.warning("El fichero de log ha desaparecido (probablemente durante la rotación). Reintentando en la próxima ejecución...")
    except Exception as e:
        logging.error(f"Ocurrió un error inesperado en monitorizar_log_defaulter: {e}")


async def _send_long_message(context: CallbackContext, text: str):
    """Envía `text` dividido en varios mensajes si supera el límite de Telegram."""
    if not text:
        return

    # Aseguramos que no haya espacios enormes al principio/fin
    text = text.strip()

    for i in range(0, len(text), MAX_LENGTH):
        chunk = text[i:i + MAX_LENGTH]
        if THREAD_ID:
            await context.bot.send_message(ID_LOGS, message_thread_id=THREAD_ID, text=f"{chunk}")
        else:
            await context.bot.send_message(ID_LOGS, text=f"{PREFIX}{chunk}")
