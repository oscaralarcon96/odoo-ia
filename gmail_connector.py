"""
gmail_connector.py
------------------
Conexión con la API de Gmail usando OAuth2.

Requiere:
  - credentials.json descargado desde Google Cloud Console
  - pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

Primera vez: abrirá una pestaña del navegador para autorizar.
Luego guarda token.json para usos futuros (no vuelve a pedir autorización).
"""

import os
import base64
import re
from email import message_from_bytes
from datetime import datetime, timedelta, timezone

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "credentials.json")
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "token.json")


def get_gmail_service(
    credentials_path: str = CREDENTIALS_FILE,
    token_path: str = TOKEN_FILE,
):
    """
    Construye y retorna el servicio autenticado de Gmail.
    Si no hay token guardado, abre el navegador para autorizar (OAuth2).
    """
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(
                    f"No se encontró credentials.json en: {credentials_path}\n"
                    "Descárgalo desde Google Cloud Console → APIs & Services → Credentials."
                )
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, "w") as token_file:
            token_file.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)
    return service


def fetch_recent_emails(
    service,
    days: int = 7,
    max_results: int = 50,
) -> list[dict]:
    """
    Obtiene los correos recibidos en los últimos `days` días.

    Retorna lista de dicts:
        {
            "id": str,
            "from": str,
            "subject": str,
            "date": str,
            "snippet": str,
            "body": str,      # Primeros 1000 chars del cuerpo plano
        }
    """
    query = f"newer_than:{days}d -from:me"

    try:
        result = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=max_results,
        ).execute()
    except Exception as exc:
        raise RuntimeError(f"Error al consultar Gmail API: {exc}") from exc

    messages_meta = result.get("messages", [])
    if not messages_meta:
        return []

    emails = []
    for meta in messages_meta:
        try:
            msg = service.users().messages().get(
                userId="me",
                id=meta["id"],
                format="full",
            ).execute()

            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            from_addr = headers.get("From", "Desconocido")
            subject = headers.get("Subject", "(Sin asunto)")
            date_str = headers.get("Date", "")
            snippet = msg.get("snippet", "")

            body = _extract_body(msg.get("payload", {}))

            emails.append({
                "id": meta["id"],
                "from": from_addr,
                "subject": subject,
                "date": date_str,
                "snippet": snippet,
                "body": body[:1500],
            })
        except Exception:
            continue  # Saltar mensajes que fallen individualmente

    return emails


def _extract_body(payload: dict) -> str:
    """
    Extrae el texto plano del cuerpo del email recursivamente.
    """
    mime_type = payload.get("mimeType", "")

    if mime_type == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")

    # Recursión para multipart
    if "parts" in payload:
        texts = []
        for part in payload["parts"]:
            text = _extract_body(part)
            if text:
                texts.append(text)
        return "\n".join(texts)

    # Fallback: text/html → limpiar tags
    if mime_type == "text/html":
        data = payload.get("body", {}).get("data", "")
        if data:
            html = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")
            clean = re.sub(r"<[^>]+>", " ", html)
            clean = re.sub(r"\s+", " ", clean).strip()
            return clean[:1500]

    return ""


def credentials_exist() -> bool:
    """Verifica si credentials.json existe en el directorio del proyecto."""
    return os.path.exists(CREDENTIALS_FILE)


def token_exists() -> bool:
    """Verifica si ya hay un token de autorización guardado."""
    return os.path.exists(TOKEN_FILE)


def revoke_token() -> None:
    """Borra el token guardado, forzando re-autorización en el próximo uso."""
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
