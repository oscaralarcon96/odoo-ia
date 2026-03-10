"""
odoo_connector.py
-----------------
Fase 1: Conexión y Extracción vía XML-RPC.

Provee funciones para autenticarse con una instancia Odoo Cloud
y extraer registros del modelo crm.lead.
"""

import xmlrpc.client
from typing import Optional


# ---------------------------------------------------------------------------
# Campos del modelo crm.lead que vamos a extraer
# ---------------------------------------------------------------------------
CRM_FIELDS = [
    "id",
    "name",               # Nombre del lead / oportunidad
    "partner_name",       # Nombre del cliente
    "stage_id",           # Etapa del pipeline
    "description",        # Notas internas
    "date_deadline",      # Fecha de cierre prevista
    "create_date",        # Fecha de creación
    "write_date",         # Última actualización
    "user_id",            # Vendedor asignado
    "email_from",         # Email del contacto
    "phone",              # Teléfono
    "active",             # Si está activo o archivado
    "type",               # 'lead' o 'opportunity'
    "tag_ids",            # Etiquetas
]


# ---------------------------------------------------------------------------
# Autenticación
# ---------------------------------------------------------------------------
def authenticate(url: str, db: str, username: str, api_key: str) -> int:
    """
    Autentica contra Odoo usando XML-RPC y retorna el uid del usuario.

    Args:
        url:       URL base de la instancia (ej. https://mycompany.odoo.com)
        db:        Nombre de la base de datos de Odoo
        username:  Email / usuario de Odoo
        api_key:   API Key generada en Odoo (Configuración → Claves de API)

    Returns:
        uid (int) si la autenticación es exitosa.

    Raises:
        ConnectionError: si no se puede conectar al servidor.
        PermissionError: si las credenciales son incorrectas.
    """
    try:
        common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
        uid: Optional[int] = common.authenticate(db, username, api_key, {})
    except Exception as exc:
        raise ConnectionError(
            f"No se pudo conectar al servidor Odoo: {exc}"
        ) from exc

    if not uid:
        raise PermissionError(
            "Autenticación fallida. Verifica la URL, DB, usuario y API Key."
        )

    return uid


# ---------------------------------------------------------------------------
# Extracción de CRM Leads / Oportunidades
# ---------------------------------------------------------------------------
def fetch_crm_leads(
    url: str,
    db: str,
    uid: int,
    api_key: str,
    limit: int = 1000,
) -> list[dict]:
    """
    Extrae registros de crm.lead desde Odoo.

    Args:
        url:    URL base de la instancia Odoo
        db:     Nombre de la base de datos
        uid:    UID del usuario autenticado
        api_key: API Key del usuario
        limit:  Número máximo de registros a extraer

    Returns:
        Lista de diccionarios con los datos de TODAS las oportunidades,
        incluyendo etapas Ganado, Perdidas y SUSPENDIDO.
    """
    try:
        models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
    except Exception as exc:
        raise ConnectionError(f"Error al conectar con el endpoint de modelos: {exc}") from exc

    # Solo oportunidades. active_test:False permite traer también
    # registros archivados (Perdidas, SUSPENDIDO, etc.)
    domain: list = [["type", "=", "opportunity"]]

    try:
        records = models.execute_kw(
            db,
            uid,
            api_key,
            "crm.lead",
            "search_read",
            [domain],
            {
                "fields": CRM_FIELDS,
                "limit": limit,
                "order": "write_date desc",
                "context": {"active_test": False},  # incluye archivados
            },
        )
    except Exception as exc:
        raise RuntimeError(f"Error al consultar crm.lead en Odoo: {exc}") from exc

    return records


# ---------------------------------------------------------------------------
# Mensajes / Conversaciones del chatter por oportunidad
# ---------------------------------------------------------------------------
def fetch_lead_messages(
    url: str,
    db: str,
    uid: int,
    api_key: str,
    lead_ids: list[int],
    messages_per_lead: int = 2,
) -> dict[int, list[dict]]:
    """
    Obtiene las últimas N conversaciones del chatter de Odoo
    para cada oportunidad en `lead_ids`.

    Hace UNA sola llamada XML-RPC (batch) para eficiencia.

    Returns:
        Dict {lead_id: [{‘author’, ‘date’, ‘body’}, ...]}
    """
    if not lead_ids:
        return {}

    try:
        models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
        messages = models.execute_kw(
            db, uid, api_key,
            "mail.message",
            "search_read",
            [[
                ["res_id", "in", lead_ids],
                ["model", "=", "crm.lead"],
                ["message_type", "in", ["email", "comment"]],
                ["body", "!=", ""],
            ]],
            {
                "fields": ["res_id", "author_id", "date", "body"],
                "order": "date desc",
                "limit": len(lead_ids) * messages_per_lead * 3,  # margen holgado
            },
        )
    except Exception:
        return {}

    # Agrupar por lead_id y quedarnos solo con los N más recientes
    result: dict[int, list[dict]] = {lid: [] for lid in lead_ids}
    for msg in messages:
        lid = msg["res_id"]
        if lid in result and len(result[lid]) < messages_per_lead:
            # Limpiar HTML del body
            body = msg.get("body", "") or ""
            body = body.replace("<br>", " ").replace("<br/>", " ")
            # Eliminar tags HTML de forma sencilla
            import re
            body = re.sub(r"<[^>]+>", "", body).strip()
            body = body[:300]  # truncar

            author = msg.get("author_id")
            author_name = author[1] if isinstance(author, (list, tuple)) and len(author) > 1 else "Desconocido"
            date_str = (msg.get("date") or "")[:10]  # solo fecha YYYY-MM-DD

            result[lid].append({
                "autor": author_name,
                "fecha": date_str,
                "mensaje": body,
            })

    return result


# ---------------------------------------------------------------------------
# Utilidad: Obtener etapas del pipeline
# ---------------------------------------------------------------------------
def fetch_pipeline_stages(url: str, db: str, uid: int, api_key: str) -> dict[int, str]:
    """
    Retorna un diccionario {stage_id: nombre_etapa} para referencia.
    """
    try:
        models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
        stages = models.execute_kw(
            db, uid, api_key,
            "crm.stage", "search_read",
            [[]],
            {"fields": ["id", "name"], "order": "sequence"},
        )
        return {s["id"]: s["name"] for s in stages}
    except Exception:
        return {}
