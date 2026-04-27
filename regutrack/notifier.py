"""Notification system — new regulatory documents — EnergyBot ACP."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import httpx

from regutrack.config import settings
from regutrack.models import Document

logger = logging.getLogger(__name__)

# ── Brand constants ──────────────────────────────────────────────────────────
_BRAND_NAME     = "ReguTrack ACP"
_BRAND_TAG      = "Alertas EnergyBot-ACP"
_BRAND_COLOR    = "#0A2240"   # Dark navy
_ACCENT_COLOR   = "#E8A020"   # Amber/gold
_MANAGER        = "Camilo Andrés Triana y Sotomonte"
_MANAGER_TITLE  = "Gerente TI e Innovación"
_ADDRESS        = "Carrera 7ª No. 73-47 Piso 12. Bogotá, D.C. – Colombia"
_DISCLAIMER     = "Track Diario de regulaciones en Colombia"


# ── Email HTML template ──────────────────────────────────────────────────────

def _build_html(docs_by_entity: dict) -> str:
    """Build the branded HTML email body — one table with Entity column."""

    total = sum(len(v) for v in docs_by_entity.values())
    rows_html = ""
    shown = 0
    for entity_name, docs in docs_by_entity.items():
        for doc in docs:
            if shown >= 50:   # hard cap
                break
            date_str  = str(doc.publication_date) if doc.publication_date else "—"
            type_str  = doc.doc_type or "Norma"
            num_str   = doc.number or ""
            title_str = doc.title

            if doc.url:
                title_html = f'<a href="{doc.url}" style="color:{_ACCENT_COLOR};text-decoration:none;font-weight:600;">{title_str}</a>'
            else:
                title_html = f'<span style="font-weight:600;">{title_str}</span>'

            rows_html += f"""
        <tr>
          <td style="padding:9px 10px;border-bottom:1px solid #e8ecf0;color:#444;font-size:12px;white-space:nowrap;vertical-align:top">{entity_name}</td>
          <td style="padding:9px 10px;border-bottom:1px solid #e8ecf0;color:#555;font-size:12px;white-space:nowrap;vertical-align:top">{date_str}</td>
          <td style="padding:9px 10px;border-bottom:1px solid #e8ecf0;vertical-align:top">
            <span style="background:{_ACCENT_COLOR};color:#fff;font-size:10px;font-weight:700;
                         padding:2px 7px;border-radius:10px;">{type_str}</span>
            {f'<span style="color:#888;font-size:11px;margin-left:5px;">#{num_str}</span>' if num_str else ""}
          </td>
          <td style="padding:9px 10px;border-bottom:1px solid #e8ecf0;font-size:11px;line-height:1.4;vertical-align:top">{title_html}</td>
        </tr>"""
            shown += 1

    overflow_note = ""
    if total > 50:
        overflow_note = f'<p style="color:#888;font-size:12px;margin-top:8px;">… y {total-50} documento(s) adicional(es). Ingrese a la plataforma para verlos todos.</p>'

    entities_summary = ", ".join(docs_by_entity.keys())


    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Alertas EnergyBot-ACP</title>
</head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:'Segoe UI',Arial,sans-serif;">

  <!-- Wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:32px 0;">
    <tr><td align="center">
      <table width="680" cellpadding="0" cellspacing="0"
             style="max-width:680px;background:#ffffff;border-radius:8px;
                    box-shadow:0 2px 12px rgba(0,0,0,0.08);overflow:hidden;">

        <!-- ── Header ── -->
        <tr>
          <td style="background:{_BRAND_COLOR};padding:28px 36px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td>
                  <p style="margin:0;color:{_ACCENT_COLOR};font-size:11px;
                             font-weight:700;letter-spacing:2px;text-transform:uppercase;">
                    {_BRAND_TAG}
                  </p>
                  <h1 style="margin:6px 0 0;color:#ffffff;font-size:22px;font-weight:700;">
                    {_BRAND_NAME}
                  </h1>
                </td>
                <td align="right" style="width:80px;">
                  <img src="data:image/png;base64,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"
                       width="80" height="80"
                       alt="EnergyBot ACP"
                       style="display:block;border-radius:50%;border:3px solid {_ACCENT_COLOR};">
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- ── Alert badge ── -->
        <tr>
          <td style="background:{_ACCENT_COLOR};padding:10px 36px;">
            <p style="margin:0;color:{_BRAND_COLOR};font-size:13px;font-weight:700;">
              🔔 &nbsp;{len(docs)} nuevo(s) documento(s) normativo(s) detectado(s)
            </p>
          </td>
        </tr>

        <!-- ── Body ── -->
        <tr>
          <td style="padding:28px 36px;">

            <p style="margin:0 0 6px;font-size:13px;color:#888;text-transform:uppercase;
                       letter-spacing:1px;font-weight:600;">Nuevas normas detectadas</p>
            <p style="margin:0 0 20px;font-size:13px;color:#555;">
              {total} documento(s) en {len(docs_by_entity)} entidad(es):<br>
              <span style="color:{_BRAND_COLOR};font-weight:600;">{entities_summary}</span>
            </p>

            <!-- Document table -->
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="border-collapse:collapse;border:1px solid #e8ecf0;border-radius:6px;
                           overflow:hidden;font-family:'Segoe UI',Arial,sans-serif;">
              <thead>
                <tr style="background:#f7f9fc;">
                  <th width="110" style="padding:9px 10px;text-align:left;font-size:11px;color:#666;
                              font-weight:700;border-bottom:2px solid #e0e5eb;">Entidad</th>
                  <th width="80" style="padding:9px 10px;text-align:left;font-size:11px;color:#666;
                              font-weight:700;border-bottom:2px solid #e0e5eb;white-space:nowrap;">Fecha</th>
                  <th width="140" style="padding:9px 10px;text-align:left;font-size:11px;color:#666;
                              font-weight:700;border-bottom:2px solid #e0e5eb;">Tipo</th>
                  <th style="padding:9px 10px;text-align:left;font-size:11px;color:#666;
                              font-weight:700;border-bottom:2px solid #e0e5eb;">Documento</th>
                </tr>
              </thead>
              <tbody>
                {rows_html}
              </tbody>
            </table>

            {overflow_note}

          </td>
        </tr>

        <!-- ── Divider ── -->
        <tr>
          <td style="padding:0 36px;">
            <hr style="border:none;border-top:1px solid #e8ecf0;margin:0;">
          </td>
        </tr>

        <!-- ── Footer ── -->
        <tr>
          <td style="padding:24px 36px;background:#f7f9fc;">
            <p style="margin:0 0 4px;font-size:13px;color:{_BRAND_COLOR};font-weight:700;">
              Atentamente,
            </p>
            <p style="margin:0 0 2px;font-size:13px;color:#333;font-weight:600;">
              {_BRAND_NAME}
            </p>
            <p style="margin:0 0 2px;font-size:12px;color:#555;">
              {_ADDRESS}
            </p>
            <p style="margin:16px 0 0;font-size:11px;color:#aaa;line-height:1.6;">
              <strong style="color:#888;">{_DISCLAIMER}</strong><br>
              {_BRAND_NAME}, liderado por {_MANAGER}, {_MANAGER_TITLE}.<br><br>
              <em>Este mensaje es automático, por favor no responda.</em>
            </p>
          </td>
        </tr>

        <!-- ── Bottom bar ── -->
        <tr>
          <td style="background:{_BRAND_COLOR};padding:12px 36px;">
            <p style="margin:0;font-size:10px;color:rgba(255,255,255,0.4);text-align:center;">
              © {_BRAND_NAME} · Sistema de Monitoreo Normativo Colombia
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>

</body>
</html>"""


