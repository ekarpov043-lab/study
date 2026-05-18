"""Main message router — Long Poll listener, FSM dispatcher."""

import logging
import re
import vk_api
from vk_api.longpoll import VkEventType, VkLongPoll

from config import VK_GROUP_TOKEN
from utils.state_manager import StateManager
from utils.keyboards import main_menu
from utils.constants import STATES

from database.queries import (
    get_or_create_user, get_patient_profile,
)
from api_stub.clinic_api import ClinicAPI

from handlers.registration import (
    handle_onboarding_step1, handle_onboarding_input,
    handle_onboarding_confirm, handle_onboarding_height,
)
from handlers.challenges import handle_challenges, handle_challenge_action, handle_mark_done, handle_take
from handlers.health_log import (
    handle_health_today, handle_select_type,
    handle_input_pressure, handle_input_weight, handle_input_sugar,
    handle_input_activity, handle_input_medication,
)
from handlers.profile import handle_profile
from handlers.achievements import handle_achievements
from handlers.discounts import handle_discounts, handle_buy_discount

logger = logging.getLogger(__name__)
clinic_api = ClinicAPI()


class MessageRouter:
    def __init__(self):
        self.vk_session = vk_api.VkApi(token=VK_GROUP_TOKEN)
        self.vk = self.vk_session.get_api()
        self._longpoll = None

    @property
    def longpoll(self):
        if self._longpoll is None:
            self._longpoll = VkLongPoll(self.vk_session)
        return self._longpoll

    def send(self, user_id, message, keyboard=None):
        try:
            self.vk.messages.send(
                user_id=user_id,
                message=message,
                random_id=vk_api.utils.get_random_id(),
                keyboard=keyboard,
            )
        except vk_api.ApiError as e:
            logger.error(f"VK API error sending to {user_id}: {e}")

    def run(self):
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                try:
                    self._process(event)
                except Exception as e:
                    logger.error(
                        f"Unhandled error processing event: {e}", exc_info=True
                    )
                    try:
                        self.send(
                            event.user_id,
                            "Произошла ошибка, попробуй ещё раз.",
                            keyboard=main_menu(),
                        )
                    except Exception:
                        pass

    def _get_user_info(self, vk_id):
        try:
            info = self.vk.users.get(user_ids=vk_id)[0]
            return (
                info.get("first_name", ""),
                info.get("last_name", ""),
            )
        except Exception as e:
            logger.warning(f"Failed to get user info for {vk_id}: {e}")
            return "", ""

    def _process(self, event):
        vk_id = event.user_id
        text = event.text.strip()
        first_name, last_name = self._get_user_info(vk_id)
        get_or_create_user(vk_id, first_name, last_name)

        state = StateManager.get_state(vk_id)
        profile = get_patient_profile(vk_id)

        logger.info(f"MSG from vk_id={vk_id} state={state} text={text[:50]}")

        # New user → onboarding
        if state == STATES["START"] and not profile:
            handle_onboarding_step1(vk_id, text, self.send)
            return

        # Back to menu
        if text in ("/start", "🔙 В меню", "Назад", "В меню", "Главное меню"):
            StateManager.set_state(vk_id, STATES["MAIN_MENU"])
            self.send(
                vk_id,
                f"Привет, я медицинский бот!\n\n"
                f"👋 {first_name}, главное меню. Выбери раздел:",
                keyboard=main_menu(registered=bool(profile)),
            )
            return

        # FSM dispatcher
        handlers = {
            STATES["ONBOARDING_ID"]: lambda: handle_onboarding_input(vk_id, text, self.send),
            STATES["ONBOARDING_CONFIRM"]: lambda: handle_onboarding_confirm(vk_id, text, self.send, first_name, last_name),
            STATES["ONBOARDING_HEIGHT"]: lambda: handle_onboarding_height(vk_id, text, self.send),
            STATES["MAIN_MENU"]: lambda: self._main_menu(vk_id, text),
            STATES["CHALLENGE_MAIN"]: lambda: handle_challenges(vk_id, text, self.send),
            STATES["CHALLENGE_ACTION"]: lambda: handle_challenge_action(vk_id, text, self.send),
            STATES["CHALLENGE_MARK"]: lambda: handle_mark_done(vk_id, text, self.send),
            STATES["CHALLENGE_TAKE"]: lambda: handle_take(vk_id, text, self.send),
            STATES["HEALTH_LOG_TYPE"]: lambda: handle_select_type(vk_id, text, self.send),
            STATES["HEALTH_LOG_PRESSURE"]: lambda: handle_input_pressure(vk_id, text, self.send),
            STATES["HEALTH_LOG_WEIGHT"]: lambda: handle_input_weight(vk_id, text, self.send),
            STATES["HEALTH_LOG_SUGAR"]: lambda: handle_input_sugar(vk_id, text, self.send),
            STATES["HEALTH_LOG_STEPS"]: lambda: handle_input_activity(vk_id, text, self.send),
            STATES["HEALTH_LOG_MEDS"]: lambda: handle_input_medication(vk_id, text, self.send),
            STATES["ACHIEVEMENTS"]: lambda: handle_achievements(vk_id, text, self.send),
            STATES["DISCOUNT_LIST"]: lambda: handle_buy_discount(vk_id, text, self.send),
        }

        fn = handlers.get(state)
        if fn:
            fn()
            return

        self._main_menu(vk_id, text)

    def _main_menu(self, vk_id, text):
        StateManager.set_state(vk_id, STATES["MAIN_MENU"])
        registered = bool(get_patient_profile(vk_id))

        if "Регистрация" in text:
            handle_onboarding_step1(vk_id, text, self.send)
            return

        if "Мои челленджи" in text:
            if not registered:
                self.send(vk_id, "Сначала пройди регистрацию.", keyboard=main_menu(registered=False))
                return
            StateManager.set_state(vk_id, STATES["CHALLENGE_MAIN"])
            handle_challenges(vk_id, text, self.send)
            logger.info(f"vk_id={vk_id} -> challenges")

        elif "Мой прогресс" in text:
            handle_profile(vk_id, text, self.send)
            logger.info(f"vk_id={vk_id} -> profile")

        elif "Здоровье сегодня" in text:
            if not registered:
                self.send(vk_id, "Сначала пройди регистрацию.", keyboard=main_menu(registered=False))
                return
            handle_health_today(vk_id, text, self.send)
            logger.info(f"vk_id={vk_id} -> health_log")

        elif "Достижения" in text:
            StateManager.set_state(vk_id, STATES["ACHIEVEMENTS"])
            handle_achievements(vk_id, text, self.send)

        elif "Мои скидки" in text:
            StateManager.set_state(vk_id, STATES["DISCOUNT_LIST"])
            handle_discounts(vk_id, text, self.send)

        elif "Помощь" in text:
            self._help(vk_id, registered)

        else:
            m = re.search(r"возьми\s*(\d+)", text.lower())
            if m:
                StateManager.set_state(vk_id, STATES["CHALLENGE_TAKE"])
                handle_take(vk_id, text, self.send)
                return
            m = re.search(r"(получить|куплю)\s*(\d+)", text.lower())
            if m:
                handle_buy_discount(vk_id, text, self.send)
                return
            pressure_m = re.match(r"^\s*(\d{2,3})\s*[/]\s*(\d{2,3})\s*$", text)
            if pressure_m:
                from utils.validators import validate_blood_pressure
                r = validate_blood_pressure(text)
                if r:
                    from handlers.health_log import _save_and_check as h_save
                    h_save(vk_id, "blood_pressure", r, self.send)
                    self.send(vk_id, f"❤️ Давление {r['systolic']}/{r['diastolic']} сохранено!", keyboard=main_menu(registered))
                    return
            weight_m = re.match(r"^\s*(\d{2,3}(?:[.,]\d)?)\s*$", text)
            if weight_m:
                from utils.validators import validate_weight
                r = validate_weight(text)
                if r:
                    from handlers.health_log import _save_and_check as h_save
                    h_save(vk_id, "weight", r, self.send)
                    self.send(vk_id, f"⚖️ Вес {r['weight']} кг сохранён!", keyboard=main_menu(registered))
                    return
            self.send(
                vk_id,
                "Привет, я медицинский бот!\n\nВоспользуйся кнопками меню 👇",
                keyboard=main_menu(registered),
            )

    def _help(self, vk_id, registered=True):
        faq = (
            "ℹ️ Помощь — Часто задаваемые вопросы\n\n"
            "❓ Как работают баллы?\n"
            "  +5 баллов за каждое измерение в «💊 Здоровье сегодня».\n"
            "  +100-500 баллов за завершение челленджей.\n"
            "  Баллы можно тратить на скидки в разделе «🎁 Мои скидки».\n\n"
            "❓ Как получить скидку?\n"
            "  Накопи достаточно баллов, зайди в «🎁 Мои скидки»,\n"
            "  напиши «получить N» (где N — номер скидки).\n"
            "  Промокод придёт сразу. Предъяви его на ресепшене.\n\n"
            "❓ Как привязать карту пациента?\n"
            "  При первом входе бот попросит ID пациента\n"
            "  из приложения «Клиника в смартфоне».\n"
            "  Если его нет — напиши ТЕСТ для демо-режима.\n\n"
            "❓ Как работают челленджи?\n"
            "  Нажми «🎯 Мои челленджи» → выбери из списка.\n"
            "  «возьми 1» — взять. «готово 1» — отметить выполнение.\n"
            "  Завершённые приносят баллы и продвигают по уровням.\n\n"
            "❓ Связаться с поддержкой\n"
            "  По вопросам работы бота пиши в сообщения группы.\n"
            "  По медицинским вопросам — в регистратуру клиники.\n\n"
            "💡 Уровни:\n"
            "  Новичок (0) → Стажёр (100) → Фельдшер (300) →\n"
            "  Медсестра (600) → Интерн (1000) → Ординатор (1500) →\n"
            "  Специалист (2500) → Кандидат (4000) →\n"
            "  Доктор наук (6000) → Профессор (10000)\n\n"
            "🔙 В меню — вернуться в главное меню"
        )
        self.send(vk_id, faq, keyboard=main_menu(registered))
