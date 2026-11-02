"""Envío de correos (HU-15: el código de acceso del repartidor).

Se usa SMTP, el protocolo estándar para mandar correos: la app se conecta al servidor de correo (por
ejemplo, el de Gmail) con un usuario y contraseña, y le entrega el mensaje. La configuración sale del .env.
"""

import logging
import smtplib
from email.message import EmailMessage

from repartos.core.config import settings

logger = logging.getLogger(__name__)


def configurado() -> bool:
    return bool(settings.smtp_host)


def enviar(destinatario: str, asunto: str, cuerpo: str) -> bool:
    """Manda el correo. Devuelve True si el servidor lo aceptó y False si no está configurado o falló.

    Nunca lanza excepción: si el correo falla, la acción que lo pidió (el alta) tiene que seguir funcionando.
    """
    if not configurado():
        logger.info("Correo no configurado (SMTP_HOST vacío): no se envía el mensaje a %s", destinatario)
        return False

    mensaje = EmailMessage()
    mensaje["From"] = settings.smtp_remitente or settings.smtp_usuario
    mensaje["To"] = destinatario
    mensaje["Subject"] = asunto
    mensaje.set_content(cuerpo)

    try:
        # timeout: si el servidor de correo no responde, el operario no se queda esperando para siempre.
        with smtplib.SMTP(settings.smtp_host, settings.smtp_puerto, timeout=10) as servidor:
            servidor.starttls()  # cifra la conexión antes de mandar la contraseña
            if settings.smtp_usuario:
                servidor.login(settings.smtp_usuario, settings.smtp_contrasena)
            servidor.send_message(mensaje)
    except (smtplib.SMTPException, OSError):
        logger.exception("No se pudo enviar el correo a %s", destinatario)
        return False
    return True