def _build_plain(docs: list[Document], entity_name: str) -> str:
    """Plain-text fallback."""
    lines = [
        f"ALERTAS ENERGYBOT-ACP — {len(docs)} nueva(s) norma(s)",
        f"Entidad: {entity_name}",
        "=" * 60,
    ]
    for doc in docs[:20]:
        lines.append(
            f"[{doc.doc_type or 'Norma'}] {doc.title}"
            f" | {doc.publication_date or 'Fecha desconocida'}"
            f" | {doc.url or 'Sin URL'}"
        )
    lines += [
        "",
        "Atentamente,",
        f"{_BRAND_NAME}",
        f"{_ADDRESS}",
        "",
        f"{_DISCLAIMER} — {_BRAND_NAME}, liderado por {_MANAGER}, {_MANAGER_TITLE}.",
        "Este mensaje es automático, por favor no responda.",
    ]
    return "\n".join(lines)


# ── Public interface ─────────────────────────────────────────────────────────

def notify_new_documents(new_docs: list[Document], entity_name: str) -> None:
    """
    Called after each entity scrape. Logs and sends webhook only.
    Email is sent once at the end of the full run via notify_run_summary().
    """
    if not new_docs:
        return
    _log_notification(new_docs, entity_name)
    if settings.notifier_webhook_url:
        _send_webhook(new_docs, entity_name)


