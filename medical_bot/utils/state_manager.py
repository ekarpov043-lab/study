"""FSM state manager — wraps user_states table."""

import json
import logging

from database.connection import execute

logger = logging.getLogger(__name__)


class StateManager:
    """Get/set/clear user state in PostgreSQL via user_states table."""

    @staticmethod
    def get_state(vk_id: int) -> str:
        row = execute(
            "SELECT current_state FROM user_states WHERE vk_id = %s",
            (vk_id,), fetchone=True,
        )
        return row["current_state"] if row else "start"

    @staticmethod
    def set_state(vk_id: int, state: str, data: dict = None) -> None:
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

    @staticmethod
    def get_data(vk_id: int) -> dict:
        row = execute(
            "SELECT state_data FROM user_states WHERE vk_id = %s",
            (vk_id,), fetchone=True,
        )
        return row["state_data"] if row else {}

    @staticmethod
    def clear_state(vk_id: int) -> None:
        execute(
            "DELETE FROM user_states WHERE vk_id = %s", (vk_id,),
        )
