"""
app.py
------
Fase 3: Interfaz de Usuario con Streamlit.

Ejecutar con:
    streamlit run app.py
"""

import os
import streamlit as st
from dotenv import load_dotenv

from odoo_connector import authenticate, fetch_crm_leads, fetch_lead_messages
from data_processor import leads_to_dataframe, leads_to_text_context, get_summary_stats, attach_messages
from ai_agent import create_openai_client, query_ai, SAMPLE_QUESTIONS

# ---------------------------------------------------------------------------
# Configuración de página
# ---------------------------------------------------------------------------
load_dotenv()

st.set_page_config(
    page_title="Odoo CRM · Asistente IA",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS personalizado — estilo premium oscuro
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Fondo principal */
    .stApp {
        background: linear-gradient(135deg, #0f0f1a 0%, #111827 50%, #0f172a 100%);
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
        border-right: 1px solid rgba(99, 102, 241, 0.2);
    }

    /* Encabezado sidebar */
    .sidebar-header {
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.3);
    }
    .sidebar-header h2 {
        color: white;
        margin: 0;
        font-size: 1.1rem;
        font-weight: 600;
    }
    .sidebar-header p {
        color: rgba(255,255,255,0.75);
        margin: 4px 0 0;
        font-size: 0.75rem;
    }

    /* KPI cards */
    .kpi-card {
        background: linear-gradient(135deg, rgba(99,102,241,0.15), rgba(139,92,246,0.1));
        border: 1px solid rgba(99,102,241,0.3);
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(99, 102, 241, 0.25);
    }
    .kpi-value {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #a5b4fc, #c4b5fd);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .kpi-label {
        color: rgba(148, 163, 184, 0.9);
        font-size: 0.8rem;
        margin-top: 4px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Chat container */
    .chat-container {
        background: rgba(17, 24, 39, 0.8);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 20px;
        padding: 8px 4px;
        backdrop-filter: blur(10px);
    }

    /* Mensajes */
    [data-testid="stChatMessage"] {
        border-radius: 12px;
        margin: 4px 0;
    }

    /* Botón primario */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3) !important;
    }
    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5) !important;
    }

    /* Status badge */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .status-ok {
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid rgba(16, 185, 129, 0.4);
        color: #6ee7b7;
    }
    .status-err {
        background: rgba(239, 68, 68, 0.15);
        border: 1px solid rgba(239, 68, 68, 0.35);
        color: #fca5a5;
    }

    /* Section divider */
    .section-title {
        color: #a5b4fc;
        font-size: 1rem;
        font-weight: 600;
        letter-spacing: 0.03em;
        padding: 0 0 8px;
        border-bottom: 1px solid rgba(99,102,241,0.25);
        margin-bottom: 12px;
    }

    /* Chip preguntas ejemplo */
    .example-chip {
        background: rgba(99,102,241,0.12);
        border: 1px solid rgba(99,102,241,0.3);
        border-radius: 20px;
        padding: 4px 12px;
        font-size: 0.75rem;
        color: #c4b5fd;
        display: inline-block;
        margin: 3px;
        cursor: pointer;
    }

    hr { border-color: rgba(99,102,241,0.2) !important; }

    /* Inputs */
    [data-testid="stTextInput"] input,
    [data-testid="stTextInput"] input:focus {
        background: rgba(30, 30, 50, 0.8) !important;
        border: 1px solid rgba(99,102,241,0.3) !important;
        color: #e2e8f0 !important;
        border-radius: 8px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Estado de sesión
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "leads_df" not in st.session_state:
    st.session_state.leads_df = None
if "crm_context" not in st.session_state:
    st.session_state.crm_context = ""
if "connected" not in st.session_state:
    st.session_state.connected = False
if "stats" not in st.session_state:
    st.session_state.stats = {}
if "openai_client" not in st.session_state:
    st.session_state.openai_client = None
if "show_cred_fields" not in st.session_state:
    st.session_state.show_cred_fields = False

# ---------------------------------------------------------------------------
# Detectar credenciales desde .env
# ---------------------------------------------------------------------------
_env_odoo_url      = os.getenv("ODOO_URL", "")
_env_odoo_db       = os.getenv("ODOO_DB", "")
_env_odoo_username = os.getenv("ODOO_USERNAME", "")
_env_odoo_api_key  = os.getenv("ODOO_API_KEY", "")
_env_openai_key    = os.getenv("OPENAI_API_KEY", "")

env_has_creds = all([
    _env_odoo_url, _env_odoo_db,
    _env_odoo_username, _env_odoo_api_key,
    _env_openai_key,
])

# ---------------------------------------------------------------------------
# ─── SIDEBAR ────────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-header">
            <h2>🤖 Odoo CRM · Asistente IA</h2>
            <p>Analista de Ventas Inteligente</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- Si .env tiene todas las credenciales, ocultamos los campos ---
    if env_has_creds and not st.session_state.show_cred_fields:
        st.markdown(
            """
            <div style="
                background: rgba(16,185,129,0.12);
                border: 1px solid rgba(16,185,129,0.35);
                border-radius: 12px;
                padding: 12px 16px;
                margin-bottom: 12px;
            ">
                <div style="color:#6ee7b7; font-weight:600; font-size:0.85rem;">🔒 Credenciales cargadas desde .env</div>
                <div style="color:rgba(148,163,184,0.7); font-size:0.75rem; margin-top:4px;">URL, DB, usuario y claves configuradas.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        # Usar los valores del .env directamente
        odoo_url      = _env_odoo_url
        odoo_db       = _env_odoo_db
        odoo_username = _env_odoo_username
        odoo_api_key  = _env_odoo_api_key
        openai_api_key = _env_openai_key

        if st.button("✏️ Cambiar credenciales", use_container_width=True):
            st.session_state.show_cred_fields = True
            st.rerun()
    else:
        # Mostrar campos manuales
        st.markdown("### 🔗 Credenciales Odoo")
        odoo_url = st.text_input(
            "URL de Odoo",
            value=_env_odoo_url,
            placeholder="https://mycompany.odoo.com",
            help="URL completa de tu instancia Odoo Cloud",
        )
        odoo_db = st.text_input(
            "Base de datos (DB)",
            value=_env_odoo_db,
            placeholder="mi-empresa",
        )
        odoo_username = st.text_input(
            "Usuario (email)",
            value=_env_odoo_username,
            placeholder="usuario@empresa.com",
        )
        odoo_api_key = st.text_input(
            "API Key de Odoo",
            value=_env_odoo_api_key,
            type="password",
            help="Generada en Odoo: Configuración → Claves de API",
        )
        st.markdown("---")
        st.markdown("### 🔑 Credenciales OpenAI")
        openai_api_key = st.text_input(
            "OpenAI API Key",
            value=_env_openai_key,
            type="password",
        )
        if env_has_creds and st.button("↩️ Usar credenciales del .env", use_container_width=True):
            st.session_state.show_cred_fields = False
            st.rerun()

    st.markdown("---")
    st.markdown("### ⚙️ Opciones de carga")
    max_records = st.slider("Máximo de registros", 50, 1000, 500, step=50)

    st.markdown("---")
    connect_btn = st.button("🔄 Conectar y cargar datos", use_container_width=True)

    # Estado de conexión
    if st.session_state.connected:
        df = st.session_state.leads_df
        total = len(df) if df is not None else 0
        st.markdown(
            f'<div class="status-badge status-ok">✅ Conectado · {total} registros</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="status-badge status-err">⚪ No conectado</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.caption("💡 **Tip:** Puedes crear un archivo `.env` con tus credenciales para no ingresarlas manualmente. Revisa `.env.example`.")

# ---------------------------------------------------------------------------
# Auto-conexión desde .env al iniciar
# ---------------------------------------------------------------------------
if env_has_creds and not st.session_state.connected:
    with st.spinner("🔌 Conectando automáticamente desde .env..."):
        try:
            uid = authenticate(_env_odoo_url, _env_odoo_db, _env_odoo_username, _env_odoo_api_key)
            leads = fetch_crm_leads(_env_odoo_url, _env_odoo_db, uid, _env_odoo_api_key, limit=500)
            df = leads_to_dataframe(leads)
            lead_ids = df["id"].tolist()
            messages_by_id = fetch_lead_messages(_env_odoo_url, _env_odoo_db, uid, _env_odoo_api_key, lead_ids=lead_ids, messages_per_lead=2)
            df = attach_messages(df, messages_by_id)
            context = leads_to_text_context(df)
            stats = get_summary_stats(df)
            st.session_state.leads_df = df
            st.session_state.crm_context = context
            st.session_state.stats = stats
            st.session_state.connected = True
            st.session_state.openai_client = create_openai_client(_env_openai_key)
            st.session_state.messages = []
            st.rerun()
        except Exception:
            pass  # Si falla silenciosamente, el usuario puede conectar manualmente

# ---------------------------------------------------------------------------
# Acción: Conectar y cargar datos (botón manual)
# ---------------------------------------------------------------------------
if connect_btn:
    if not all([odoo_url, odoo_db, odoo_username, odoo_api_key]):
        st.error("⚠️ Completa todos los campos de Odoo en la barra lateral.")
    elif not openai_api_key:
        st.error("⚠️ Ingresa tu OpenAI API Key en la barra lateral.")
    else:
        with st.spinner("🔌 Conectando con Odoo y cargando datos..."):
            try:
                uid = authenticate(odoo_url, odoo_db, odoo_username, odoo_api_key)
                leads = fetch_crm_leads(
                    odoo_url, odoo_db, uid, odoo_api_key,
                    limit=max_records,
                )
                df = leads_to_dataframe(leads)

                # Obtener las últimas 2 conversaciones por oportunidad (batch)
                lead_ids = df["id"].tolist()
                messages_by_id = fetch_lead_messages(
                    odoo_url, odoo_db, uid, odoo_api_key,
                    lead_ids=lead_ids,
                    messages_per_lead=2,
                )
                df = attach_messages(df, messages_by_id)

                context = leads_to_text_context(df)
                stats = get_summary_stats(df)

                st.session_state.leads_df = df
                st.session_state.crm_context = context
                st.session_state.stats = stats
                st.session_state.connected = True
                st.session_state.openai_client = create_openai_client(openai_api_key)
                st.session_state.messages = []  # Limpiar conversación al recargar
                st.success(f"✅ Conexión exitosa. {len(df)} oportunidades cargadas.")
                st.rerun()
            except PermissionError as e:
                st.error(f"🔐 Error de autenticación: {e}")
                st.session_state.connected = False
            except ConnectionError as e:
                st.error(f"🌐 Error de conexión: {e}")
                st.session_state.connected = False
            except Exception as e:
                st.error(f"❌ Error inesperado: {e}")
                st.session_state.connected = False

# ---------------------------------------------------------------------------
# ─── MAIN PANEL ─────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------
st.markdown(
    """
    <h1 style="
        background: linear-gradient(135deg, #a5b4fc, #c4b5fd, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 4px;
    ">🤖 Asistente de Ventas IA</h1>
    <p style="color: rgba(148,163,184,0.8); margin-top: 0; font-size: 0.95rem;">
        Conectado a tu pipeline de Odoo CRM · Powered by OpenAI
    </p>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# KPI Metrics
# ---------------------------------------------------------------------------
if st.session_state.connected and st.session_state.stats:
    import pandas as pd
    from datetime import datetime, timedelta
    stats = st.session_state.stats
    _df = st.session_state.leads_df

    # Calcular esta semana
    hoy = pd.Timestamp.now()
    semana_atras = hoy - pd.Timedelta(days=7)
    esta_semana = int((_df["fecha_actualizacion"] >= semana_atras).sum()) if _df is not None and "fecha_actualizacion" in _df.columns else 0
    sin_conv = int((_df["ultimas_conversaciones"] == "Sin conversaciones registradas").sum()) if _df is not None and "ultimas_conversaciones" in _df.columns else 0

    c1, c2, c3, c4 = st.columns(4)

    def kpi(col, value, label):
        col.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-value">{value}</div>
                <div class="kpi-label">{label}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    kpi(c1, stats["total_oportunidades"], "Total Oportunidades")
    ganadas = len(_df[_df["etapa"] == "Ganado"]) if _df is not None else 0
    kpi(c2, ganadas, "Ganadas")
    kpi(c3, esta_semana, "Actualizadas esta semana")
    kpi(c4, sin_conv, "Sin conversaciones")

    st.markdown("<br>", unsafe_allow_html=True)

    # Data Preview (colapsable)
    with st.expander("📊 Vista previa del pipeline", expanded=False):
        df = st.session_state.leads_df
        col_filter, col_type = st.columns([3, 1])
        with col_filter:
            search = st.text_input("🔍 Buscar", placeholder="Nombre, cliente, etapa...")
        with col_type:
            tipo_filter = st.selectbox("Tipo", ["Todos", "Oportunidad", "Lead"])

        display_df = df.copy()
        if search:
            mask = (
                display_df["nombre"].str.contains(search, case=False, na=False)
                | display_df["cliente"].str.contains(search, case=False, na=False)
                | display_df["etapa"].str.contains(search, case=False, na=False)
            )
            display_df = display_df[mask]
        if tipo_filter != "Todos":
            display_df = display_df[display_df["tipo"] == tipo_filter]

        cols_show = [
            "nombre", "cliente", "etapa", "vendedor",
            "fecha_creacion", "fecha_actualizacion", "fecha_cierre",
            "ultimas_conversaciones",
        ]
        # solo mostrar columnas que existan
        cols_show = [c for c in cols_show if c in display_df.columns]
        st.dataframe(
            display_df[cols_show].rename(columns={
                "nombre": "Nombre",
                "cliente": "Cliente",
                "etapa": "Etapa",
                "vendedor": "Vendedor",
                "fecha_creacion": "Creación",
                "fecha_actualizacion": "Última Act.",
                "fecha_cierre": "Fecha Cierre",
                "ultimas_conversaciones": "Últimas Conversaciones",
            }),
            use_container_width=True,
            height=320,
        )

    st.markdown("---")

# ---------------------------------------------------------------------------
# Chat Interface
# ---------------------------------------------------------------------------
if not st.session_state.connected:
    st.markdown(
        """
        <div style="
            text-align: center;
            padding: 60px 20px;
            background: rgba(99,102,241,0.04);
            border: 1px dashed rgba(99,102,241,0.3);
            border-radius: 20px;
            margin: 20px 0;
        ">
            <div style="font-size: 3rem; margin-bottom: 16px;">🔌</div>
            <h3 style="color: #a5b4fc; margin: 0 0 8px;">Conecta tu instancia de Odoo</h3>
            <p style="color: rgba(148,163,184,0.7); max-width: 400px; margin: 0 auto;">
                Ingresa tus credenciales en la barra lateral y haz clic en
                <strong style="color: #a5b4fc;">Conectar y cargar datos</strong>
                para comenzar a chatear con tu pipeline.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    # Preguntas de ejemplo
    st.markdown('<div class="section-title">💬 Chatea con tu pipeline</div>', unsafe_allow_html=True)

    with st.expander("💡 Preguntas de ejemplo — haz clic para usar"):
        for q in SAMPLE_QUESTIONS:
            if st.button(q, key=f"sample_{hash(q)}", use_container_width=False):
                st.session_state.messages.append({"role": "user", "content": q})
                with st.spinner("Aria está analizando..."):
                    try:
                        reply = query_ai(
                            st.session_state.openai_client,
                            st.session_state.messages[:-0] if False else st.session_state.messages,
                            st.session_state.crm_context,
                        )
                        st.session_state.messages.append({"role": "assistant", "content": reply})
                    except RuntimeError as e:
                        st.session_state.messages.append(
                            {"role": "assistant", "content": f"❌ Error: {e}"}
                        )
                st.rerun()

    # Historial de mensajes
    chat_container = st.container()
    with chat_container:
        if not st.session_state.messages:
            st.markdown(
                """
                <div style="text-align:center; padding: 40px 0; color: rgba(148,163,184,0.5);">
                    <div style="font-size: 2rem;">👋</div>
                    <p>Hola, soy <strong style="color:#a5b4fc">Aria</strong>, tu Analista de Ventas IA.<br>
                    Pregúntame cualquier cosa sobre tu pipeline de Odoo.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        for msg in st.session_state.messages:
            with st.chat_message(
                msg["role"],
                avatar="🧑‍💼" if msg["role"] == "user" else "🤖",
            ):
                st.markdown(msg["content"])

    # Input del chat
    if prompt := st.chat_input("Pregunta sobre tu pipeline... (ej: '¿Qué oportunidades están próximas a cerrar?')"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="🧑‍💼"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Aria está analizando tu pipeline..."):
                try:
                    reply = query_ai(
                        st.session_state.openai_client,
                        st.session_state.messages,
                        st.session_state.crm_context,
                    )
                    st.markdown(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                except RuntimeError as e:
                    err_msg = f"❌ Error al consultar la IA: {e}"
                    st.error(err_msg)
                    st.session_state.messages.append({"role": "assistant", "content": err_msg})

    # Botón para limpiar chat
    if st.session_state.messages:
        if st.button("🗑️ Limpiar conversación", key="clear_chat"):
            st.session_state.messages = []
            st.rerun()

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown(
    """
    <br><hr>
    <p style="text-align:center; color: rgba(148,163,184,0.4); font-size: 0.75rem;">
        Odoo CRM AI Assistant · Datos en tiempo real desde Odoo Cloud · Powered by OpenAI gpt-4o-mini
    </p>
    """,
    unsafe_allow_html=True,
)
