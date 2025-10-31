import logging
import re
import time
from typing import List

from telegram.error import NetworkError
from telegram.ext import CallbackContext

# Variables internas del módulo
ID_LOGS = ""
THREAD_ID = None
PREFIX = ""
MAX_LENGTH = 4095

# Configuración del logger

logger = logging.getLogger("telegram_bot_logger")


def setup_logger(id_logs: str, prefix: str, log_file: str = "my_logs.log", thread_id: int = None):
    """
    Configura el sistema de logging reutilizable. Solo se configura una vez por proceso.
    """
    global ID_LOGS, THREAD_ID, PREFIX, logger, MAX_LENGTH
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
    log_handler = logging.FileHandler(log_file, encoding="utf-8")

    log_handler.setLevel(logging.INFO)

    # Formato común
    formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
    log_handler.setFormatter(formatter)

    # Añadir handlers
    logger.addHandler(log_handler)

    # Silenciar ruido externo
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('apscheduler').setLevel(logging.WARNING)


def get_last_lines(num_lines: int = 1000) -> List[str]:
    buffer_size = 4095  # Puedes ajustar este valor si deseas

    with open('my_logs.log', 'rb') as f:
        f.seek(0, 2)
        pos = f.tell()
        lines = []
        while pos > 0 and len(lines) < num_lines:
            to_read = min(pos, buffer_size)
            pos -= to_read
            f.seek(pos)
            chunk = f.read(to_read)
            lines[:0] = chunk.decode('utf-8', errors='replace').splitlines()
    logs = '\n'.join(lines[-num_lines:])
    result = re.split(r'(?=^\d{4}-\d{2}-\d{2} )', logs, flags=re.MULTILINE)
    result = [element.strip() for element in result if element]
    return result


async def check_logs(context: CallbackContext):
    logs = get_last_lines()

    last_send_log = context.bot_data.get("last_log", None)

    context.bot_data["last_log"] = logs[-1]

    if last_send_log and last_send_log not in logs:
        await context.bot.send_message(ID_LOGS, text=f"{PREFIX}-- Algo ha ido regular, se han perdido logs --}}\n{last_send_log}")
        logger.error(f"Algo ha ido regular, se han perdido logs -> {last_send_log}\n{logs}")
        return

    if not last_send_log:
        diff = [logs[-1]]
    else:
        diff = logs[logs.index(last_send_log) + 1:]
    for text in diff:
        for i in range(0, len(text), MAX_LENGTH):
            fragment = text[i:i + MAX_LENGTH]
            if "INFO" in fragment:
                continue
            try:
                if THREAD_ID:
                    await context.bot.send_message(ID_LOGS, message_thread_id=THREAD_ID, text=f"{fragment}")
                else:
                    await context.bot.send_message(ID_LOGS, text=f"{PREFIX}{fragment}")
            except NetworkError as _:
                pass
            except Exception as e:
                logger.error(e)
