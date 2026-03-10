"""
ai_agent.py
-----------
Fase 4: Integración con OpenAI.

Construye el prompt de sistema con contexto de CRM y gestiona
la conversación multi-turno con el modelo.
"""

from openai import OpenAI


# ---------------------------------------------------------------------------
# Prompt del sistema — Persona: Analista de Ventas Senior
# ---------------------------------------------------------------------------
SYSTEM_PROMPT_TEMPLATE = """Eres un Analista de Ventas Senior altamente experimentado, especializado en CRM y gestión de pipeline de ventas. Tu nombre es **Aria**.

Tu misión es ayudar al equipo comercial a tomar decisiones basadas en datos reales de su instancia Odoo CRM.

**Tu comportamiento:**
- Responde SIEMPRE en español, de forma clara, precisa y orientada a acción.
- Analiza los datos con pensamiento crítico: detecta tendencias, riesgos y oportunidades.
- Cuando cites oportunidades o leads, menciona su nombre, etapa, probabilidad e ingreso esperado.
- Si la pregunta no puede responderse con los datos disponibles, dilo claramente.
- Usa formato Markdown en tus respuestas (listas, negritas, tablas si es necesario).
- Nunca inventes datos que no estén en el contexto proporcionado.

**Contexto actual del CRM (datos en tiempo real de Odoo):**

{crm_context}
"""


# ---------------------------------------------------------------------------
# Construcción del prompt con contexto
# ---------------------------------------------------------------------------
def build_system_prompt(crm_context: str) -> str:
    """
    Inyecta el contexto CRM en el template del prompt del sistema.

    Args:
        crm_context: Texto Markdown con la tabla de leads/oportunidades.

    Returns:
        System prompt completo listo para enviar a OpenAI.
    """
    return SYSTEM_PROMPT_TEMPLATE.format(crm_context=crm_context)


# ---------------------------------------------------------------------------
# Cliente OpenAI
# ---------------------------------------------------------------------------
def create_openai_client(api_key: str) -> OpenAI:
    """Crea y retorna un cliente OpenAI autenticado."""
    return OpenAI(api_key=api_key)


# ---------------------------------------------------------------------------
# Consulta al modelo
# ---------------------------------------------------------------------------
def query_ai(
    client: OpenAI,
    conversation_history: list[dict],
    crm_context: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.3,
) -> str:
    """
    Envía la conversación completa a OpenAI y retorna la respuesta del modelo.

    Args:
        client:               Cliente OpenAI autenticado.
        conversation_history: Lista de mensajes {role, content} (sin el system).
        crm_context:          Contexto CRM actual como texto Markdown.
        model:                Modelo a usar (default: gpt-4o-mini).
        temperature:          Creatividad del modelo (0 = determinístico).

    Returns:
        Respuesta del asistente como string.

    Raises:
        RuntimeError: Si la llamada a la API falla.
    """
    system_prompt = build_system_prompt(crm_context)

    messages = [{"role": "system", "content": system_prompt}] + conversation_history

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=1500,
        )
        return response.choices[0].message.content
    except Exception as exc:
        raise RuntimeError(f"Error al consultar la API de OpenAI: {exc}") from exc


# ---------------------------------------------------------------------------
# Preguntas de ejemplo para la UI
# ---------------------------------------------------------------------------
SAMPLE_QUESTIONS = [
    "¿Qué oportunidades tienen más del 80% de probabilidad de cierre?",
    "¿Cuál es el estado general de mi pipeline?",
    "¿Cuánto ingreso esperado tenemos en total?",
    "¿Qué leads no tienen fecha de cierre definida?",
    "Resúmeme las oportunidades más importantes de esta semana.",
    "¿Qué etapa concentra más oportunidades?",
    "¿Quién es el vendedor con mayor cartera potencial?",
]
