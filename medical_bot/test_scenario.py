"""
Integration test — simulates a full user journey through the bot.

Runs against a real PostgreSQL database but mocks VK message sending.
No real VK API calls are made.

Usage:
    python test_scenario.py

Requires:
    - Running PostgreSQL with medical_bot database (or configured DB)
    - Database tables created (python seed_db.py)

Environment variables (from .env) are used for DB connection.
"""

import sys
import os
import json
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(__file__))

# Patch vk_api before importing anything that uses it
import vk_api
original_send = vk_api.VkApi


class MockVkApi:
    """Mock VK API class that captures messages instead of sending."""

    class Messages:
        def __init__(self):
            self.sent = []

        def send(self, user_id, message, random_id=None, keyboard=None):
            self.sent.append({
                "user_id": user_id,
                "message": message,
                "keyboard": keyboard,
            })

    def __init__(self, token=None):
        self.messages = self.Messages()
        self.token = token
        self.longpoll = MockLongPoll()
        self.users = type("Users", (), {"get": lambda *a, **kw: self._fake_user()})()

    def get_api(self):
        return self

    def _fake_user(self):
        return [{"first_name": "Тест", "last_name": "Пользователь"}]


class MockLongPoll:
    """Placeholder — not used in this simulation."""

    def listen(self):
        return []


# Replace real VK API with mock
vk_api.VkApi = MockVkApi
vk_api.utils.get_random_id = lambda: 12345

from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
from database.connection import execute, get_connection
from database.models import SCHEMA_SQL
from handlers.base_handler import MessageRouter
from utils.state_manager import StateManager


TEST_VK_ID = 999999
PASS = 0
FAIL = 0


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} — {detail}")


def cleanup():
    """Remove test user data from DB."""
    for table in [
        "user_achievements", "user_discounts", "user_challenges",
        "health_logs", "advice_log", "user_states",
        "patient_profiles", "users",
    ]:
        execute(f"DELETE FROM {table} WHERE vk_id = %s", (TEST_VK_ID,))


def run_test():
    global PASS, FAIL
    print("=" * 60)
    print("🧪 Медицинский VK Бот — Интеграционный тест")
    print("=" * 60)

    # Setup
    print("\n[1/9] Подготовка тестовой среды...")
    try:
        conn = get_connection()
        test("Подключение к БД", conn is not None)
    except Exception as e:
        test("Подключение к БД", False, str(e))
        return

    execute(SCHEMA_SQL)
    cleanup()
    router = MessageRouter()

    # Helper to simulate a user message
    def msg(text):
        """Simulate a VK message event and return the last sent message."""
        from types import SimpleNamespace
        fake_event = SimpleNamespace(
            user_id=TEST_VK_ID,
            text=text,
            to_me=True,
            type=SimpleNamespace(name="message_new"),
        )

        # Clear sent messages
        router.vk.messages.sent = []
        router._process(fake_event)
        sent = router.vk.messages.sent
        return sent[-1]["message"] if sent else ""

    def last_msg():
        sent = router.vk.messages.sent
        return sent[-1]["message"] if sent else ""

    # ─── Test 1: New user starts ───────────────────────
    print("\n[2/9] Новый пользователь — регистрация...")
    resp = msg("Начать")
    test("Шаг 1: Запрос ID пациента",
         "Введи свой ID пациента" in resp,
         f"Got: {resp[:80]}")

    # ─── Test 2: Enter TEST ────────────────────────────
    print("\n[3/9] Ввод ТЕСТ...")
    resp = msg("ТЕСТ")
    test("Шаг 2: Подтверждение профиля",
         "Подтверди" in resp and "это ты" in resp.lower(),
         f"Got: {resp[:100]}")

    # ─── Test 3: Confirm identity ──────────────────────
    print("\n[4/9] Подтверждение личности + рост...")
    resp = msg("Да, это я")
    test("Шаг 3: Запрос роста",
         "рост" in resp.lower() and "сантиметрах" in resp.lower(),
         f"Got: {resp[:100]}")

    resp = msg("178")
    test("Шаг 4: Приветствие с челленджами",
         "Всё готово" in resp or "челлендж" in resp.lower(),
         f"Got: {resp[:100]}")

    # ─── Test 4: Check main menu ───────────────────────
    print("\n[5/9] Главное меню...")
    resp = msg("📊 Мой прогресс")
    test("Прогресс: карточка пользователя",
         "Профиль" in resp or "Баллы" in resp or "Уровень" in resp,
         f"Got: {resp[:100]}")

    # ─── Test 5: Log health data ───────────────────────
    print("\n[6/9] Запись показателей здоровья + совет + баллы...")

    resp = msg("💊 Здоровье сегодня")
    test("Выбор типа измерения",
         "Выбери тип" in resp,
         f"Got: {resp[:80]}")

    resp = msg("❤️ Давление")
    test("Запрос ввода давления",
         "120/80" in resp,
         f"Got: {resp[:80]}")

    # Valid pressure
    msg("135/88")
    msgs = router.vk.messages.sent
    all_text = " ".join(m["message"] for m in msgs)

    test("Давление сохранено",
         "сохранено" in all_text,
         f"Got: {all_text[:120]}")

    test("+5 баллов начислено",
         "+5" in all_text and "баллов" in all_text,
         f"Got: {all_text[:120]}")

    has_advice = any("Совет" in m["message"] or "Давление" in m["message"]
                     for m in msgs)
    test("Персональный совет получен",
         has_advice,
         f"Got: {[m['message'][:50] for m in msgs]}")

    # ─── Test 6: Invalid input ─────────────────────────
    print("\n[7/9] Обработка некорректного ввода...")
    resp = msg("💊 Здоровье сегодня")
    resp = msg("❤️ Давление")
    resp = msg("abc")
    test("Ошибка при неверном формате",
         "Неверный формат" in resp,
         f"Got: {resp[:80]}")

    # Navigate back to main menu
    msg("🔙 В меню")

    # ─── Test 7: Challenges ────────────────────────────
    print("\n[8/9] Челленджи и скидки...")
    resp = msg("🎯 Мои челленджи")
    test("Список активных челленджей",
         "актив" in resp.lower() or "челлендж" in resp.lower(),
         f"Got: {resp[:100]}")

    resp = msg("🎁 Мои скидки")
    test("Список скидок",
         "скидк" in resp.lower() or "баллов" in resp.lower(),
         f"Got: {resp[:100]}")

    # Navigate back to main menu
    msg("🔙 В меню")

    # ─── Test 8: FSM state is correct ──────────────────
    print("\n[9/9] Проверка FSM...")
    state = StateManager.get_state(TEST_VK_ID)
    test("Состояние = main_menu",
         state == "main_menu",
         f"Got: {state}")

    # ─── Results ───────────────────────────────────────
    print("\n" + "=" * 60)
    total = PASS + FAIL
    print(f"📊 Результаты: {PASS}/{total} тестов пройдено")
    if FAIL == 0:
        print("🎉 Все тесты пройдены!")
    else:
        print(f"❌ {FAIL} тестов не пройдено")
    print("=" * 60)

    # Cleanup
    cleanup()


if __name__ == "__main__":
    run_test()
