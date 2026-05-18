"""All SQL query functions for the bot."""

import logging
from datetime import date, timedelta, datetime
import random
import string

from database.connection import execute

logger = logging.getLogger(__name__)


# ─── Users ───────────────────────────────────────────────

def get_or_create_user(vk_id, first_name="", last_name=""):
    user = execute(
        "SELECT * FROM users WHERE vk_id = %s", (vk_id,), fetchone=True
    )
    if not user:
        execute(
            "INSERT INTO users (vk_id, first_name, last_name) VALUES (%s, %s, %s)",
            (vk_id, first_name, last_name),
        )
        user = execute(
            "SELECT * FROM users WHERE vk_id = %s", (vk_id,), fetchone=True
        )
        logger.info(f"New user created: vk_id={vk_id}, name={first_name} {last_name}")
    return user


def get_user(vk_id):
    return execute("SELECT * FROM users WHERE vk_id = %s", (vk_id,), fetchone=True)


def get_all_users():
    return execute("SELECT * FROM users ORDER BY vk_id", fetchall=True)


def add_points(vk_id, points):
    execute(
        "UPDATE users SET total_points = total_points + %s WHERE vk_id = %s",
        (points, vk_id),
    )
    user = get_user(vk_id)
    from utils.levels import level_from_points
    new_level = level_from_points(user["total_points"])
    if new_level != user["level"]:
        execute(
            "UPDATE users SET level = %s WHERE vk_id = %s",
            (new_level, vk_id),
        )
        user["level"] = new_level
        logger.info(f"vk_id={vk_id} leveled up to {new_level}")
    logger.info(f"vk_id={vk_id} +{points} points (total={user['total_points']})")
    return user


def add_points_and_notify(vk_id, points, send_callback):
    """Add points and send animated notification."""
    user = add_points(vk_id, points)
    send_callback(vk_id, f"+{points} ⭐ баллов! Всего: {user['total_points']}")
    return user


def recalc_level(vk_id):
    user = get_user(vk_id)
    if not user:
        return
    from utils.levels import level_from_points
    new_level = level_from_points(user["total_points"])
    execute("UPDATE users SET level = %s WHERE vk_id = %s", (new_level, vk_id))


def increment_accepted_challenges(vk_id):
    execute(
        "UPDATE users SET accepted_challenges_count = accepted_challenges_count + 1 WHERE vk_id = %s",
        (vk_id,),
    )


def increment_completed_challenges(vk_id):
    execute(
        "UPDATE users SET completed_challenges_count = completed_challenges_count + 1 WHERE vk_id = %s",
        (vk_id,),
    )


def update_streak(vk_id):
    today = date.today()
    row = execute(
        """
        SELECT COUNT(DISTINCT DATE(recorded_at)) as cnt,
               MAX(DATE(recorded_at)) as last_date
        FROM health_logs
        WHERE vk_id = %s AND DATE(recorded_at) >= %s
        """,
        (vk_id, today - timedelta(days=30)),
        fetchone=True,
    )
    if not row or not row["last_date"]:
        execute("UPDATE users SET current_streak = 0 WHERE vk_id = %s", (vk_id,))
        return 0
    if row["last_date"] < today - timedelta(days=1):
        execute("UPDATE users SET current_streak = 0 WHERE vk_id = %s", (vk_id,))
        return 0
    streak = 1
    check = today - timedelta(days=1)
    while True:
        has = execute(
            "SELECT 1 FROM health_logs WHERE vk_id = %s AND DATE(recorded_at) = %s LIMIT 1",
            (vk_id, check), fetchone=True,
        )
        if has:
            streak += 1
            check -= timedelta(days=1)
        else:
            break
    execute("UPDATE users SET current_streak = %s WHERE vk_id = %s", (streak, vk_id))
    return streak


def get_last_active_date(vk_id):
    row = execute(
        "SELECT MAX(DATE(recorded_at)) as last_date FROM health_logs WHERE vk_id = %s",
        (vk_id,), fetchone=True,
    )
    return row["last_date"] if row else None


# ─── Patient profiles ────────────────────────────────────

def get_patient_profile(vk_id):
    return execute(
        "SELECT * FROM patient_profiles WHERE vk_id = %s", (vk_id,), fetchone=True
    )


def get_patient_by_id(patient_id):
    return execute(
        "SELECT * FROM patient_profiles WHERE patient_id = %s",
        (patient_id,), fetchone=True,
    )


