"""Onboarding FSM — registration with height input for BMI."""

import logging
import random

from utils.state_manager import StateManager
from utils.keyboards import confirm_keyboard, back_to_menu, main_menu
from utils.constants import STATES
from database.queries import (
    get_or_create_user, save_patient_profile, get_user,
    assign_initial_challenges, get_user_challenges,
)
from api_stub.clinic_api import ClinicAPI

logger = logging.getLogger(__name__)
clinic_api = ClinicAPI()


def handle_onboarding_step1(vk_id, text, send):
    StateManager.set_state(vk_id, STATES["ONBOARDING_ID"])
    logger.info(f"User {vk_id} started onboarding")
    send(
        vk_id,
        "Привет! Я бот клиники «Клиника в смартфоне». Давай познакомимся!\n\n"
        "Введи свой ID пациента из приложения «Клиника в смартфоне»\n"
        "(или напиши ТЕСТ для демо-режима).",
        keyboard=back_to_menu(),
    )


def handle_onboarding_input(vk_id, text, send):
    patient = None
    if text.upper() == "ТЕСТ":
        test_ids = [111, 222, 333, 444, 555]
        chosen = random.choice(test_ids)
        patient = clinic_api.get_patient_by_vk_id(chosen)
        logger.info(f"User {vk_id} chose TEST -> patient vk_id={chosen}")
    else:
        for pid in [111, 222, 333, 444, 555]:
            p = clinic_api.get_patient_by_vk_id(pid)
            if p and p["patient_id"].lower() == text.strip().lower():
                patient = p
                break
        if patient:
            logger.info(f"User {vk_id} entered patient_id={text} -> found")

    if not patient:
        logger.warning(f"User {vk_id} entered invalid patient_id={text}")
        send(
            vk_id,
            "❌ Пациент с таким ID не найден. Попробуй ещё раз\n"
            "или напиши ТЕСТ для демо-режима.",
        )
        return

    StateManager.set_state(vk_id, STATES["ONBOARDING_CONFIRM"], {"patient": patient})
    diseases = ", ".join(patient["diagnoses"]) if patient["diagnoses"] else "нет"
    send(
        vk_id,
        f"Подтверди, что ты {patient['first_name']} {patient['last_name']}?\n"
        f"🆔 ID: {patient['patient_id']}\n"
        f"🩺 Диагнозы: {diseases}\n\n"
        f"Это ты?",
        keyboard=confirm_keyboard(),
    )


def handle_onboarding_confirm(vk_id, text, send, first_name, last_name):
    sd = StateManager.get_data(vk_id)
    patient = sd.get("patient")
    if not patient:
        logger.error(f"User {vk_id} onboarding_confirm missing patient data")
        StateManager.set_state(vk_id, STATES["MAIN_MENU"])
        send(vk_id, "Что-то пошло не так. Начни заново.", keyboard=main_menu())
        return

    if "Да, это я" in text or text.lower() in ("да", "yes"):
        get_or_create_user(vk_id, patient["first_name"], patient["last_name"])
        logger.info(f"User {vk_id} confirmed as {patient['first_name']} {patient['last_name']}")
        StateManager.set_state(
            vk_id, STATES["ONBOARDING_HEIGHT"],
            {"patient": patient},
        )
        send(
            vk_id,
            "Отлично! Теперь укажи свой рост в сантиметрах\n"
            "(например: 175). Это нужно для расчёта ИМТ\n"
            "и более точных рекомендаций.",
            keyboard=back_to_menu(),
        )
    else:
        StateManager.set_state(vk_id, STATES["ONBOARDING_ID"])
        send(vk_id, "Попробуем ещё раз. Введи ID пациента или напиши ТЕСТ.", keyboard=back_to_menu())


def handle_onboarding_height(vk_id, text, send):
    """Step 3: save height, auto-assign challenges, show welcome."""
    try:
        height = int(text.strip())
        if height < 100 or height > 250:
            raise ValueError
    except (ValueError, TypeError):
        logger.warning(f"User {vk_id} entered invalid height: {text}")
        send(vk_id, "❌ Введи рост в сантиметрах числом от 100 до 250.\nНапример: 175", keyboard=back_to_menu())
        return

    sd = StateManager.get_data(vk_id)
    patient = sd.get("patient")
    if not patient:
        StateManager.set_state(vk_id, STATES["MAIN_MENU"])
        send(vk_id, "Ошибка. Начни заново.", keyboard=main_menu())
        return

    save_patient_profile(
        vk_id=vk_id,
        patient_id=patient["patient_id"],
        birth_date=patient["birth_date"],
        diseases=patient["chronic_diseases"],
        height=height,
    )
    assigned = assign_initial_challenges(vk_id)
    user = get_user(vk_id)
    active_uc = get_user_challenges(vk_id)

    logger.info(
        f"User {vk_id} registered: height={height}, "
        f"challenges={assigned}, diseases={patient['chronic_diseases']}"
    )

    welcome = (
        f"✅ Всё готово, {patient['first_name']}!\n\n"
        f"💎 Система баллов:\n"
        f"  • +5 баллов за каждое измерение\n"
        f"  • До +{sum(uc['reward_points'] for uc in active_uc) if active_uc else 0} баллов за челленджи\n"
        f"  • Баллы можно тратить на скидки\n\n"
        f"📋 Тебе назначено {assigned} челленджа(ей):\n"
    )
    for uc in active_uc:
        welcome += f"  • {uc['title']} — {uc['progress']}/{uc['required_count']}\n"
    welcome += (
        "\nНачни с «💊 Здоровье сегодня» — записывай показатели\n"
        "и зарабатывай баллы!"
    )
    StateManager.set_state(vk_id, STATES["MAIN_MENU"])
    send(vk_id, welcome, keyboard=main_menu())
