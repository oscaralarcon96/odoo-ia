"""
data_processor.py
-----------------
Fase 2: Procesamiento y Contexto para la IA.

Convierte los registros de crm.lead en:
  - Un DataFrame de Pandas para análisis estructurado
  - Un bloque de texto Markdown para injectar como contexto al LLM
"""

import pandas as pd


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------
def _extract_name(field_value, fallback: str = "—") -> str:
    """Extrae el nombre de un campo many2one (tuple o False)."""
    if isinstance(field_value, (list, tuple)) and len(field_value) >= 2:
        return str(field_value[1])
    return fallback


# Traducción de etapas inglés → español
STAGE_TRANSLATIONS = {
    "New": "Nuevo",
    "Proposition": "Propuesta",
    "Won": "Ganada",
    "Qualified": "Calificada",
    "Teleconference": "Telereunión",
    "Lost": "Perdida",
}

def _translate_stage(name: str) -> str:
    return STAGE_TRANSLATIONS.get(name, name)


def _fmt_date(val) -> str:
    """Formatea un valor datetime de Odoo (string ISO) a YYYY-MM-DD."""
    if not val or val == "—":
        return "—"
    return str(val)[:10]


# ---------------------------------------------------------------------------
# Conversión a DataFrame
# ---------------------------------------------------------------------------
def leads_to_dataframe(leads: list[dict]) -> pd.DataFrame:
    """
    Convierte la lista de dicts retornada por Odoo en un DataFrame limpio.

    Columnas resultantes:
        id, nombre, cliente, etapa, tipo, vendedor, email, telefono,
        fecha_creacion, fecha_actualizacion, fecha_cierre, notas,
        ultimas_conversaciones (se añade después con attach_messages)
    """
    if not leads:
        return pd.DataFrame()

    rows = []
    for lead in leads:
        rows.append(
            {
                "id": lead.get("id"),
                "nombre": lead.get("name", "—"),
                "cliente": lead.get("partner_name") or "—",
                "etapa": _translate_stage(_extract_name(lead.get("stage_id"), "Sin etapa")),
                "tipo": "Oportunidad" if lead.get("type") == "opportunity" else "Lead",
                "vendedor": _extract_name(lead.get("user_id"), "Sin asignar"),
                "email": lead.get("email_from") or "—",
                "telefono": lead.get("phone") or "—",
                "fecha_creacion": _fmt_date(lead.get("create_date")),
                "fecha_actualizacion": _fmt_date(lead.get("write_date")),
                "fecha_cierre": lead.get("date_deadline") or "—",
                "notas": (lead.get("description") or "").strip()[:300],
                "ultimas_conversaciones": "",  # se rellena con attach_messages()
            }
        )

    df = pd.DataFrame(rows)

    # Convertir fechas a datetime
    df["fecha_cierre"] = pd.to_datetime(df["fecha_cierre"], errors="coerce")
    df["fecha_creacion"] = pd.to_datetime(df["fecha_creacion"], errors="coerce")
    df["fecha_actualizacion"] = pd.to_datetime(df["fecha_actualizacion"], errors="coerce")

    # Ordenar por fecha de actualización más reciente primero
    df = df.sort_values("fecha_actualizacion", ascending=False).reset_index(drop=True)

    return df


# ---------------------------------------------------------------------------
# Adjuntar mensajes del chatter al DataFrame
# ---------------------------------------------------------------------------
def attach_messages(df: pd.DataFrame, messages_by_id: dict) -> pd.DataFrame:
    """
    Añade la columna 'ultimas_conversaciones' al DataFrame con las
    últimas N conversaciones de cada oportunidad.

    Args:
        df:             DataFrame de oportunidades (debe tener columna 'id')
        messages_by_id: Dict {lead_id: [{'autor', 'fecha', 'mensaje'}, ...]}

    Returns:
        DataFrame con la columna 'ultimas_conversaciones' rellenada.
    """
    def format_msgs(lead_id):
        msgs = messages_by_id.get(int(lead_id), [])
        if not msgs:
            return "Sin conversaciones registradas"
        parts = []
        for m in msgs:
            parts.append(f"[{m['fecha']}] {m['autor']}: {m['mensaje']}")
        return " | ".join(parts)

    df = df.copy()
    df["ultimas_conversaciones"] = df["id"].apply(format_msgs)
    return df


# ---------------------------------------------------------------------------
# Conversión a texto Markdown para el LLM (RAG simple)
# ---------------------------------------------------------------------------
def leads_to_text_context(df: pd.DataFrame, max_rows: int = 150) -> str:
    """
    Serializa el DataFrame como texto Markdown para inyectar al LLM como contexto.
    Incluye fechas y últimas conversaciones para que la IA tenga contexto temporal.
    """
    if df.empty:
        return "No hay datos de CRM disponibles."

    sample = df.head(max_rows).copy()

    # Formatear fechas para legibilidad
    for col in ["fecha_cierre", "fecha_creacion", "fecha_actualizacion"]:
        if col in sample.columns:
            sample[col] = sample[col].apply(
                lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else "—"
            )

    cols = [
        "id", "nombre", "cliente", "etapa", "vendedor",
        "fecha_creacion", "fecha_actualizacion", "fecha_cierre",
        "ultimas_conversaciones",
    ]
    cols = [c for c in cols if c in sample.columns]
    table_md = sample[cols].to_markdown(index=False)

    total = len(df)
    shown = len(sample)
    footer = f"\n\n> Mostrando {shown} de {total} registros totales."

    return f"## Pipeline CRM — Oportunidades\n\n{table_md}{footer}"


# ---------------------------------------------------------------------------
# Filtros útiles
# ---------------------------------------------------------------------------
def filter_opportunities(df: pd.DataFrame) -> pd.DataFrame:
    """Retorna solo las Oportunidades (excluye leads sin calificar)."""
    return df[df["tipo"] == "Oportunidad"].copy()


def get_summary_stats(df: pd.DataFrame) -> dict:
    """Retorna métricas resumen del pipeline para mostrar en la UI."""
    if df.empty:
        return {"total_oportunidades": 0}

    return {
        "total_oportunidades": int(len(df)),
    }
