import warnings
from telegram import Update
from telegram.ext import Application
from .logger_config import check_last_logs, check_log_errors
from .error_handler import error_callback

warnings.filterwarnings("ignore")


def run_bot(token, id_logs, add_handlers, add_jobs):
    app = Application.builder().token(token).build()
    job = app.job_queue

    add_handlers(app)
    app.add_error_handler(error_callback)
    add_jobs(job)

    job.run_repeating(check_last_logs, interval=60, first=1)
    job.run_repeating(check_log_errors, interval=60, first=1)

    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as ex:
        app.bot.sendMessage(id_logs, text=str(ex))
