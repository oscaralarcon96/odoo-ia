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

**Tu comportamiento general:**
- Responde SIEMPRE en español, de forma clara, precisa y orientada a acción.
- Analiza los datos con pensamiento crítico: detecta tendencias, riesgos y oportunidades.
- Cuando cites oportunidades, menciona su nombre, etapa y fecha de actualización.
- Si la pregunta no puede responderse con los datos disponibles, dilo claramente.
- Usa formato Markdown en tus respuestas (listas, negritas, tablas si es necesario).
- Nunca inventes datos que no estén en el contexto proporcionado.

---

**🆕 Creación de oportunidades:**

Si el usuario dice que quiere crear una oportunidad (o algo similar), debes recopilar estos 4 datos de forma conversacional, uno a la vez si no los proporcionan todos juntos:
1. **Nombre del contacto**
2. **Empresa**
3. **Correo electrónico**
4. **Servicio o producto de interés**

Cuando tengas los 4 datos confirmados por el usuario, muéstrale un resumen claro y luego en una línea completamente separada escribe EXACTAMENTE este bloque JSON (sin modificar el formato):

```json
{{"ACTION":"CREATE_OPPORTUNITY","nombre":"VALOR","empresa":"VALOR","email":"VALOR","servicio":"VALOR"}}
```

Reemplaza cada VALOR con los datos recopilados. El sistema detectará este bloque automáticamente para crear la oportunidad en Odoo.

---

**Contexto actual del CRM (datos en tiempo real de Odoo):**

{crm_context}
"""


# ---------------------------------------------------------------------------
# Construcción del prompt con contexto
# ---------------------------------------------------------------------------
def build_system_prompt(crm_context: str) -> str:
    """
    Inyecta el contexto CRM en el template del prompt del sistema.
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
# Parser: detecta el JSON de acción en la respuesta de la IA
# ---------------------------------------------------------------------------
def parse_action(response: str) -> dict | None:
    """
    Busca un bloque JSON con ACTION:CREATE_OPPORTUNITY en la respuesta del modelo.

    Returns:
        Dict con los campos si se encontró la acción, None en caso contrario.
    """
    import re, json
    # Busca el JSON dentro de un bloque ```json ... ``` o en línea
    patterns = [
        r'```json\s*(\{.*?"ACTION"\s*:\s*"CREATE_OPPORTUNITY".*?\})\s*```',
        r'(\{[^{}]*?"ACTION"\s*:\s*"CREATE_OPPORTUNITY"[^{}]*?\})',
    ]
    for pattern in patterns:
        match = re.search(pattern, response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
    return None


# ---------------------------------------------------------------------------
# Preguntas de ejemplo para la UI
# ---------------------------------------------------------------------------
SAMPLE_QUESTIONS = [
    "Quiero crear una nueva oportunidad",
    "¿Cuál es el estado general de mi pipeline?",
    "¿Qué oportunidades se actualizaron esta semana?",
    "¿Qué etapa concentra más oportunidades?",
    "Resúmeme las oportunidades más importantes.",
    "¿Quién es el vendedor con mayor cartera?",
    "¿Qué oportunidades no tienen fecha de cierre definida?",
]
