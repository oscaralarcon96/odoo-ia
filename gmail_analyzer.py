"""
gmail_analyzer.py
-----------------
Analiza correos de Gmail usando OpenAI para detectar posibles oportunidades comerciales.
Procesa en lotes de 10 correos para evitar timeouts por exceso de tokens.
"""

import json
import re
from openai import OpenAI

OPPORTUNITY_PROMPT = """Eres un Analista Comercial Senior. Revisa estos correos y determina cuáles son posibles **oportunidades comerciales** (cotizaciones, consultas de servicios, propuestas de negocio, solicitudes comerciales, licitaciones, etc.).

Devuelve un JSON array con este formato EXACTO (sin texto adicional):
[
  {{
    "id": "ID_DEL_CORREO",
    "es_oportunidad": true,
    "nivel_interes": "alto",
    "razon": "Breve explicación (máx 60 palabras)",
    "nombre_contacto": "Nombre del remitente o null",
    "empresa_contacto": "Empresa o null",
    "email_contacto": "email@ejemplo.com"
  }}
]

Niveles: "alto" | "medio" | "bajo" | "ninguno"

Correos:
{emails_text}
"""


def _analyze_batch(client: OpenAI, batch: list[dict], model: str) -> list[dict]:
    """
    Analiza un lote de correos con OpenAI y retorna la lista de análisis.
    """
    emails_text_parts = []
    for i, email in enumerate(batch, 1):
        part = (
            f"[#{i}] ID:{email['id']}\n"
            f"De: {email['from']}\n"
            f"Asunto: {email['subject']}\n"
            f"Resumen: {email['snippet'][:400]}\n"
        )
        emails_text_parts.append(part)

    prompt = OPPORTUNITY_PROMPT.format(emails_text="\n---\n".join(emails_text_parts))

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=2000,
        timeout=30,  # 30 segundos max por lote
    )
    raw = response.choices[0].message.content.strip()

    # Extraer JSON (puede venir dentro de ```json ... ```)
    json_match = re.search(r"```json\s*(.*?)```", raw, re.DOTALL)
    if json_match:
        raw = json_match.group(1).strip()

    return json.loads(raw)


def analyze_emails_for_opportunities(
    client: OpenAI,
    emails: list[dict],
    model: str = "gpt-4o-mini",
    batch_size: int = 10,
) -> list[dict]:
    """
    Analiza una lista de correos en lotes y clasifica cuáles son posibles oportunidades.

    Args:
        client:     Cliente OpenAI autenticado
        emails:     Lista de dicts con keys: id, from, subject, date, snippet
        model:      Modelo de OpenAI a usar
        batch_size: Correos por lote (default 10 para evitar timeouts)

    Returns:
        Lista de dicts con análisis por correo.
    """
    if not emails:
        return []

    all_results: list[dict] = []

    # Procesar en lotes
    for start in range(0, len(emails), batch_size):
        batch = emails[start:start + batch_size]
        try:
            batch_analysis = _analyze_batch(client, batch, model)
            # Mapear resultados por ID
            analysis_map = {item["id"]: item for item in batch_analysis if isinstance(item, dict)}

            for email in batch:
                analysis_item = analysis_map.get(email["id"], {
                    "id": email["id"],
                    "es_oportunidad": False,
                    "nivel_interes": "ninguno",
                    "razon": "No clasificado",
                    "nombre_contacto": None,
                    "empresa_contacto": None,
                    "email_contacto": email.get("from", ""),
                })
                all_results.append({**email, **analysis_item})

        except (json.JSONDecodeError, Exception) as exc:
            # Si falla un lote, marcar esos correos como no analizados
            for email in batch:
                all_results.append({
                    **email,
                    "es_oportunidad": False,
                    "nivel_interes": "ninguno",
                    "razon": f"Error al analizar lote: {exc}",
                    "nombre_contacto": None,
                    "empresa_contacto": None,
                    "email_contacto": email.get("from", ""),
                })

    return all_results
