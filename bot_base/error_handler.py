import traceback
from telegram.error import BadRequest, Conflict, NetworkError
from .logger_config import logger

async def error_callback(_, context):
    try:
        raise context.error
    except BadRequest as e:
        logger.warning(f"BadRequest -> {e}")
    except NetworkError as e:
        logger.warning(f"NetworkError -> {e}")
    except Conflict as e:
        logger.error(f"Conflicto -> {e} {traceback.format_exc()}")
    except Exception as e:
        logger.error(f"Otro error -> {e} {traceback.format_exc()}")
