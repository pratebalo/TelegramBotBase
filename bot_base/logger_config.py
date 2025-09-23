import logging
import re

from telegram.error import NetworkError
from telegram.ext import ContextTypes

# Variables internas del módulo
ID_LOGS = None
THREAD_ID = None
PREFIX = ""
MAX_LENGTH = 4095


# Configuración del logger

def setup_logger(id_logs: str, prefix: str, info_log_file: str = "info_warning.log", error_log_file: str = "errors.log", thread_id: int = None):
    """
    Configura el sistema de logging reutilizable.
    Debe llamarse al iniciar cada bot.

    Args:
        id_logs (str): ID del chat donde se enviarán los logs por Telegram.
        thread_id (int, optional): ID del hilo para mensajes en grupo. Defaults to None.
        prefix (str): Prefijo para los mensajes enviados por el bot.
        info_log_file (str): Archivo para logs INFO y WARNING.
        error_log_file (str): Archivo para logs ERROR.
    """
    global ID_LOGS, THREAD_ID, PREFIX, logger, MAX_LENGTH
    ID_LOGS = id_logs
    THREAD_ID = thread_id
    PREFIX = f"{prefix} - "
    MAX_LENGTH = 4095 - len(PREFIX)

    # Configura el sistema de registro
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')

    httpx_logger = logging.getLogger('httpx')
    httpx_logger.setLevel(logging.WARNING)
    logging.getLogger('apscheduler').propagate = False

    # Manejadores
    info_warning_handler = logging.FileHandler(info_log_file)
    error_handler = logging.FileHandler(error_log_file)

    # Filtro personalizado para INFO y WARNING
    class InfoWarningFilter(logging.Filter):
        def filter(self, record):
            return record.levelno <= logging.WARNING

    info_warning_handler.addFilter(InfoWarningFilter())
    info_warning_handler.setLevel(logging.INFO)
    error_handler.setLevel(logging.ERROR)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
    info_warning_handler.setFormatter(formatter)
    error_handler.setFormatter(formatter)

    # Logger principal
    logger = logging.getLogger()
    logger.addHandler(info_warning_handler)
    logger.addHandler(error_handler)


def get_last_lines(file: str, num_lines: int = 200) -> str:
    buffer_size = 4095  # Puedes ajustar este valor si deseas

    with open(file, 'rb') as f:
        f.seek(0, 2)
        pos = f.tell()
        lines = []
        while pos > 0 and len(lines) < num_lines:
            to_read = min(pos, buffer_size)
            pos -= to_read
            f.seek(pos)
            chunk = f.read(to_read)
            lines[:0] = chunk.decode('utf-8', errors='replace').splitlines()

        return '\n'.join(lines[-num_lines:])


async def check_log_errors(context: ContextTypes.DEFAULT_TYPE):
    await check_logs(context, "errors.log", "last_error_log")


async def check_last_logs(context: ContextTypes.DEFAULT_TYPE):
    await check_logs(context, "info_warning.log", "last_log")


async def check_logs(context: ContextTypes.DEFAULT_TYPE, file_name: str, context_key: str):
    logs = get_last_lines(file_name)

    regex = r'^\d{4}-\d{2}-\d{2} '
    result = re.split(regex, logs, flags=re.MULTILINE)
    result = [element.strip() for element in result if element]
    if context_key in context.bot_data:
        if context.bot_data[context_key] in result:
            diff = result[result.index(context.bot_data[context_key]) + 1:]
            for text in diff:
                for i in range(0, len(text), MAX_LENGTH):
                    fragment = text[i:i + MAX_LENGTH]
                    try:
                        if "INFO" not in fragment:
                            if THREAD_ID:
                                await context.bot.send_message(ID_LOGS, message_thread_id=THREAD_ID, text=f"{PREFIX}{fragment}")
                            else:
                                await context.bot.send_message(ID_LOGS, text=f"{PREFIX}{fragment}")
                    except NetworkError as _:
                        pass
                    except Exception as e:
                        logger.error(e)

    if result:
        context.bot_data[context_key] = result[-1]


# Exponemos el logger configurado
logger = logging.getLogger()
