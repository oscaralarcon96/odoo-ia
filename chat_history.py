"""
chat_history.py
---------------
Manejo del historial de conversación persistente en disco.
Los mensajes se guardan en chat_history.json en la misma carpeta del proyecto.
"""

import json
import os
from datetime import datetime

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "chat_history.json")
MAX_MESSAGES = 200  # Límite para no crecer indefinidamente


def load_history(path: str = HISTORY_FILE) -> list[dict]:
    """
    Carga el historial de conversación desde disco.
    Retorna una lista vacía si el archivo no existe o está corrupto.
    """
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Validar que sea una lista de dicts con role/content
        if isinstance(data, list):
            return [m for m in data if isinstance(m, dict) and "role" in m and "content" in m]
    except (json.JSONDecodeError, OSError):
        pass
    return []


def save_history(messages: list[dict], path: str = HISTORY_FILE) -> None:
    """
    Guarda el historial de conversación en disco.
    Mantiene solo los últimos MAX_MESSAGES mensajes.
    """
    try:
        trimmed = messages[-MAX_MESSAGES:] if len(messages) > MAX_MESSAGES else messages
        with open(path, "w", encoding="utf-8") as f:
            json.dump(trimmed, f, ensure_ascii=False, indent=2)
    except OSError:
        pass  # No interrumpir la app si falla el guardado


def clear_history(path: str = HISTORY_FILE) -> None:
    """
    Borra el historial persistente del disco.
    """
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def get_history_stats(path: str = HISTORY_FILE) -> dict:
    """
    Retorna estadísticas del historial guardado.
    """
    if not os.path.exists(path):
        return {"exists": False, "count": 0, "size_kb": 0}
    try:
        size_kb = round(os.path.getsize(path) / 1024, 1)
        messages = load_history(path)
        return {"exists": True, "count": len(messages), "size_kb": size_kb}
    except OSError:
        return {"exists": False, "count": 0, "size_kb": 0}
