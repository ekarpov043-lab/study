"""
Entry point — Long Poll listener + scheduler.
Handles exceptions gracefully, logs everything.
"""

import sys
import os
import logging
import logging.handlers
import threading
import time
from datetime import datetime, date, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from config import LOG_FILE, LOG_LEVEL
from database.models import SCHEMA_SQL
from database.connection import execute
from handlers.base_handler import MessageRouter


def setup_logging():
    os.makedirs("logs", exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8",
    )
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    root.addHandler(handler)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    root.addHandler(console)

    return logging.getLogger(__name__)


logger = setup_logging()


def init_db():
    logger.info("Creating database tables...")
    execute(SCHEMA_SQL)
    logger.info("Database tables ready.")


def send_reminder(vk, vk_id, text):
    try:
        vk.messages.send(
            user_id=vk_id,
            message=text,
            random_id=int(time.time() * 1000),
        )
        logger.info(f"Reminder sent to vk_id={vk_id}")
    except Exception as e:
        logger.error(f"Failed to send reminder to vk_id={vk_id}: {e}")


def scheduler_thread(router):
    """Background: weekly reports + inactivity reminders."""
    vk = router.vk
    last_weekly = None

    while True:
        try:
            now = datetime.now()
            today = date.today()

            if today.weekday() == 6 and now.hour == 10 and 0 <= now.minute < 5:
                key = today.isoformat()
                if last_weekly != key:
                    last_weekly = key
                    logger.info("Sending weekly reports...")
                    _weekly_reports(vk)

            if now.hour in (8, 14, 20) and now.minute == 0:
                logger.debug("Checking inactivity reminders...")
                _inactivity_reminders(vk)
        except Exception as e:
            logger.error(f"Scheduler error: {e}")

        time.sleep(60)


def _weekly_reports(vk):
    from database.queries import (
        get_all_users, get_health_logs_week,
        count_logs_by_type, get_user_challenges,
    )
    users = get_all_users()
    sent = 0
    for u in users:
        try:
            logs = get_health_logs_week(u["vk_id"]) or []
            pc = count_logs_by_type(u["vk_id"], "blood_pressure")
            wc = count_logs_by_type(u["vk_id"], "weight")
            steps_total = 0
            for log in logs:
                if log["measurement_type"] == "steps":
                    steps_total += log["value"].get("steps", 0)
            avg = steps_total // 7 if steps_total else 0
            active_uc = get_user_challenges(u["vk_id"]) or []
            done = u["completed_challenges_count"]
            total = len(active_uc) + done
            pts = len(logs) * 5
            report = (
                "📊 Твой отчёт за неделю:\n\n"
                f"❤️ Измерений давления: {pc}\n"
                f"⚖️ Измерений веса: {wc}\n"
                f"🚶 Средняя активность: {avg} шагов/день\n"
                f"⭐ Заработано баллов: ~{pts}\n"
                f"🎯 Прогресс по челленджам: {done}/{total}\n\n"
                "Новая неделя — новые возможности! 💪"
            )
            send_reminder(vk, u["vk_id"], report)
            sent += 1
        except Exception as e:
            logger.error(f"Weekly report error vk_id={u['vk_id']}: {e}")
    logger.info(f"Weekly reports sent to {sent} users.")


def _inactivity_reminders(vk):
    from database.queries import get_all_users, get_last_active_date
    users = get_all_users()
    reminded = 0
    for u in users:
        try:
            last = get_last_active_date(u["vk_id"])
            if last and last < date.today() - timedelta(days=3):
                name = u["first_name"] or "Друг"
                text = (
                    f"👋 {name}, ты не заходил в бот больше 3 дней!\n"
                    "Твой активный челлендж ждёт. "
                    "Не прерывай серию! 🔥\n"
                    "Запиши показатели в «💊 Здоровье сегодня»."
                )
                send_reminder(vk, u["vk_id"], text)
                reminded += 1
        except Exception as e:
            logger.error(f"Inactivity check error vk_id={u['vk_id']}: {e}")
    if reminded:
        logger.info(f"Inactivity reminders sent to {reminded} users.")


def main():
    logger.info("=" * 50)
    logger.info("Starting medical VK bot...")
    try:
        init_db()
    except Exception as e:
        logger.critical(f"Database init failed: {e}")
        sys.exit(1)

    try:
        router = MessageRouter()
    except Exception as e:
        logger.critical(f"MessageRouter init failed: {e}")
        sys.exit(1)

    scheduler = threading.Thread(
        target=scheduler_thread, args=(router,), daemon=True
    )
    scheduler.start()
    logger.info("Scheduler thread started.")

    logger.info("Bot is running. Listening for messages via Long Poll...")
    try:
        router.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C).")
    except Exception as e:
        logger.critical(f"Fatal error in main loop: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