def save_patient_profile(vk_id, patient_id, birth_date, diseases, height=170):
    execute(
        """
        INSERT INTO patient_profiles (vk_id, patient_id, birth_date, chronic_diseases, height_cm)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (patient_id) DO UPDATE
        SET birth_date = EXCLUDED.birth_date,
            chronic_diseases = EXCLUDED.chronic_diseases
        """,
        (vk_id, patient_id, birth_date, diseases, height),
    )


# ─── Challenges ──────────────────────────────────────────

def get_active_challenges():
    return execute(
        "SELECT * FROM challenges WHERE is_active = TRUE ORDER BY id",
        fetchall=True,
    )


def get_challenge(challenge_id):
    return execute(
        "SELECT * FROM challenges WHERE id = %s", (challenge_id,), fetchone=True,
    )


def get_user_challenges(vk_id):
    return execute(
        """
        SELECT uc.*, c.title, c.description, c.challenge_type,
               c.required_count, c.reward_points, c.is_general
        FROM user_challenges uc
        JOIN challenges c ON c.id = uc.challenge_id
        WHERE uc.vk_id = %s AND uc.status = 'active'
        """,
        (vk_id,), fetchall=True,
    )


def get_completed_challenges(vk_id):
    return execute(
        """
        SELECT uc.*, c.title, c.challenge_type
        FROM user_challenges uc
        JOIN challenges c ON c.id = uc.challenge_id
        WHERE uc.vk_id = %s AND uc.status = 'completed'
        ORDER BY uc.completed_at DESC
        """,
        (vk_id,), fetchall=True,
    )


def get_matching_challenges(user_diseases):
    if user_diseases:
        return execute(
            """
            SELECT * FROM challenges
            WHERE is_active = TRUE
              AND (is_general = TRUE
                   OR related_diseases && %s::text[])
            ORDER BY is_general DESC, id
            """,
            (user_diseases,), fetchall=True,
        )
    return execute(
        "SELECT * FROM challenges WHERE is_active = TRUE AND is_general = TRUE ORDER BY id",
        fetchall=True,
    )


def accept_challenge(vk_id, challenge_id):
    challenge = get_challenge(challenge_id)
    if not challenge:
        return False
    existing = execute(
        "SELECT 1 FROM user_challenges WHERE vk_id = %s AND challenge_id = %s",
        (vk_id, challenge_id), fetchone=True,
    )
    if existing:
        return False
    execute(
        "INSERT INTO user_challenges (vk_id, challenge_id, progress, status) VALUES (%s, %s, 0, 'active')",
        (vk_id, challenge_id),
    )
    increment_accepted_challenges(vk_id)
    return True


def update_challenge_progress(vk_id, challenge_id, increment=1):
    uc = execute(
        "SELECT * FROM user_challenges WHERE vk_id = %s AND challenge_id = %s AND status = 'active'",
        (vk_id, challenge_id), fetchone=True,
    )
    if not uc:
        return None
    challenge = get_challenge(challenge_id)
    if not challenge:
        return None
    new_progress = uc["progress"] + increment
    if new_progress >= challenge["required_count"]:
        execute(
            "UPDATE user_challenges SET progress = %s, status = 'completed', completed_at = NOW() WHERE id = %s",
            (new_progress, uc["id"]),
        )
        add_points(vk_id, challenge["reward_points"])
        increment_completed_challenges(vk_id)
        logger.info(
            f"vk_id={vk_id} completed challenge #{challenge_id} "
            f"\"{challenge['title']}\" +{challenge['reward_points']} pts"
        )
        return execute(
            "SELECT uc.*, c.title, c.challenge_type, c.required_count, c.reward_points "
            "FROM user_challenges uc JOIN challenges c ON c.id = uc.challenge_id WHERE uc.id = %s",
            (uc["id"],), fetchone=True,
        )
    execute(
        "UPDATE user_challenges SET progress = %s WHERE id = %s",
        (new_progress, uc["id"]),
    )
    return execute(
        "SELECT uc.*, c.title, c.challenge_type, c.required_count, c.reward_points "
        "FROM user_challenges uc JOIN challenges c ON c.id = uc.challenge_id WHERE uc.id = %s",
        (uc["id"],), fetchone=True,
    )


