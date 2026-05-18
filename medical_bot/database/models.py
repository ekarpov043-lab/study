SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    vk_id BIGINT PRIMARY KEY,
    first_name TEXT NOT NULL DEFAULT '',
    last_name TEXT NOT NULL DEFAULT '',
    registered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    total_points INTEGER NOT NULL DEFAULT 0,
    level INTEGER NOT NULL DEFAULT 1 CHECK (level BETWEEN 1 AND 10),
    current_streak INTEGER NOT NULL DEFAULT 0,
    completed_challenges_count INTEGER NOT NULL DEFAULT 0,
    accepted_challenges_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS patient_profiles (
    id SERIAL PRIMARY KEY,
    vk_id BIGINT NOT NULL REFERENCES users(vk_id) ON DELETE CASCADE,
    patient_id TEXT NOT NULL UNIQUE,
    birth_date DATE,
    chronic_diseases TEXT[] DEFAULT '{}',
    height_cm INTEGER DEFAULT 170,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS challenges (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    challenge_type TEXT NOT NULL CHECK (challenge_type IN ('pressure','weight','activity','medication','blood_sugar','steps')),
    required_count INTEGER NOT NULL DEFAULT 7,
    reward_points INTEGER NOT NULL DEFAULT 100,
    related_diseases TEXT[] DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_general BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS user_challenges (
    id SERIAL PRIMARY KEY,
    vk_id BIGINT NOT NULL REFERENCES users(vk_id) ON DELETE CASCADE,
    challenge_id INTEGER NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    progress INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','completed','failed')),
    completed_at TIMESTAMPTZ,
    UNIQUE(vk_id, challenge_id)
);

CREATE TABLE IF NOT EXISTS health_logs (
    id SERIAL PRIMARY KEY,
    vk_id BIGINT NOT NULL REFERENCES users(vk_id) ON DELETE CASCADE,
    measurement_type TEXT NOT NULL,
    value JSONB NOT NULL DEFAULT '{}',
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    challenge_id INTEGER REFERENCES challenges(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS achievements (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    icon TEXT NOT NULL DEFAULT '🏆',
    condition_type TEXT NOT NULL DEFAULT '',
    condition_value INTEGER NOT NULL DEFAULT 0,
    condition_extra TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS user_achievements (
    id SERIAL PRIMARY KEY,
    vk_id BIGINT NOT NULL REFERENCES users(vk_id) ON DELETE CASCADE,
    achievement_id INTEGER NOT NULL REFERENCES achievements(id) ON DELETE CASCADE,
    earned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(vk_id, achievement_id)
);

CREATE TABLE IF NOT EXISTS discounts (
    id SERIAL PRIMARY KEY,
    service_description TEXT NOT NULL,
    discount_percent INTEGER NOT NULL CHECK (discount_percent BETWEEN 1 AND 100),
    required_points INTEGER NOT NULL,
    base_promo_code TEXT NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_discounts (
    id SERIAL PRIMARY KEY,
    vk_id BIGINT NOT NULL REFERENCES users(vk_id) ON DELETE CASCADE,
    discount_id INTEGER NOT NULL REFERENCES discounts(id) ON DELETE CASCADE,
    promo_code TEXT NOT NULL DEFAULT '',
    earned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    is_used BOOLEAN NOT NULL DEFAULT FALSE,
    used_at TIMESTAMPTZ,
    UNIQUE(vk_id, discount_id)
);

CREATE TABLE IF NOT EXISTS user_states (
    vk_id BIGINT PRIMARY KEY REFERENCES users(vk_id) ON DELETE CASCADE,
    current_state TEXT NOT NULL DEFAULT 'start',
    state_data JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS advice_log (
    id SERIAL PRIMARY KEY,
    vk_id BIGINT NOT NULL REFERENCES users(vk_id) ON DELETE CASCADE,
    advice_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""
