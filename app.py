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

from odoo_connector import (
    authenticate, fetch_crm_leads, fetch_lead_messages,
    create_crm_opportunity, search_duplicate_leads,
)
from data_processor import leads_to_dataframe, leads_to_text_context, get_summary_stats, attach_messages
from ai_agent import create_openai_client, query_ai, SAMPLE_QUESTIONS, parse_action
from chat_history import load_history, save_history, clear_history, get_history_stats
from gmail_connector import (
    get_gmail_service, fetch_recent_emails,
    credentials_exist, token_exists, revoke_token,
)
from gmail_analyzer import analyze_emails_for_opportunities

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

    /* Oportunidad badge */
    .opp-badge-yes {
        background: rgba(16,185,129,0.15);
        border: 1px solid rgba(16,185,129,0.4);
        color: #6ee7b7;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.78rem;
        font-weight: 600;
    }
    .opp-badge-no {
        background: rgba(100,116,139,0.15);
        border: 1px solid rgba(100,116,139,0.3);
        color: #94a3b8;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.78rem;
    }
    .opp-badge-high {
        background: rgba(234,179,8,0.15);
        border: 1px solid rgba(234,179,8,0.4);
        color: #fde68a;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
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
    st.session_state.messages = load_history()  # ← cargar historial persistente
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
# Estado para flujo de creación con detección de duplicados
if "pending_create" not in st.session_state:
    st.session_state.pending_create = None  # dict con datos de la oportunidad pendiente
# Estado para Gmail
if "gmail_emails" not in st.session_state:
    st.session_state.gmail_emails = []
if "gmail_analyzed" not in st.session_state:
    st.session_state.gmail_analyzed = []
if "gmail_analyzing" not in st.session_state:
    st.session_state.gmail_analyzing = False

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
        odoo_url      = _env_odoo_url
        odoo_db       = _env_odoo_db
        odoo_username = _env_odoo_username
        odoo_api_key  = _env_odoo_api_key
        openai_api_key = _env_openai_key

        if st.button("✏️ Cambiar credenciales", use_container_width=True):
            st.session_state.show_cred_fields = True
            st.rerun()
    else:
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

    # Historial info
    st.markdown("---")
    hist_stats = get_history_stats()
    if hist_stats["exists"] and hist_stats["count"] > 0:
        st.caption(f"💬 Historial: {hist_stats['count']} mensajes guardados ({hist_stats['size_kb']} KB)")
    st.caption("💡 **Tip:** Puedes crear un archivo `.env` con tus credenciales para no ingresarlas manualmente.")

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
            # NO limpiamos el historial — ya fue cargado desde disco al iniciar
            st.rerun()
        except Exception:
            pass

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
                leads = fetch_crm_leads(odoo_url, odoo_db, uid, odoo_api_key, limit=max_records)
                df = leads_to_dataframe(leads)
                lead_ids = df["id"].tolist()
                messages_by_id = fetch_lead_messages(
                    odoo_url, odoo_db, uid, odoo_api_key,
                    lead_ids=lead_ids, messages_per_lead=2,
                )
                df = attach_messages(df, messages_by_id)
                context = leads_to_text_context(df)
                stats = get_summary_stats(df)

                st.session_state.leads_df = df
                st.session_state.crm_context = context
                st.session_state.stats = stats
                st.session_state.connected = True
                st.session_state.openai_client = create_openai_client(openai_api_key)
                # NO limpiamos el historial al reconectar
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
    stats = st.session_state.stats
    _df = st.session_state.leads_df

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
# ─── TABS: CHAT y GMAIL ─────────────────────────────────────────────────────
# ---------------------------------------------------------------------------
tab_chat, tab_gmail = st.tabs(["💬 Chat con Aria", "📧 Gmail — Oportunidades"])

# ===========================================================================
# TAB 1: CHAT
# ===========================================================================
with tab_chat:
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
        st.markdown('<div class="section-title">💬 Chatea con tu pipeline</div>', unsafe_allow_html=True)

        # -----------------------------------------------------------------------
        # Preguntas de ejemplo
        # -----------------------------------------------------------------------
        with st.expander("💡 Preguntas de ejemplo — haz clic para usar"):
            for q in SAMPLE_QUESTIONS:
                if st.button(q, key=f"sample_{hash(q)}", use_container_width=False):
                    st.session_state.messages.append({"role": "user", "content": q})
                    with st.spinner("Aria está analizando..."):
                        try:
                            reply = query_ai(
                                st.session_state.openai_client,
                                st.session_state.messages,
                                st.session_state.crm_context,
                            )
                            st.session_state.messages.append({"role": "assistant", "content": reply})
                            save_history(st.session_state.messages)
                            action = parse_action(reply)
                            if action and action.get("ACTION") == "CREATE_OPPORTUNITY":
                                st.session_state.pending_create = action
                        except RuntimeError as e:
                            st.session_state.messages.append(
                                {"role": "assistant", "content": f"❌ Error: {e}"}
                            )
                            save_history(st.session_state.messages)
                    st.rerun()

        # -----------------------------------------------------------------------
        # Detección de duplicados — flujo de confirmación
        # -----------------------------------------------------------------------
        if st.session_state.pending_create:
            action = st.session_state.pending_create
            email_val = action.get("email", "")
            empresa_val = action.get("empresa", "")

            with st.spinner("🔍 Buscando posibles duplicados en Odoo..."):
                try:
                    uid_check = authenticate(odoo_url, odoo_db, odoo_username, odoo_api_key)
                    duplicates = search_duplicate_leads(
                        odoo_url, odoo_db, uid_check, odoo_api_key,
                        email=email_val, empresa=empresa_val,
                    )
                except Exception:
                    duplicates = []

            if duplicates:
                st.warning(
                    f"⚠️ Se encontraron **{len(duplicates)} registro(s)** en Odoo con datos similares "
                    f"(email: `{email_val}` o empresa: `{empresa_val}`)."
                )
                with st.expander("👁️ Ver registros existentes", expanded=True):
                    for dup in duplicates:
                        stage_name = dup.get("stage_id", [None, "Sin etapa"])
                        stage_label = stage_name[1] if isinstance(stage_name, (list, tuple)) and len(stage_name) > 1 else "Sin etapa"
                        tipo_label = "🎯 Oportunidad" if dup.get("type") == "opportunity" else "📋 Lead"
                        st.markdown(
                            f"""
                            <div style="
                                background: rgba(99,102,241,0.08);
                                border: 1px solid rgba(99,102,241,0.25);
                                border-radius: 10px;
                                padding: 12px 16px;
                                margin-bottom: 8px;
                            ">
                                <strong style="color:#a5b4fc;">{dup.get('name', 'Sin nombre')}</strong>
                                &nbsp;·&nbsp; {tipo_label}
                                &nbsp;·&nbsp; <span style="color:#94a3b8;">Etapa: {stage_label}</span><br>
                                <span style="font-size:0.82rem; color:#64748b;">
                                    📧 {dup.get('email_from','—')} &nbsp;·&nbsp;
                                    🏢 {dup.get('partner_name','—')} &nbsp;·&nbsp;
                                    🕒 {str(dup.get('write_date',''))[:10]}
                                </span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                st.markdown("**¿Deseas crear la oportunidad de todas formas?**")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("✅ Sí, crear de todas formas", key="confirm_create", use_container_width=True):
                        _do_create = True
                    else:
                        _do_create = False
                with col_no:
                    if st.button("❌ Cancelar", key="cancel_create", use_container_width=True):
                        st.session_state.pending_create = None
                        cancel_msg = "❌ Creación cancelada. No se creó ninguna oportunidad nueva."
                        st.session_state.messages.append({"role": "assistant", "content": cancel_msg})
                        save_history(st.session_state.messages)
                        st.rerun()
                    else:
                        _do_create = _do_create  # sin cambio

                if _do_create:
                    try:
                        uid_new = authenticate(odoo_url, odoo_db, odoo_username, odoo_api_key)
                        new_id = create_crm_opportunity(
                            odoo_url, odoo_db, uid_new, odoo_api_key,
                            nombre=action["nombre"],
                            empresa=action["empresa"],
                            email=action["email"],
                            servicio=action["servicio"],
                        )
                        ok_msg = f"✅ **Oportunidad creada exitosamente en Odoo** (ID: `{new_id}`).\nRecarga los datos con el botón \"Conectar y cargar datos\" para verla en la tabla."
                        st.success(ok_msg)
                        st.session_state.messages.append({"role": "assistant", "content": ok_msg})
                        save_history(st.session_state.messages)
                    except Exception as ce:
                        err = f"❌ No se pudo crear la oportunidad en Odoo: {ce}"
                        st.error(err)
                        st.session_state.messages.append({"role": "assistant", "content": err})
                        save_history(st.session_state.messages)
                    finally:
                        st.session_state.pending_create = None
                        st.rerun()

            else:
                # Sin duplicados: crear directamente
                try:
                    uid_new = authenticate(odoo_url, odoo_db, odoo_username, odoo_api_key)
                    new_id = create_crm_opportunity(
                        odoo_url, odoo_db, uid_new, odoo_api_key,
                        nombre=action["nombre"],
                        empresa=action["empresa"],
                        email=action["email"],
                        servicio=action["servicio"],
                    )
                    ok_msg = f"✅ **Oportunidad creada exitosamente en Odoo** (ID: `{new_id}`).\nRecarga los datos con el botón \"Conectar y cargar datos\" para verla en la tabla."
                    st.success(ok_msg)
                    st.session_state.messages.append({"role": "assistant", "content": ok_msg})
                    save_history(st.session_state.messages)
                except Exception as ce:
                    err = f"❌ No se pudo crear la oportunidad en Odoo: {ce}"
                    st.error(err)
                    st.session_state.messages.append({"role": "assistant", "content": err})
                    save_history(st.session_state.messages)
                finally:
                    st.session_state.pending_create = None
                    st.rerun()

        # -----------------------------------------------------------------------
        # Historial de mensajes
        # -----------------------------------------------------------------------
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

        # -----------------------------------------------------------------------
        # Input del chat
        # -----------------------------------------------------------------------
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
                        save_history(st.session_state.messages)  # ← guardar en disco

                        # Detectar acción de creación
                        action = parse_action(reply)
                        if action and action.get("ACTION") == "CREATE_OPPORTUNITY":
                            st.session_state.pending_create = action
                            st.rerun()  # disparar flujo de duplicados

                    except RuntimeError as e:
                        err_msg = f"❌ Error al consultar la IA: {e}"
                        st.error(err_msg)
                        st.session_state.messages.append({"role": "assistant", "content": err_msg})
                        save_history(st.session_state.messages)

        # -----------------------------------------------------------------------
        # Botones de historial
        # -----------------------------------------------------------------------
        if st.session_state.messages:
            col_clear, col_export = st.columns(2)
            with col_clear:
                if st.button("🗑️ Limpiar conversación", key="clear_chat"):
                    st.session_state.messages = []
                    clear_history()
                    st.rerun()
            with col_export:
                import json as _json
                hist_json = _json.dumps(st.session_state.messages, ensure_ascii=False, indent=2)
                st.download_button(
                    label="📂 Exportar historial",
                    data=hist_json,
                    file_name="historial_aria.json",
                    mime="application/json",
                    key="export_chat",
                )

# ===========================================================================
# TAB 2: GMAIL
# ===========================================================================
with tab_gmail:
    st.markdown('<div class="section-title">📧 Análisis de Correos — Detección de Oportunidades</div>', unsafe_allow_html=True)

    if not credentials_exist():
        st.markdown(
            """
            <div style="
                background: rgba(234,179,8,0.08);
                border: 1px solid rgba(234,179,8,0.35);
                border-radius: 14px;
                padding: 20px 24px;
                margin-bottom: 16px;
            ">
                <div style="color:#fde68a; font-weight:700; font-size:1rem; margin-bottom:8px;">
                    🔧 Configuración requerida — Google Cloud Console
                </div>
                <ol style="color:rgba(148,163,184,0.9); font-size:0.88rem; line-height:1.8; margin:0; padding-left:18px;">
                    <li>Ve a <strong>console.cloud.google.com</strong> y crea un proyecto nuevo.</li>
                    <li>En <strong>APIs &amp; Services → Library</strong>, busca y habilita <strong>Gmail API</strong>.</li>
                    <li>En <strong>APIs &amp; Services → Credentials</strong>, crea credenciales tipo <strong>OAuth 2.0 → Desktop App</strong>.</li>
                    <li>Descarga el archivo JSON y renómbralo a <strong><code>credentials.json</code></strong>.</li>
                    <li>Coloca <code>credentials.json</code> en la carpeta del proyecto: <code>odoo-ia/</code></li>
                    <li>Recarga esta página — la primera vez se abrirá el navegador para autorizar.</li>
                </ol>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        # Credenciales existen
        gmail_creds_ok = True

        col_gmail1, col_gmail2 = st.columns([2, 1])
        with col_gmail1:
            days_back = st.slider("📅 Correos de los últimos N días", 1, 14, 7)
            max_emails = st.slider("📬 Máximo de correos a analizar", 10, 100, 30, step=10)
        with col_gmail2:
            st.markdown("<br>", unsafe_allow_html=True)
            if token_exists():
                st.markdown(
                    '<div class="status-badge status-ok">✅ Gmail autorizado</div>',
                    unsafe_allow_html=True,
                )
                if st.button("🔓 Desconectar Gmail", use_container_width=True, key="revoke_gmail"):
                    revoke_token()
                    st.session_state.gmail_emails = []
                    st.session_state.gmail_analyzed = []
                    st.rerun()
            else:
                st.markdown(
                    '<div class="status-badge status-err">⚪ Gmail no autorizado</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("")

        if not st.session_state.connected:
            st.info("ℹ️ Conecta primero tu instancia de Odoo para poder crear oportunidades desde correos.")

        analyze_btn = st.button("🔍 Analizar correos de la última semana", use_container_width=True, key="gmail_analyze_btn")

        if analyze_btn:
            if not st.session_state.openai_client and not _env_openai_key:
                st.error("⚠️ Se necesita la API Key de OpenAI para analizar los correos. Conecta Odoo primero o ingresa la clave.")
            else:
                openai_client_for_gmail = st.session_state.openai_client or create_openai_client(_env_openai_key)
                with st.spinner(f"📬 Obteniendo correos de los últimos {days_back} días desde Gmail..."):
                    try:
                        service = get_gmail_service()
                        emails = fetch_recent_emails(service, days=days_back, max_results=max_emails)
                        st.session_state.gmail_emails = emails
                    except FileNotFoundError as e:
                        st.error(str(e))
                        emails = []
                    except Exception as e:
                        st.error(f"❌ Error al conectar con Gmail: {e}")
                        emails = []

                if emails:
                    n_batches = (len(emails) + 9) // 10
                    with st.spinner(f"🤖 Aria está analizando {len(emails)} correos en {n_batches} lote(s)... (puede tomar ~{n_batches * 8}s)"):
                        try:
                            analyzed = analyze_emails_for_opportunities(openai_client_for_gmail, emails)
                            st.session_state.gmail_analyzed = analyzed
                        except Exception as e:
                            st.error(f"❌ Error al analizar correos: {e}")
                elif emails == []:
                    st.info(f"📭 No se encontraron correos en los últimos {days_back} días.")

        # -----------------------------------------------------------------------
        # Mostrar resultados del análisis
        # -----------------------------------------------------------------------
        if st.session_state.gmail_analyzed:
            analyzed = st.session_state.gmail_analyzed
            oportunidades = [e for e in analyzed if e.get("es_oportunidad")]
            otros = [e for e in analyzed if not e.get("es_oportunidad")]

            st.markdown(f"""
            <div style="display:flex; gap:12px; margin: 12px 0 20px;">
                <div style="
                    background: rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.35);
                    border-radius:10px; padding:10px 20px; text-align:center;
                ">
                    <div style="font-size:1.6rem; font-weight:700; color:#6ee7b7;">{len(oportunidades)}</div>
                    <div style="font-size:0.75rem; color:rgba(148,163,184,0.7);">🎯 Oportunidades</div>
                </div>
                <div style="
                    background: rgba(100,116,139,0.1); border:1px solid rgba(100,116,139,0.25);
                    border-radius:10px; padding:10px 20px; text-align:center;
                ">
                    <div style="font-size:1.6rem; font-weight:700; color:#94a3b8;">{len(otros)}</div>
                    <div style="font-size:0.75rem; color:rgba(148,163,184,0.7);">📭 No relevantes</div>
                </div>
                <div style="
                    background: rgba(99,102,241,0.1); border:1px solid rgba(99,102,241,0.25);
                    border-radius:10px; padding:10px 20px; text-align:center;
                ">
                    <div style="font-size:1.6rem; font-weight:700; color:#a5b4fc;">{len(analyzed)}</div>
                    <div style="font-size:0.75rem; color:rgba(148,163,184,0.7);">📬 Total analizados</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Oportunidades primero
            if oportunidades:
                st.markdown("### 🎯 Posibles Oportunidades Comerciales")
                for i, email_item in enumerate(oportunidades):
                    nivel = email_item.get("nivel_interes", "bajo")
                    nivel_color = {"alto": "#fde68a", "medio": "#a5b4fc", "bajo": "#94a3b8"}.get(nivel, "#94a3b8")
                    with st.expander(
                        f"📧 {email_item.get('subject', '(Sin asunto)')} — De: {email_item.get('from', '?')}",
                        expanded=(i == 0),
                    ):
                        col_info, col_action = st.columns([3, 1])
                        with col_info:
                            st.markdown(
                                f"""
                                <div style="font-size:0.85rem; color:rgba(148,163,184,0.8); margin-bottom:8px;">
                                    📅 {email_item.get('date','')} &nbsp;|&nbsp;
                                    <span style="color:{nivel_color}; font-weight:600;">
                                        Interés: {nivel.upper()}
                                    </span>
                                </div>
                                <div style="
                                    background:rgba(16,185,129,0.08);
                                    border-left: 3px solid #10b981;
                                    padding: 8px 12px;
                                    border-radius: 0 8px 8px 0;
                                    font-size:0.88rem;
                                    color: #d1fae5;
                                    margin-bottom: 8px;
                                ">
                                    💡 {email_item.get('razon','—')}
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                            with st.expander("Ver cuerpo del correo"):
                                st.text(email_item.get("snippet", ""))
                        with col_action:
                            if st.session_state.connected:
                                if st.button(
                                    "➕ Crear oportunidad",
                                    key=f"create_from_gmail_{i}",
                                    use_container_width=True,
                                ):
                                    # Pre-llenar datos desde el email para el flujo de creación
                                    nombre_contacto = email_item.get("nombre_contacto") or email_item.get("from", "")
                                    empresa_contacto = email_item.get("empresa_contacto") or ""
                                    email_contacto = email_item.get("email_contacto") or email_item.get("from", "")
                                    servicio_desc = email_item.get("subject", "Consulta desde Gmail")

                                    st.session_state.pending_create = {
                                        "ACTION": "CREATE_OPPORTUNITY",
                                        "nombre": nombre_contacto,
                                        "empresa": empresa_contacto,
                                        "email": email_contacto,
                                        "servicio": servicio_desc,
                                    }
                                    # Ir al tab de chat para manejar duplicados
                                    st.info("✅ Datos cargados. Ve a la pestaña **💬 Chat con Aria** para confirmar la creación.")
                            else:
                                st.caption("Conecta Odoo para crear")

            # Correos no relevantes
            if otros:
                with st.expander(f"📭 Ver {len(otros)} correos no relevantes"):
                    for email_item in otros:
                        st.markdown(
                            f"""
                            <div style="
                                padding: 8px 12px;
                                border-bottom: 1px solid rgba(99,102,241,0.1);
                                font-size:0.85rem;
                                color: rgba(148,163,184,0.7);
                            ">
                                <strong>{email_item.get('subject','(Sin asunto)')}</strong>
                                &nbsp;·&nbsp; {email_item.get('from','')}
                                &nbsp;·&nbsp; <em>{email_item.get('razon','—')}</em>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

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