def assign_initial_challenges(vk_id):
    profile = get_patient_profile(vk_id)
    diseases = profile["chronic_diseases"] if profile else []
    challenges = get_matching_challenges(diseases)
    assigned = 0
    for c in challenges:
        if assigned >= 3:
            break
        existing = execute(
            "SELECT 1 FROM user_challenges WHERE vk_id = %s AND challenge_id = %s",
            (vk_id, c["id"]), fetchone=True,
        )
        if not existing:
            execute(
                "INSERT INTO user_challenges (vk_id, challenge_id, progress, status) VALUES (%s, %s, 0, 'active')",
                (vk_id, c["id"]),
            )
            increment_accepted_challenges(vk_id)
            assigned += 1
    return assigned


# ─── Health logs ─────────────────────────────────────────

def save_health_log(vk_id, measurement_type, value, challenge_id=None):
    import json
    if isinstance(value, dict):
        value = json.dumps(value)
    execute(
        "INSERT INTO health_logs (vk_id, measurement_type, value, challenge_id) VALUES (%s, %s, %s, %s)",
        (vk_id, measurement_type, value, challenge_id),
    )


def get_health_logs(vk_id, measurement_type=None, limit=10):
    if measurement_type:
        return execute(
            "SELECT * FROM health_logs WHERE vk_id = %s AND measurement_type = %s ORDER BY recorded_at DESC LIMIT %s",
            (vk_id, measurement_type, limit), fetchall=True,
        )
    return execute(
        "SELECT * FROM health_logs WHERE vk_id = %s ORDER BY recorded_at DESC LIMIT %s",
        (vk_id, limit), fetchall=True,
    )


def get_health_logs_week(vk_id):
    week_ago = date.today() - timedelta(days=7)
    return execute(
        "SELECT * FROM health_logs WHERE vk_id = %s AND recorded_at >= %s ORDER BY recorded_at DESC",
        (vk_id, week_ago), fetchall=True,
    )


def count_health_logs(vk_id):
    row = execute(
        "SELECT COUNT(*) as cnt FROM health_logs WHERE vk_id = %s",
        (vk_id,), fetchone=True,
    )
    return row["cnt"] if row else 0


def count_logs_by_type(vk_id, mtype):
    row = execute(
        "SELECT COUNT(*) as cnt FROM health_logs WHERE vk_id = %s AND measurement_type = %s",
        (vk_id, mtype), fetchone=True,
    )
    return row["cnt"] if row else 0


def get_total_steps(vk_id):
    row = execute(
        """
        SELECT COALESCE(SUM((value->>'steps')::integer), 0) as total
        FROM health_logs
        WHERE vk_id = %s AND measurement_type = 'steps'
        """,
        (vk_id,), fetchone=True,
    )
    return row["total"] if row else 0


def get_points_earned_this_week(vk_id):
    week_ago = date.today() - timedelta(days=7)
    row = execute(
        """
        SELECT COALESCE(SUM(uc.reward_points), 0) as total
        FROM user_challenges uc
        WHERE uc.vk_id = %s AND uc.status = 'completed' AND uc.completed_at >= %s
        """,
        (vk_id, week_ago), fetchone=True,
    )
    return (row["total"] if row else 0) + (count_health_logs(vk_id) * 5)


# ─── Achievements ────────────────────────────────────────

def get_all_achievements():
    return execute(
        "SELECT * FROM achievements WHERE is_active = TRUE ORDER BY category, id",
        fetchall=True,
    )


def get_user_achievements(vk_id):
    return execute(
        """
        SELECT a.*, ua.earned_at
        FROM achievements a
        JOIN user_achievements ua ON ua.achievement_id = a.id
        WHERE ua.vk_id = %s
        ORDER BY ua.earned_at DESC
        """,
        (vk_id,), fetchall=True,
    )


def add_achievement(vk_id, achievement_id):
    execute(
        "INSERT INTO user_achievements (vk_id, achievement_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        (vk_id, achievement_id),
    )


def has_achievement(vk_id, achievement_id):
    return bool(execute(
        "SELECT 1 FROM user_achievements WHERE vk_id = %s AND achievement_id = %s",
        (vk_id, achievement_id), fetchone=True,
    ))


