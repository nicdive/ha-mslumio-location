#!/usr/bin/env python3
"""Build the 49 Ledbury guest user manual PDF."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SHOTS = HERE  # PNGs live next to this script
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


class ColoredBox(Flowable):
    def __init__(self, width, height, color):
        super().__init__()
        self.width = width
        self.height = height
        self.color = color

    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.roundRect(0, 0, self.width, self.height, 8, fill=1, stroke=0)


class PhoneShot(Flowable):
    """Phone screenshot with a thin frame."""

    def __init__(self, path: Path, max_h=118 * mm, label: str = ""):
        super().__init__()
        self.path = path
        self.label = label
        self.max_h = max_h
        img = Image(str(path))
        # Native shots are 390x844
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
    s = {
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
    return s


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
            "Wi-Fi voucher · Door code · Home web app",
            s["cover_sub"],
        )
    )
    story.append(Spacer(1, 16 * mm))
    story.append(
        callout_box(
            "<b>Your stay, your link.</b> Before arrival you receive a personal message "
            "with the guest Wi-Fi details, door code (if enabled), and a private link "
            "to the 49 Ledbury home app. This guide explains how each piece works.",
            s,
            content_w,
        )
    )
    story.append(Spacer(1, 20 * mm))
    story.append(
        Paragraph(
            "English interface  ·  Mobile-first  ·  Valid for your stay dates only",
            s["cover_sub"],
        )
    )
    story.append(PageBreak())

    # -- 1 Getting started --
    story.append(Paragraph("1. Getting started", s["h1"]))
    story.append(
        Paragraph(
            "Around a few days before arrival (typically two), you receive a welcome "
            "message by email or from the host. It contains everything you need for "
            "the stay - no Home Assistant login is required for the guest app.",
            s["body"],
        )
    )
    story.append(Paragraph("What you receive", s["h2"]))
    bullets = [
        "<b>Wi-Fi network name</b> - join <font face='Courier'>49Ledbury-Guest</font> (or the SSID shown in your message).",
        "<b>Wi-Fi code (voucher)</b> - one password for your stay; several devices can use it.",
        "<b>Door code</b> - keypad PIN for the front door, when enabled for your booking.",
        "<b>Home app link</b> - a private URL that opens the 49 Ledbury controls on your phone.",
    ]
    for b in bullets:
        story.append(Paragraph(f"-  {b}", s["bullet"]))
        story.append(Spacer(1, 2 * mm))

    story.append(Paragraph("When things become active", s["h2"]))
    story.append(
        Paragraph(
            "Wi-Fi and door codes are prepared ahead of arrival so you can plan. "
            "The <b>home app link</b> unlocks on your <b>arrival day</b>. Opening it "
            "earlier shows a message such as <i>Available from 25 November.</i> "
            "The link closes at the end of your departure day; Wi-Fi may remain "
            "available one extra day depending on house settings.",
            s["body"],
        )
    )
    story.append(
        callout_box(
            "<b>Tip - Add to Home Screen.</b> On iPhone: open the stay link, then "
            "Share &gt; Add to Home Screen. On Android: browser menu &gt; Install app. "
            "Keep the URL that includes your personal code.",
            s,
            content_w,
        )
    )
    story.append(PageBreak())

    # -- 2 Wi-Fi --
    story.append(Paragraph("2. Guest Wi-Fi & voucher", s["h1"]))
    story.append(
        Paragraph(
            "Internet for guests uses a dedicated network. Access is granted with a "
            "<b>voucher code</b> created for your booking (Cambium EasyPass or equivalent). "
            "You do not need a separate portal account - connect to the network and enter "
            "the code when the hotspot page asks for it.",
            s["body"],
        )
    )
    story.append(Paragraph("How to connect", s["h2"]))
    steps = [
        "Open phone Wi-Fi settings and select the guest network shown in your welcome message (e.g. <font face='Courier'>49Ledbury-Guest</font>).",
        "When the captive portal / EasyPass page appears, enter your <b>Wi-Fi code</b>.",
        "Or open the home app &gt; <b>Info</b> and tap <b>Copy</b> next to Wi-Fi network / Wi-Fi code, then paste into the portal.",
        "Several devices can share the same voucher (within the house device limit).",
    ]
    for i, step in enumerate(steps, 1):
        story.append(Paragraph(f"<b>{i}.</b>  {step}", s["bullet"]))
        story.append(Spacer(1, 2 * mm))

    story.append(Paragraph("Where to find the code again", s["h2"]))
    story.append(
        Paragraph(
            "In the home app, open the <b>Info</b> tab. You will see "
            "<b>Wi-Fi network</b>, <b>Wi-Fi code</b>, and <b>Door code</b>, each with a "
            "Copy button. If a code was revoked by the host, the app shows it as revoked "
            "and a new one may appear in a fresh message.",
            s["body"],
        )
    )
    story.append(Spacer(1, 4 * mm))
    story.append(PhoneShot(SHOTS / "info.png", max_h=130 * mm, label="Info - Wi-Fi, door code, share"))
    story.append(Paragraph("Figure: Info tab with Wi-Fi voucher and door code.", s["caption"]))
    story.append(PageBreak())

    # -- 3 Home app --
    story.append(Paragraph("3. The home web app", s["h1"]))
    story.append(
        Paragraph(
            "The home app is a lightweight web application branded for 49 Ledbury "
            "(English). It only shows controls allowed for your stay. Open your "
            "personal link on the house Wi-Fi for the best experience.",
            s["body"],
        )
    )
    story.append(Paragraph("Bottom navigation", s["h2"]))
    nav = [
        ["Tab", "What it does"],
        ["Home", "Welcome, London weather, alarm status, charger status if plugged in"],
        ["Heating", "Underfloor / radiator setpoints by room (heating only - no cooling fans)"],
        ["Lights", "Room lights, dimmers, and lighting scenes"],
        ["Access", "Door lock, gate, shutters, alarm arm/disarm, doorbell, EV charger"],
        ["Info", "Wi-Fi, door code, QR / link to share the app"],
    ]
    rows = [
        [Paragraph(f"<b>{a}</b>", s["small"]), Paragraph(b, s["small"])]
        if i
        else [Paragraph(f"<b>{a}</b>", s["small"]), Paragraph(f"<b>{b}</b>", s["small"])]
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
    story.append(Paragraph("Figure: Home welcome & Heating controls.", s["caption"]))
    story.append(PageBreak())

    # -- 4 Features --
    story.append(Paragraph("4. Features in detail", s["h1"]))

    story.append(Paragraph("Heating", s["h2"]))
    story.append(
        Paragraph(
            "49 Ledbury is heating-only. Use <b>Adjust</b> to change setpoints with - / +, "
            "or power a room on and off. <b>Overview</b> shows room cards at a glance. "
            "Tap a room for the large dial. Outdoor temperature appears when a sensor is available.",
            s["body"],
        )
    )

    story.append(Paragraph("Lights", s["h2"]))
    story.append(
        Paragraph(
            "Lights are grouped by room. Tap the lamp icon to switch on/off. "
            "For dimmable lights, <b>swipe horizontally</b> on the row to set brightness "
            "(about 10% steps); release to confirm. Scene buttons (e.g. Evening, Night) "
            "apply a prepared look in one tap.",
            s["body"],
        )
    )
    story.append(two_col_shots(SHOTS / "lights.png", "Lights", SHOTS / "access.png", "Access", s))
    story.append(Paragraph("Figure: Lights & Access.", s["caption"]))

    story.append(Paragraph("Access & security", s["h2"]))
    story.append(
        Paragraph(
            "<b>Front door</b> - Open / Close (unlock / lock). "
            "<b>Gate / shutters</b> - Open, Close, or Stop while moving. "
            "<b>Home Alarm</b> - Arm or Disarm with a confirmation prompt. "
            "Home shows alarm status only (no arm button there). "
            "If someone rings, a <b>Door entry</b> popup may offer a live view and "
            "<b>Open the gate</b>. The EV charger card shows charge status when relevant.",
            s["body"],
        )
    )

    story.append(Paragraph("Share the app", s["h2"]))
    story.append(
        Paragraph(
            "On Info, use the QR code or copy the home link so other guests in your party "
            "can open the same stay on their phones. Everyone shares the same temporary access - "
            "do not post the link publicly.",
            s["body"],
        )
    )
    story.append(PageBreak())

    # -- 5 Practical --
    story.append(Paragraph("5. Practical notes", s["h1"]))
    story.append(Paragraph("Good to know", s["h2"]))
    notes = [
        "The app never shows a Home Assistant password - that is for the host Console only.",
        "Only equipment enabled for guests appears; missing tabs simply mean nothing is linked for that category.",
        "Prefer the house Wi-Fi for door, gate and live updates.",
        "If the link says the house is unavailable, check the network or ask the host for a fresh link.",
        "After checkout the personal link stops; Wi-Fi may linger one more day.",
    ]
    for n in notes:
        story.append(Paragraph(f"-  {n}", s["bullet"]))
        story.append(Spacer(1, 2 * mm))

    story.append(Paragraph("Need help?", s["h2"]))
    story.append(
        Paragraph(
            "Contact <b>The 49 Ledbury team</b> with your stay dates. Mention whether the "
            "issue is Wi-Fi login, door code, or the home app link so they can help quickly.",
            s["body"],
        )
    )
    story.append(Spacer(1, 10 * mm))
    story.append(
        callout_box(
            "Screenshots in this manual are illustrative (demo data). "
            "Your live codes, rooms and equipment names come from your booking.",
            s,
            content_w,
        )
    )
    story.append(Spacer(1, 16 * mm))
    story.append(Paragraph("© 49 Ledbury  ·  Guest experience guide", s["footer"]))
    story.append(Paragraph("Notting Hill · Portobello · London", s["footer"]))

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
