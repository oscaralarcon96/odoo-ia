# 🤖 Odoo CRM · Asistente de Ventas IA

Aplicación web que conecta a tu instancia **Odoo Cloud** vía XML-RPC, extrae datos del pipeline CRM y permite hacer consultas en **lenguaje natural** usando OpenAI como motor de IA.

---

## 🚀 Instalación rápida

### 1. Clonar / situar el proyecto

```bash
cd /ruta/a/odoo-ia
```

### 2. Crear entorno virtual (recomendado)

```bash
python3 -m venv venv
source venv/bin/activate   # macOS / Linux
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar credenciales

```bash
cp .env.example .env
```

Edita `.env` con tus datos:

```env
ODOO_URL=https://tuempresa.odoo.com
ODOO_DB=nombre-de-tu-db
ODOO_USERNAME=tu@email.com
ODOO_API_KEY=tu_api_key_de_odoo

OPENAI_API_KEY=sk-...
```

> **¿Dónde obtengo la API Key de Odoo?**  
> Odoo Cloud → `Configuración` → `Usuarios` → Tu usuario → `Claves de API` → `Nueva clave`.

### 5. Ejecutar la aplicación

```bash
streamlit run app.py
```

Abre tu navegador en `http://localhost:8501` 🎉

---

## 📋 Estructura del proyecto

```
odoo-ia/
├── app.py               # 🖥️  Interfaz Streamlit (Fase 3)
├── odoo_connector.py    # 🔗  Conexión XML-RPC a Odoo (Fase 1)
├── data_processor.py    # 🧹  Procesamiento de datos para la IA (Fase 2)
├── ai_agent.py          # 🤖  Integración OpenAI — Analista de Ventas (Fase 4)
├── requirements.txt     # 📦  Dependencias Python
├── .env.example         # 🔒  Plantilla de variables de entorno
└── README.md
```

---

## 💬 Ejemplos de preguntas al asistente

- *"¿Qué oportunidades tienen más del 80% de probabilidad de cierre?"*
- *"¿Cuál es el ingreso esperado total de mi pipeline?"*
- *"Resúmeme el estado del prospecto [Nombre]"*
- *"¿Qué etapa concentra más oportunidades?"*
- *"¿Qué leads no tienen fecha de cierre definida?"*
- *"¿Quién es el vendedor con mayor cartera potencial?"*

---

## 🔒 Seguridad

- Las credenciales nunca se almacenan en disco desde la UI — solo en `st.session_state`.
- El archivo `.env` está en `.gitignore` por defecto (agrégalo si aún no está).
- La API Key de Odoo tiene permisos limitables — se recomienda crear una clave exclusiva para esta app.

---

## 🛠️ Tecnologías

| Tecnología | Uso |
|---|---|
| Python 3.11+ | Lenguaje base |
| `xmlrpc.client` | Conexión con Odoo (stdlib) |
| `pandas` | Procesamiento de datos CRM |
| `openai` | Motor de IA (gpt-4o-mini) |
| `streamlit` | Interfaz web |
| `python-dotenv` | Gestión de variables de entorno |