def check_and_award_achievements(vk_id):
    """Check all achievements conditions, award unearned ones. Return newly awarded list."""
    user = get_user(vk_id)
    if not user:
        return []
    profile = get_patient_profile(vk_id)
    total_logs = count_health_logs(vk_id)
    completed_count = user["completed_challenges_count"]
    taken_count = user["accepted_challenges_count"]
    streak = user["current_streak"]
    all_achievements = get_all_achievements()
    awarded = []

    for a in all_achievements:
        if has_achievement(vk_id, a["id"]):
            continue
        earned = False
        ct = a["condition_type"]
        cv = a["condition_value"]
        ce = a["condition_extra"]

        if ct == "logs_total" and total_logs >= cv:
            earned = True
        elif ct == "challenges_completed" and completed_count >= cv:
            earned = True
        elif ct == "challenges_taken" and taken_count >= cv:
            earned = True
        elif ct == "streak_days" and streak >= cv:
            earned = True
        elif ct == "points_total" and user["total_points"] >= cv:
            earned = True
        elif ct == "profile_filled" and profile is not None:
            earned = True
        elif ct == "logs_type" and count_logs_by_type(vk_id, ce) >= cv:
            earned = True
        elif ct == "steps_total" and get_total_steps(vk_id) >= cv:
            earned = True

        if earned:
            add_achievement(vk_id, a["id"])
            awarded.append(a)
    return awarded


# ─── Discounts ───────────────────────────────────────────

def generate_promo_code(discount_percent, vk_id):
    """Generate unique promo code: HEALTH[%]-[USER_ID]-[RANDOM5]."""
    rand = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"HEALTH{discount_percent}-{vk_id}-{rand}"


def get_available_discounts(vk_id):
    return execute(
        """
        SELECT d.*, ud.id as user_discount_id, ud.is_used,
               ud.promo_code as user_promo_code, ud.expires_at as user_expires_at
        FROM discounts d
        LEFT JOIN user_discounts ud ON ud.discount_id = d.id AND ud.vk_id = %s
        WHERE d.is_active = TRUE
        ORDER BY d.required_points
        """,
        (vk_id,), fetchall=True,
    )


def purchase_discount(vk_id, discount_id, send_callback=None):
    discount = execute(
        "SELECT * FROM discounts WHERE id = %s AND is_active = TRUE",
        (discount_id,), fetchone=True,
    )
    if not discount:
        return None
    user = get_user(vk_id)
    if user["total_points"] < discount["required_points"]:
        return None
    existing = execute(
        "SELECT 1 FROM user_discounts WHERE vk_id = %s AND discount_id = %s",
        (vk_id, discount_id), fetchone=True,
    )
    if existing:
        return None
    execute(
        "UPDATE users SET total_points = total_points - %s WHERE vk_id = %s",
        (discount["required_points"], vk_id),
    )
    recalc_level(vk_id)
    promo = generate_promo_code(discount["discount_percent"], vk_id)
    expires = datetime.now() + timedelta(days=30)
    execute(
        "INSERT INTO user_discounts (vk_id, discount_id, promo_code, expires_at) VALUES (%s, %s, %s, %s)",
        (vk_id, discount_id, promo, expires),
    )
    if send_callback and discount["discount_percent"] == 100:
        send_callback(vk_id, f"🎉 +{discount['required_points']} баллов потрачено!")
    return {
        "promo_code": promo,
        "expires_at": expires,
        "discount_percent": discount["discount_percent"],
        "service_description": discount["service_description"],
    }


# ─── User states ─────────────────────────────────────────

def get_user_state(vk_id):
    return execute(
        "SELECT * FROM user_states WHERE vk_id = %s", (vk_id,), fetchone=True,
    )


def set_user_state(vk_id, state, data=None):
    import json
    row = execute(
        "SELECT 1 FROM user_states WHERE vk_id = %s", (vk_id,), fetchone=True,
    )
    if row:
        execute(
            "UPDATE user_states SET current_state = %s, state_data = %s WHERE vk_id = %s",
            (state, json.dumps(data or {}), vk_id),
        )
    else:
        execute(
            "INSERT INTO user_states (vk_id, current_state, state_data) VALUES (%s, %s, %s)",
            (vk_id, state, json.dumps(data or {})),
        )


# ─── Advice ──────────────────────────────────────────────

def save_advice(vk_id, text):
    execute(
        "INSERT INTO advice_log (vk_id, advice_text) VALUES (%s, %s)",
        (vk_id, text),
    )
