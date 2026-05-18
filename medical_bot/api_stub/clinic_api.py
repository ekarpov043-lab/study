from datetime import datetime, timedelta


_patients = {
    111: {
        "vk_id": 111,
        "patient_id": "P-001",
        "first_name": "Иван",
        "last_name": "Петров",
        "birth_date": "1980-03-15",
        "age": 45,
        "diagnoses": ["Гипертоническая болезнь II ст.", "Сахарный диабет 2 типа"],
        "chronic_diseases": ["гипертония", "сахарный диабет 2 типа"],
        "history": [
            {"date": "2025-12-10", "type": "blood_pressure", "value": "145/90", "notes": "Утреннее измерение"},
            {"date": "2025-12-05", "type": "blood_test", "value": {"glucose": 7.8, "hbA1c": 7.2, "cholesterol": 6.1}, "notes": ""},
            {"date": "2025-11-20", "type": "ecg", "value": "Синусовый ритм, ЧСС 78", "notes": "Признаки гипертрофии ЛЖ"},
        ],
        "prescriptions": [
            {"medication": "Эналаприл 10 мг", "schedule": "2 раза в день", "prescribed_at": "2025-10-01"},
            {"medication": "Метформин 850 мг", "schedule": "3 раза в день после еды", "prescribed_at": "2025-10-01"},
        ],
        "appointments": [
            {"date": "2026-01-25", "time": "10:00", "doctor": "Кардиолог", "cabinet": "215"},
            {"date": "2026-02-10", "time": "11:30", "doctor": "Эндокринолог", "cabinet": "308"},
        ],
    },
    222: {
        "vk_id": 222,
        "patient_id": "P-002",
        "first_name": "Мария",
        "last_name": "Сидорова",
        "birth_date": "1987-07-22",
        "age": 38,
        "diagnoses": ["Ожирение I ст.", "Преддиабет", "Нарушение толерантности к глюкозе"],
        "chronic_diseases": ["избыточный вес", "преддиабет"],
        "history": [
            {"date": "2025-12-12", "type": "weight", "value": "92.5 кг", "notes": "ИМТ 32.1"},
            {"date": "2025-12-12", "type": "blood_test", "value": {"glucose": 6.4, "hbA1c": 5.9, "insulin": 18}, "notes": "Натощак"},
            {"date": "2025-11-28", "type": "blood_pressure", "value": "125/80", "notes": ""},
        ],
        "prescriptions": [
            {"medication": "Метформин 500 мг", "schedule": "2 раза в день", "prescribed_at": "2025-11-01"},
            {"medication": "Витамин D 2000 МЕ", "schedule": "1 раз в день", "prescribed_at": "2025-11-01"},
        ],
        "appointments": [
            {"date": "2026-01-20", "time": "09:30", "doctor": "Диетолог", "cabinet": "112"},
        ],
    },
    333: {
        "vk_id": 333,
        "patient_id": "P-003",
        "first_name": "Алексей",
        "last_name": "Козлов",
        "birth_date": "1973-11-08",
        "age": 52,
        "diagnoses": ["Ишемическая болезнь сердца", "Постинфарктный кардиосклероз (2025-07)"],
        "chronic_diseases": ["ИБС", "после инфаркта"],
        "history": [
            {"date": "2025-12-15", "type": "blood_pressure", "value": "130/85", "notes": "На фоне терапии"},
            {"date": "2025-12-15", "type": "blood_test", "value": {"cholesterol": 4.2, "LDL": 2.8, "HDL": 1.1, "triglycerides": 1.8}, "notes": "Липидный профиль"},
            {"date": "2025-12-01", "type": "ecg", "value": "Синусовый ритм, ЧСС 72", "notes": "Рубец в передне-перегородочной области"},
            {"date": "2025-11-10", "type": "exercise_test", "value": "Тредмил-тест: 8 METS, без ишемии", "notes": "ФК II"},
        ],
        "prescriptions": [
            {"medication": "Аспирин 100 мг", "schedule": "1 раз в день", "prescribed_at": "2025-08-01"},
            {"medication": "Бисопролол 5 мг", "schedule": "1 раз в день утром", "prescribed_at": "2025-08-01"},
            {"medication": "Аторвастатин 40 мг", "schedule": "1 раз в день вечером", "prescribed_at": "2025-08-01"},
            {"medication": "Клопидогрел 75 мг", "schedule": "1 раз в день", "prescribed_at": "2025-08-01"},
        ],
        "appointments": [
            {"date": "2026-01-28", "time": "14:00", "doctor": "Кардиолог", "cabinet": "215"},
            {"date": "2026-02-15", "time": "10:00", "doctor": "Реабилитолог", "cabinet": "405"},
        ],
    },
    444: {
        "vk_id": 444,
        "patient_id": "P-004",
        "first_name": "Елена",
        "last_name": "Новикова",
        "birth_date": "1964-04-30",
        "age": 61,
        "diagnoses": ["Остеопороз (T-критерий -2.8)", "Ревматоидный артрит серопозитивный"],
        "chronic_diseases": ["остеопороз", "артрит"],
        "history": [
            {"date": "2025-12-08", "type": "densitometry", "value": "Поясничный отдел: T=-2.8, шейка бедра: T=-2.3", "notes": "Остеопороз"},
            {"date": "2025-11-25", "type": "blood_test", "value": {"CRP": 12, "ESR": 28, "RF": 45, "vitamin_D": 18}, "notes": "Активность воспаления умеренная"},
            {"date": "2025-11-25", "type": "joint_ultrasound", "value": "Синовит лучезапястных и коленных суставов", "notes": ""},
        ],
        "prescriptions": [
            {"medication": "Метотрексат 15 мг/нед", "schedule": "1 раз в неделю", "prescribed_at": "2025-09-15"},
            {"medication": "Фолиевая кислота 5 мг", "schedule": "через день", "prescribed_at": "2025-09-15"},
            {"medication": "Алендронат 70 мг/нед", "schedule": "1 раз в неделю утром натощак", "prescribed_at": "2025-10-01"},
            {"medication": "Кальций D3", "schedule": "2 раза в день", "prescribed_at": "2025-10-01"},
        ],
        "appointments": [
            {"date": "2026-01-22", "time": "11:00", "doctor": "Ревматолог", "cabinet": "320"},
            {"date": "2026-02-05", "time": "09:00", "doctor": "Денситометрия", "cabinet": "105"},
        ],
    },
    555: {
        "vk_id": 555,
        "patient_id": "P-005",
        "first_name": "Дмитрий",
        "last_name": "Волков",
        "birth_date": "1996-08-14",
        "age": 29,
        "diagnoses": [],
        "chronic_diseases": [],
        "history": [
            {"date": "2025-11-30", "type": "checkup", "value": "Общий анализ крови, биохимия — норма", "notes": "Здоров"},
            {"date": "2025-11-30", "type": "blood_pressure", "value": "118/75", "notes": ""},
            {"date": "2025-06-10", "type": "blood_test", "value": {"glucose": 4.8, "cholesterol": 4.5, "ALT": 22, "AST": 20}, "notes": "В пределах нормы"},
        ],
        "prescriptions": [],
        "appointments": [
            {"date": "2026-02-01", "time": "16:00", "doctor": "Терапевт", "cabinet": "101"},
        ],
    },
}


class ClinicAPI:
    def get_patient_by_vk_id(self, vk_id: int) -> dict | None:
        return _patients.get(vk_id)

    def get_patient_history(self, patient_id: str) -> dict:
        for p in _patients.values():
            if p["patient_id"] == patient_id:
                return {"patient_id": patient_id, "records": p["history"]}
        return {"patient_id": patient_id, "records": []}

    def get_appointments(self, patient_id: str) -> list:
        for p in _patients.values():
            if p["patient_id"] == patient_id:
                return p["appointments"]
        return []

    def get_prescriptions(self, patient_id: str) -> list:
        for p in _patients.values():
            if p["patient_id"] == patient_id:
                return p["prescriptions"]
        return []
