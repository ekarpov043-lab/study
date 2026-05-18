"""
Seed script — populates challenges, achievements, discounts tables.

Run: python seed_db.py
"""

import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(__file__))

from database.connection import execute
from database.models import SCHEMA_SQL


def init_db():
    execute(SCHEMA_SQL)
    logger.info("Tables created.")


# (title, description, challenge_type, required_count, reward_points, related_diseases, is_active, is_general)
CHALLENGES = [
    ("Давление в норме", "Измеряй давление ежедневно 7 дней. Выяви тенденции.", "pressure", 7, 150,
     ["гипертония", "гипертоническая болезнь"], True, False),
    ("Контроль давления — 2 недели", "14 дней измерений. Помогает врачу скорректировать терапию.", "pressure", 14, 300,
     ["гипертония", "ИБС", "сердечная недостаточность"], True, False),
    ("Лёгкий шаг", "Взвешивайся каждое утро 7 дней. Отслеживай динамику.", "weight", 7, 100,
     ["избыточный вес", "ожирение", "сахарный диабет 2 типа"], True, False),
    ("Здоровое питание — 2 недели", "14 дней без фастфуда, с ограничением сладкого.", "weight", 14, 250,
     ["избыточный вес", "ожирение", "преддиабет", "сахарный диабет 2 типа"], True, False),
    ("Активный день", "30+ минут активности ежедневно. 14 дней.", "activity", 14, 200,
     ["ИБС", "избыточный вес", "ожирение", "после инфаркта", "гиподинамия"], True, False),
    ("10 000 шагов", "Не менее 10000 шагов в день. 7 дней.", "steps", 7, 150,
     ["все заболевания", "профилактика"], True, True),
    ("Лекарства без пропусков", "Принимай все препараты ежедневно. 7 дней без пропусков.", "medication", 7, 150,
     ["гипертония", "ИБС", "сахарный диабет 2 типа", "остеопороз", "артрит", "после инфаркта"], True, False),
    ("Инсулинотерапия — месяц", "30 дней строгого режима инсулинотерапии.", "medication", 30, 500,
     ["сахарный диабет 1 типа", "сахарный диабет 2 типа"], True, False),
    ("Контроль сахара", "Измеряй сахар крови ежедневно 7 дней.", "blood_sugar", 7, 150,
     ["сахарный диабет 1 типа", "сахарный диабет 2 типа", "преддиабет"], True, False),
    ("Ежедневная активность", "Отмечай любой тип активности каждый день. 7 дней.", "activity", 7, 100,
     [], True, True),
]

# (title, description, icon, condition_type, condition_value, condition_extra, category)
ACHIEVEMENTS = [
    # Первые шаги
    ("Первый шаг", "Сделать первое измерение любого показателя", "🌱", "logs_total", 1, "", "Первые шаги"),
    ("Знакомство", "Заполнить профиль пациента", "📝", "profile_filled", 1, "", "Первые шаги"),
    ("Охотник за целями", "Взять первый челлендж", "🎯", "challenges_taken", 1, "", "Первые шаги"),

    # Постоянство
    ("3 дня подряд", "Вводить данные 3 дня подряд", "🔥", "streak_days", 3, "", "Постоянство"),
    ("Неделя здоровья", "Вводить данные 7 дней подряд", "💪", "streak_days", 7, "", "Постоянство"),
    ("Марафонец", "Вводить данные 30 дней подряд", "🏃", "streak_days", 30, "", "Постоянство"),
    ("Железная воля", "Вводить данные 100 дней подряд", "⚡", "streak_days", 100, "", "Постоянство"),

    # Челленджи
    ("Первая победа", "Завершить первый челлендж", "🏅", "challenges_completed", 1, "", "Челленджи"),
    ("На разогреве", "Завершить 3 челленджа", "🥈", "challenges_completed", 3, "", "Челленджи"),
    ("Чемпион", "Завершить 10 челленджей", "🥇", "challenges_completed", 10, "", "Челленджи"),

    # Показатели
    ("Сердечник", "Сделать 30 измерений давления", "❤️", "logs_type", 30, "blood_pressure", "Показатели"),
    ("Под контролем", "Сделать 30 измерений веса", "⚖️", "logs_type", 30, "weight", "Показатели"),
    ("Ходок", "Суммарно пройти 500 000 шагов", "🚶", "steps_total", 500000, "", "Показатели"),

    # Социальные
    ("VIP пациент", "Накопить 1000 баллов", "💎", "points_total", 1000, "", "Социальные"),
    ("Легенда клиники", "Накопить 5000 баллов", "👑", "points_total", 5000, "", "Социальные"),
]

DISCOUNTS = [
    ("5% скидка на общий анализ крови", 5, 100, "BLOOD5"),
    ("10% скидка на расширенный анализ крови", 10, 200, "BLOOD10"),
    ("10% скидка на УЗИ одного органа", 10, 300, "UZI10"),
    ("15% скидка на УЗИ всех органов", 15, 500, "UZI15"),
    ("20% скидка на стоматологию", 20, 700, "STOM20"),
    ("Бесплатный анализ крови (100%)", 100, 800, "BLOODFREE"),
    ("Бесплатная консультация терапевта", 100, 1000, "THERAPISTFREE"),
    ("Бесплатный расширенный чекап организма", 100, 2000, "CHECKUPFREE"),
]


def seed_challenges():
    cnt = execute("SELECT COUNT(*) as c FROM challenges", fetchone=True)["c"]
    if cnt > 0:
        print("[SEED] Challenges — already has data. Skip.")
        return
    q = """
        INSERT INTO challenges
            (title, description, challenge_type, required_count,
             reward_points, related_diseases, is_active, is_general)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    for c in CHALLENGES:
        execute(q, c)
    print(f"[SEED] Inserted {len(CHALLENGES)} challenges.")


def seed_achievements():
    cnt = execute("SELECT COUNT(*) as c FROM achievements", fetchone=True)["c"]
    if cnt > 0:
        print("[SEED] Achievements — already has data. Skip.")
        return
    q = """
        INSERT INTO achievements
            (title, description, icon, condition_type, condition_value, condition_extra, category)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    for a in ACHIEVEMENTS:
        execute(q, a)
    print(f"[SEED] Inserted {len(ACHIEVEMENTS)} achievements.")


def seed_discounts():
    cnt = execute("SELECT COUNT(*) as c FROM discounts", fetchone=True)["c"]
    if cnt > 0:
        print("[SEED] Discounts — already has data. Skip.")
        return
    q = """
        INSERT INTO discounts
            (service_description, discount_percent, required_points, base_promo_code)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (base_promo_code) DO NOTHING
    """
    for d in DISCOUNTS:
        execute(q, d)
    print(f"[SEED] Inserted {len(DISCOUNTS)} discounts.")


def list_all():
    for table, label in [
        ("challenges", "Challenges"),
        ("achievements", "Achievements"),
        ("discounts", "Discounts"),
    ]:
        rows = execute(f"SELECT * FROM {table} ORDER BY id", fetchall=True)
        print(f"\n{label}:")
        print("-" * 60)
        for r in rows:
            name = r.get("title") or r.get("service_description") or r.get("base_promo_code", "")
            print(f"  #{r['id']} | {name}")
        print(f"  Total: {len(rows)}")


if __name__ == "__main__":
    init_db()
    seed_challenges()
    seed_achievements()
    seed_discounts()
    list_all()
