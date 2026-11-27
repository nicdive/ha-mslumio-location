#!/usr/bin/env python3
"""Build the 49 Ledbury guest user manual PDF."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SHOTS = HERE
OUT_ARTIFACT = Path("/opt/cursor/artifacts/49-Ledbury-Guest-User-Manual.pdf")
OUT_DOCS = HERE / "49-Ledbury-Guest-User-Manual.pdf"
LOGO = REPO / "custom_components/usvegliu/www/logo-ledbury.png"

GREEN = HexColor("#1F3A2E")
GREEN_SOFT = HexColor("#3D5C4C")
INK = HexColor("#1A2420")
MUTED = HexColor("#5C6B63")
PAPER = HexColor("#F2F6F3")
CARD = HexColor("#FFFFFF")
RULE = HexColor("#C5D0C8")
ACCENT = HexColor("#8FA896")


class PhoneShot(Flowable):
    """Phone screenshot with a thin frame."""

    def __init__(self, path: Path, max_h=118 * mm, label: str = ""):
        super().__init__()
        self.path = path
        self.label = label
        self.max_h = max_h
        img = Image(str(path))
        scale = min(62 * mm / img.imageWidth, max_h / img.imageHeight)
        self.img_w = img.imageWidth * scale
        self.img_h = img.imageHeight * scale
        self.width = self.img_w + 8
        self.height = self.img_h + (14 if label else 6)

    def draw(self):
        c = self.canv
        x = 3
        y = self.height - self.img_h - 3
        c.setStrokeColor(GREEN)
        c.setLineWidth(1.2)
        c.setFillColor(CARD)
        c.roundRect(x - 2, y - 2, self.img_w + 4, self.img_h + 4, 10, fill=1, stroke=1)
        c.drawImage(
            str(self.path),
            x,
            y,
            width=self.img_w,
            height=self.img_h,
            preserveAspectRatio=True,
            mask="auto",
        )
        if self.label:
            c.setFillColor(MUTED)
            c.setFont("Helvetica", 8)
            c.drawCentredString(self.width / 2, 2, self.label)


def styles():
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "cover_title",
            parent=base["Title"],
            fontName="Times-Bold",
            fontSize=34,
            leading=38,
            textColor=GREEN,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontName="Times-Bold",
            fontSize=18,
            leading=22,
            textColor=GREEN,
            spaceBefore=4,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName="Times-Bold",
            fontSize=13,
            leading=16,
            textColor=GREEN_SOFT,
            spaceBefore=10,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=INK,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=12.5,
            textColor=INK,
            leftIndent=4,
        ),
        "caption": ParagraphStyle(
            "caption",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=10,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceBefore=2,
            spaceAfter=8,
        ),
        "footer": ParagraphStyle(
            "footer",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=MUTED,
            alignment=TA_CENTER,
        ),
        "callout": ParagraphStyle(
            "callout",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=GREEN,
            alignment=TA_LEFT,
        ),
        "small": ParagraphStyle(
            "small",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=MUTED,
        ),
    }


def header_footer(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    if doc.page > 1:
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.4)
        canvas.line(18 * mm, h - 12 * mm, w - 18 * mm, h - 12 * mm)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(18 * mm, h - 10 * mm, "49 Ledbury  ·  Guest User Manual")
        canvas.drawRightString(w - 18 * mm, h - 10 * mm, "Notting Hill · London")
        canvas.line(18 * mm, 12 * mm, w - 18 * mm, 12 * mm)
        canvas.drawCentredString(w / 2, 7 * mm, f"{doc.page}")
    canvas.restoreState()


def callout_box(text: str, s, width):
    p = Paragraph(text, s["callout"])
    t = Table([[p]], colWidths=[width])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), HexColor("#E4EDE7")),
                ("BOX", (0, 0), (-1, -1), 0.4, ACCENT),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return t


def two_col_shots(left_path, left_label, right_path, right_label, s):
    left = PhoneShot(left_path, max_h=105 * mm, label=left_label)
    right = PhoneShot(right_path, max_h=105 * mm, label=right_label)
    t = Table([[left, right]], colWidths=[95 * mm, 95 * mm])
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def build():
    s = styles()
    content_w = A4[0] - 36 * mm
    story = []

    # -- Cover --
    story.append(Spacer(1, 28 * mm))
    if LOGO.exists():
        logo = Image(str(LOGO), width=28 * mm, height=28 * mm)
        logo.hAlign = "CENTER"
        story.append(logo)
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("49 LEDBURY", s["cover_title"]))
    story.append(Paragraph("NOTTING HILL  ·  LONDON", s["cover_sub"]))
    story.append(Spacer(1, 10 * mm))
    story.append(
        Paragraph(
            "Guest User Manual",
            ParagraphStyle(
                "manual",
                parent=s["cover_title"],
                fontSize=22,
                leading=26,
                textColor=INK,
            ),
        )
    )
    story.append(Spacer(1, 4 * mm))
    story.append(
        Paragraph(
            "Wi-Fi voucher · Home web app with access",
            s["cover_sub"],
        )
    )
    story.append(Spacer(1, 16 * mm))
    story.append(
        callout_box(
            "<b>Your stay, your link.</b> Before arrival you receive the guest Wi-Fi "
            "details and a private link to the 49 Ledbury home app.",
            s,
            content_w,
        )
    )
    story.append(Spacer(1, 12 * mm))
    story.append(Paragraph("Valid for your stay dates only", s["cover_sub"]))
    story.append(PageBreak())

    # -- 1 Getting started --
    story.append(Paragraph("1. Getting started", s["h1"]))
    story.append(
        Paragraph(
            "A few days before arrival you receive a welcome message with:",
            s["body"],
        )
    )
    for b in (
        "<b>Wi-Fi network</b> — e.g. <font face='Courier'>49Ledbury-Guest</font>",
        "<b>Wi-Fi voucher</b> — one code for your stay (several devices)",
        "<b>Home app link</b> — private URL for heating, lights, access, TV, and more",
    ):
        story.append(Paragraph(f"-  {b}", s["bullet"]))
        story.append(Spacer(1, 2 * mm))

    story.append(Paragraph("When it opens", s["h2"]))
    story.append(
        Paragraph(
            "The <b>home app</b> unlocks on your <b>arrival day</b>. Earlier, you may see "
            "<i>Available from …</i> The link closes at the end of departure day; "
            "Wi-Fi may stay one extra day.",
            s["body"],
        )
    )
    story.append(
        callout_box(
            "<b>Add to Home Screen.</b> iPhone: Share → Add to Home Screen. "
            "Android: browser menu → Install. Keep the personal link.",
            s,
            content_w,
        )
    )
    story.append(PageBreak())

    # -- 2 Wi-Fi --
    story.append(Paragraph("2. Guest Wi-Fi & voucher", s["h1"]))
    story.append(
        Paragraph(
            "Join the guest Wi-Fi from your welcome message. When the "
            "<b>captive portal</b> appears, enter your <b>Wi-Fi voucher</b>.",
            s["body"],
        )
    )
    for i, step in enumerate(
        (
            "Select the guest network (e.g. <font face='Courier'>49Ledbury-Guest</font>).",
            "Enter the voucher on the captive portal page.",
            "Or open the home app → <b>Info</b> → <b>Copy</b> next to Wi-Fi / code.",
        ),
        1,
    ):
        story.append(Paragraph(f"<b>{i}.</b>  {step}", s["bullet"]))
        story.append(Spacer(1, 2 * mm))

    story.append(
        Paragraph(
            "Find the code again anytime under <b>Info</b> in the home app.",
            s["body"],
        )
    )
    story.append(Spacer(1, 4 * mm))
    story.append(PhoneShot(SHOTS / "info.png", max_h=120 * mm, label="Info — Wi-Fi & share"))
    story.append(PageBreak())

    # -- 3 Home app --
    story.append(Paragraph("3. Home web app", s["h1"]))
    story.append(
        Paragraph(
            "Open your personal link on your phone. Tabs appear when useful for your stay:",
            s["body"],
        )
    )
    nav = [
        ["Tab", "What it does"],
        ["Home", "Welcome, London weather, alarm status"],
        ["Heating", "Heating by room (no cooling)"],
        ["Lights", "Lights, dimmers, scenes"],
        ["Access", "Door lock, alarm, doorbell"],
        ["TV", "Apple TV remote — power, pad, volume"],
        ["Sound", "Audio zones (if available)"],
        ["Info", "Wi-Fi voucher, QR / link to share the app"],
    ]
    rows = [
        [
            Paragraph(f"<b>{a}</b>", s["small"]),
            Paragraph(f"<b>{b}</b>" if i == 0 else b, s["small"]),
        ]
        for i, (a, b) in enumerate(nav)
    ]
    table = Table(rows, colWidths=[28 * mm, content_w - 28 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), GREEN),
                ("TEXTCOLOR", (0, 0), (-1, 0), white),
                ("BACKGROUND", (0, 1), (-1, -1), CARD),
                ("BOX", (0, 0), (-1, -1), 0.4, RULE),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, RULE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 6 * mm))
    story.append(two_col_shots(SHOTS / "home.png", "Home", SHOTS / "heating.png", "Heating", s))
    story.append(PageBreak())

    # -- 4 Features --
    story.append(Paragraph("4. Using the controls", s["h1"]))

    story.append(Paragraph("Heating", s["h2"]))
    story.append(
        Paragraph(
            "<b>Adjust</b> for ± setpoint and on/off; <b>Overview</b> for room cards. "
            "Tap a room for the dial.",
            s["body"],
        )
    )

    story.append(Paragraph("Lights", s["h2"]))
    story.append(
        Paragraph(
            "Grouped by room. Tap the lamp for on/off. Swipe a dimmable row for brightness. "
            "Scenes apply a set look in one tap.",
            s["body"],
        )
    )
    story.append(two_col_shots(SHOTS / "lights.png", "Lights", SHOTS / "access.png", "Access", s))

    story.append(Paragraph("Access", s["h2"]))
    story.append(
        Paragraph(
            "Door lock Open / Close; alarm Arm / Disarm with confirmation. "
            "If someone rings, a popup may show the door camera.",
            s["body"],
        )
    )

    story.append(Paragraph("TV", s["h2"]))
    story.append(
        Paragraph(
            "Open a TV for power, directional pad (▲▼◀▶ / OK), Menu, Home, and volume. "
            "Each screen uses a fixed Apple TV — no source grid in the app. "
            "You can also AirPlay from your phone to an Apple TV over guest Wi-Fi.",
            s["body"],
        )
    )

    story.append(Paragraph("Share", s["h2"]))
    story.append(
        Paragraph(
            "On Info, use the QR or copy the link for others in your party. "
            "Do not post the link publicly.",
            s["body"],
        )
    )
    story.append(PageBreak())

    # -- 5 Practical --
    story.append(Paragraph("5. Practical notes", s["h1"]))
    for n in (
        "If the link says the house is unavailable, check the network or ask for a fresh link.",
        "After checkout the personal link stops; Wi-Fi may linger one more day.",
    ):
        story.append(Paragraph(f"-  {n}", s["bullet"]))
        story.append(Spacer(1, 2 * mm))

    story.append(Paragraph("Need help?", s["h2"]))
    story.append(
        Paragraph(
            "Contact <b>The 49 Ledbury team</b> with your stay dates. "
            "Say whether the issue is Wi-Fi login or the home app link.",
            s["body"],
        )
    )
    story.append(Spacer(1, 20 * mm))
    story.append(Paragraph("© 49 Ledbury  ·  Guest experience guide", s["footer"]))
    story.append(Paragraph("Notting Hill · London", s["footer"]))

    OUT_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    OUT_DOCS.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT_ARTIFACT),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=16 * mm,
        title="49 Ledbury - Guest User Manual",
        author="49 Ledbury",
    )
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    import shutil

    shutil.copyfile(OUT_ARTIFACT, OUT_DOCS)
    print("wrote", OUT_ARTIFACT, OUT_ARTIFACT.stat().st_size)
    print("copied", OUT_DOCS)


if __name__ == "__main__":
    build()
