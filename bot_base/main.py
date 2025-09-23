import warnings
from typing import Optional

from telegram import Update, BotCommand
from telegram.ext import Application
from .logger_config import check_last_logs, check_log_errors, setup_logger
from .error_handler import error_callback

warnings.filterwarnings("ignore")


def make_post_init(commands: Optional[list[tuple[str, str]]] = None):
    async def _post_init(app: Application):
        if commands:
            cmd_objs = [BotCommand(cmd, desc) for cmd, desc in commands]
            await app.bot.set_my_commands(cmd_objs)

    return _post_init


def create_app(token, commands: Optional[list[tuple[str, str]]] = None):
    """
    Crea una instancia de la aplicación de Telegram.

    Args:
        commands (List[str,str], optional): Lista de comandos para el bot. Defaults to None.
        token (str): Token del bot de Telegram.

    Returns:
        Application: Instancia de la aplicación de Telegram.
    """
    return Application.builder().token(token).post_init(make_post_init(commands)).build()


def run_bot(app, id_logs, add_handlers=None, add_jobs=None):
    job = app.job_queue

    if add_handlers:
        add_handlers(app)
    app.add_error_handler(error_callback)

    if add_jobs:
        add_jobs(job)

    job.run_repeating(check_last_logs, interval=60, first=1)
    job.run_repeating(check_log_errors, interval=60, first=1)
    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as ex:
        app.bot.sendMessage(id_logs, text=str(ex))


def main(id_logs: str, thread_id: Optional[int], name: str, token: str, commands: Optional[list[tuple[str, str]]] = None, add_handlers=None, create_jobs=None):
    setup_logger(id_logs=id_logs, thread_id=thread_id, prefix=name)
    my_app = create_app(token, commands=commands)

    create_jobs(my_app.job_queue)
    run_bot(
        app=my_app,
        id_logs=id_logs,
        add_handlers=add_handlers
    )