def notify_run_summary(docs_by_entity: dict) -> None:
    """
    Send ONE consolidated email after a full scraping run finishes.
    docs_by_entity: {entity_name: [Document, ...]}
    Only called when there is at least one new document.
    """
    total = sum(len(v) for v in docs_by_entity.values())
    if total == 0:
        logger.info("[Notifier] No new documents this run — email skipped.")
        return

    logger.info(f"[Notifier] Sending consolidated email: {total} docs across {len(docs_by_entity)} entities")

    if settings.notifier_smtp_host and settings.notifier_email_to:
        _send_consolidated_email(docs_by_entity)


def _log_notification(docs: list[Document], entity_name: str) -> None:
    logger.info(f"🔔 NUEVAS NORMAS [{entity_name}]: {len(docs)} documento(s)")
    for doc in docs:
        logger.info(
            f"  → [{doc.doc_type}] {doc.title[:80]}{'...' if len(doc.title) > 80 else ''}"
            f" | {doc.url or 'sin URL'}"
        )


def _send_webhook(docs: list[Document], entity_name: str) -> None:
    payload = {
        "text": f"🔔 *{_BRAND_TAG} — Nuevas normas detectadas*\n*Entidad:* {entity_name}",
        "attachments": [
            {
                "title": f"[{doc.doc_type}] {doc.title}",
                "title_link": doc.url or "",
                "text": doc.raw_summary or "",
                "footer": f"Publicado: {doc.publication_date or 'Fecha desconocida'}",
            }
            for doc in docs[:10]
        ],
    }
    try:
        response = httpx.post(settings.notifier_webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        logger.debug(f"Webhook enviado: {response.status_code}")
    except Exception as exc:
        logger.warning(f"Fallo al enviar webhook: {exc}")


def _build_plain_consolidated(docs_by_entity: dict) -> str:
    total = sum(len(v) for v in docs_by_entity.values())
    lines = [
        f"ALERTAS ENERGYBOT-ACP — {total} nueva(s) norma(s)",
        "=" * 60,
    ]
    for entity_name, docs in docs_by_entity.items():
        lines.append(f"\n[{entity_name}]")
        for doc in docs:
            lines.append(
                f"  [{doc.doc_type or 'Norma'}] {doc.title}"
                f" | {doc.publication_date or 'Fecha desconocida'}"
                f" | {doc.url or 'Sin URL'}"
            )
    lines += [
        "",
        "Atentamente,",
        f"{_BRAND_NAME}",
        f"{_ADDRESS}",
        "",
        f"{_DISCLAIMER} — {_BRAND_NAME}, liderado por {_MANAGER}, {_MANAGER_TITLE}.",
        "Este mensaje es automatico, por favor no responda.",
    ]
    return "\n".join(lines)


def _send_consolidated_email(docs_by_entity: dict) -> None:
    total = sum(len(v) for v in docs_by_entity.values())
    n_ents = len(docs_by_entity)
    subject = f"[{_BRAND_TAG}] {total} nueva(s) norma(s) en {n_ents} entidad(es)"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{_BRAND_NAME} <{settings.notifier_email_from}>"
    msg["To"]      = settings.notifier_email_to

    msg.attach(MIMEText(_build_plain_consolidated(docs_by_entity), "plain", "utf-8"))
    msg.attach(MIMEText(_build_html(docs_by_entity),               "html",  "utf-8"))

    try:
        with smtplib.SMTP(settings.notifier_smtp_host, settings.notifier_smtp_port) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(settings.notifier_smtp_user, settings.notifier_smtp_pass)
            smtp.sendmail(
                settings.notifier_email_from,
                [addr.strip() for addr in settings.notifier_email_to.split(",")],
                msg.as_bytes(),
            )
        logger.info(f"Email consolidado enviado a {settings.notifier_email_to} [{total} docs, {n_ents} entidades]")
    except Exception as exc:
        logger.warning(f"Fallo al enviar email consolidado: {exc}")

