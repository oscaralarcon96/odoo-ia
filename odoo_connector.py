"""
odoo_connector.py
-----------------
Fase 1: Conexión y Extracción vía XML-RPC.

Provee funciones para autenticarse con una instancia Odoo Cloud,
extraer registros del modelo crm.lead y crear nuevas oportunidades.
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
    Solo trae oportunidades (type='opportunity'), incluyendo archivadas.
    Ordenadas por actividad más reciente primero.
    """
    try:
        models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
    except Exception as exc:
        raise ConnectionError(f"Error al conectar con el endpoint de modelos: {exc}") from exc

    domain: list = [["type", "=", "opportunity"]]

    try:
        records = models.execute_kw(
            db, uid, api_key,
            "crm.lead",
            "search_read",
            [domain],
            {
                "fields": CRM_FIELDS,
                "limit": limit,
                "order": "write_date desc",
                "context": {"active_test": False},
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
    para cada oportunidad en `lead_ids`. Hace UNA sola llamada (batch).
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
                "limit": len(lead_ids) * messages_per_lead * 3,
            },
        )
    except Exception:
        return {}

    result: dict[int, list[dict]] = {lid: [] for lid in lead_ids}
    for msg in messages:
        lid = msg["res_id"]
        if lid in result and len(result[lid]) < messages_per_lead:
            body = msg.get("body", "") or ""
            body = body.replace("<br>", " ").replace("<br/>", " ")
            import re
            body = re.sub(r"<[^>]+>", "", body).strip()[:300]

            author = msg.get("author_id")
            author_name = author[1] if isinstance(author, (list, tuple)) and len(author) > 1 else "Desconocido"
            date_str = (msg.get("date") or "")[:10]

            result[lid].append({
                "autor": author_name,
                "fecha": date_str,
                "mensaje": body,
            })

    return result


# ---------------------------------------------------------------------------
# Crear una nueva oportunidad en Odoo
# ---------------------------------------------------------------------------
def create_crm_opportunity(
    url: str,
    db: str,
    uid: int,
    api_key: str,
    nombre: str,
    empresa: str,
    email: str,
    servicio: str,
) -> int:
    """
    Crea una nueva oportunidad en crm.lead y retorna su ID.

    Args:
        nombre:   Nombre del contacto
        empresa:  Nombre de la empresa
        email:    Correo electrónico del contacto
        servicio: Descripción del servicio / notas internas

    Returns:
        ID del nuevo registro creado.
    """
    try:
        models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
        new_id = models.execute_kw(
            db, uid, api_key,
            "crm.lead",
            "create",
            [{
                "name": f"{nombre} - {servicio}",
                "partner_name": empresa,
                "contact_name": nombre,
                "email_from": email,
                "description": servicio,
                "type": "opportunity",
            }],
        )
        return new_id
    except Exception as exc:
        raise RuntimeError(f"Error al crear la oportunidad en Odoo: {exc}") from exc


# ---------------------------------------------------------------------------
# Buscar duplicados antes de crear una oportunidad
# ---------------------------------------------------------------------------
def search_duplicate_leads(
    url: str,
    db: str,
    uid: int,
    api_key: str,
    email: str = "",
    empresa: str = "",
) -> list[dict]:
    """
    Busca oportunidades/leads ya existentes que coincidan con el email
    o el nombre de empresa proporcionados.

    Returns:
        Lista de dicts con id, name, partner_name, email_from, stage_id, write_date
        de los posibles duplicados. Lista vacía si no hay coincidencias.
    """
    if not email and not empresa:
        return []

    try:
        models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

        domain_conditions = []
        if email:
            domain_conditions.append(["email_from", "ilike", email])
        if empresa:
            domain_conditions.append(["partner_name", "ilike", empresa])

        # OR entre las condiciones si hay más de una
        if len(domain_conditions) == 1:
            domain = [domain_conditions[0]]
        else:
            domain = ["|"] + domain_conditions

        records = models.execute_kw(
            db, uid, api_key,
            "crm.lead",
            "search_read",
            [domain],
            {
                "fields": ["id", "name", "partner_name", "email_from", "stage_id", "write_date", "type"],
                "limit": 10,
                "order": "write_date desc",
                "context": {"active_test": False},
            },
        )
        return records
    except Exception:
        return []  # No interrumpir el flujo si la búsqueda falla


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
