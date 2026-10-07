from dataclasses import dataclass
from datetime import date
import logging
from pathlib import Path
from typing import Optional
import uuid

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

from app.core.config import settings

logger = logging.getLogger(__name__)


class PDFGenerationError(Exception):
    """Custom exception raised when certificate PDF generation fails."""

    pass


@dataclass
class CertificateData:
    """Input payload for generating a certificate PDF."""

    certificate_id: uuid.UUID
    job_id: uuid.UUID
    recipient_name: str
    event_name: str
    event_date: Optional[date] = None


def generate_certificate_pdf(
    data: CertificateData,
    base_storage_dir: Optional[Path] = None,
) -> Path:
    """Generates a professional PDF certificate file using ReportLab."""
    try:
        storage_root = (
            base_storage_dir
            if base_storage_dir is not None
            else Path(settings.STORAGE_PATH)
        )
        job_dir = storage_root / "certificates" / str(data.job_id)
        job_dir.mkdir(parents=True, exist_ok=True)

        output_file = job_dir / f"{data.certificate_id}.pdf"

        page_width, page_height = landscape(A4)

        c = canvas.Canvas(
            str(output_file),
            pagesize=(page_width, page_height),
            compress=0,
        )
        c.setPageCompression(0)
        c.setTitle(f"Certificate - {data.recipient_name}")

        _draw_borders(c, page_width, page_height)

        # 1. Header Title
        c.setFillColor(colors.HexColor("#1A365D"))
        c.setFont("Helvetica-Bold", 28)
        c.drawCentredString(page_width / 2.0, page_height - 100, "CERTIFICATE OF PARTICIPATION")

        # 2. Subtitle
        c.setFillColor(colors.HexColor("#4A5568"))
        c.setFont("Helvetica", 14)
        c.drawCentredString(
            page_width / 2.0, page_height - 145, "This certificate is proudly presented to"
        )

        # 3. Recipient Name
        c.setFillColor(colors.HexColor("#1A202C"))
        c.setFont("Helvetica-Bold", 26)
        c.drawCentredString(page_width / 2.0, page_height - 200, data.recipient_name.strip())

        # Decorative accent line
        c.setStrokeColor(colors.HexColor("#D69E2E"))
        c.setLineWidth(1.5)
        c.line(page_width / 2.0 - 150, page_height - 215, page_width / 2.0 + 150, page_height - 215)

        # 4. Presentation text
        c.setFillColor(colors.HexColor("#4A5568"))
        c.setFont("Helvetica", 13)
        c.drawCentredString(page_width / 2.0, page_height - 260, "for successfully participating in")

        # 5. Event Name
        c.setFillColor(colors.HexColor("#2B6CB0"))
        c.setFont("Helvetica-Bold", 22)
        c.drawCentredString(page_width / 2.0, page_height - 300, data.event_name.strip())

        # 6. Event Date
        formatted_date = (
            data.event_date.strftime("%d %B %Y") if data.event_date else "N/A"
        )
        c.setFillColor(colors.HexColor("#4A5568"))
        c.setFont("Helvetica", 12)
        c.drawCentredString(page_width / 2.0, page_height - 340, f"Date: {formatted_date}")

        # 7. Signature & Footer Section
        c.setStrokeColor(colors.HexColor("#718096"))
        c.setLineWidth(1)
        c.line(page_width - 240, 120, page_width - 80, 120)
        c.setFillColor(colors.HexColor("#4A5568"))
        c.setFont("Helvetica", 11)
        c.drawCentredString(page_width - 160, 100, "Authorized Signature")

        c.setFillColor(colors.HexColor("#718096"))
        c.setFont("Helvetica", 9)
        c.drawString(80, 100, f"Certificate ID: {data.certificate_id}")

        c.save()
        logger.info("Successfully generated certificate PDF at: %s", output_file)
        return output_file

    except Exception as exc:
        logger.error("Failed to generate PDF for certificate %s: %s", getattr(data, "certificate_id", "unknown"), exc, exc_info=True)
        raise PDFGenerationError(f"Certificate PDF generation failed: {exc}") from exc


def _draw_borders(c: canvas.Canvas, width: float, height: float) -> None:
    """Draws outer navy and inner gold decorative border frames."""
    c.setStrokeColor(colors.HexColor("#1A365D"))
    c.setLineWidth(4)
    c.rect(20, 20, width - 40, height - 40)

    c.setStrokeColor(colors.HexColor("#D69E2E"))
    c.setLineWidth(1.5)
    c.rect(28, 28, width - 56, height - 56)
