"""Owner Console copy (Lovelace) in French or English."""

from __future__ import annotations

from typing import Any, Final, Mapping

from .branding import brand_locale
from .const import LOCALE_EN, LOCALE_FR

_FR: Final[dict[str, str]] = {
    "home": "Accueil",
    "stays": "Séjours",
    "history": "Historique",
    "settings": "Réglages",
    "console": "Console",
    "console_intro": (
        "Séjour **en cours** et **prochain** à venir. "
        "Ouvrez une fiche pour le compte HA, le Wi-Fi et le message. "
        "Les locataires ne voient pas cette page."
    ),
    "open_stays": "Séjours ouverts",
    "current_wifi": "Code Wi-Fi courant",
    "heat_cool": "Chauffage / climatisation",
    "shortcuts": "Raccourcis",
    "tools": "Outils",
    "journal": "Journal",
    "current": "En cours",
    "next": "Prochain",
    "upcoming": "À venir",
    "wifi_still_active": "Wi-Fi encore actif",
    "trial": "Essai",
    "open": "Ouvrir",
    "read": "Lire",
    "create": "Créer",
    "apply": "Appliquer",
    "path": "Chemin",
    "generate": "Générer",
    "revoke": "Révoquer",
    "send": "Envoyer",
    "print": "Imprimer",
    "none": "aucun",
    "stay": "Séjour",
    "reread_calendar": "Relire le calendrier",
    "reread_calendar_confirm": (
        "Relire le calendrier maintenant ? Les accès Wi-Fi et HA suivront les réservations."
    ),
    "refresh_dashboards": "Rafraîchir les tableaux",
    "refresh_dashboards_confirm": "Réécrire Séjour et Console maintenant ?",
    "trial_link": "Lien d'essai 24 h",
    "trial_link_confirm": "Créer un lien maison d'essai (24 h, sans calendrier) ?",
    "export_journal": "Exporter le journal",
    "edit_settings": "Modifier les réglages",
    "all_stays": "Tous les séjours",
    "open_stay": "Ouvrir le séjour",
    "no_current": "Aucun séjour en cours.",
    "no_next": "Pas de réservation suivante dans la fenêtre.",
    "sensor_missing": "*Capteur séjours indisponible.*",
    "roster_intro": (
        "Du séjour **en cours** au plus lointain. Touchez un nom pour le compte, "
        "le Wi-Fi et le message."
    ),
    "no_open_stays": "*Aucun séjour ouvert.*",
    "history_intro": (
        "Séjours **clos** et dernières créations / retraits d'accès. "
        "Les codes Wi-Fi restent dans le fichier CSV."
    ),
    "past_stays": "Séjours passés",
    "no_past": "*Aucun séjour clos enregistré pour l'instant.*",
    "access": "Accès",
    "no_events": "*Pas encore d'événement.*",
    "trial_badge": "lien d'essai",
    "back_home": "← Accueil",
    "new_password": "Nouveau mot de passe",
    "new_password_confirm": "Générer un nouveau mot de passe pour {guest} ?",
    "revoke_ha": "Révoquer le compte HA",
    "revoke_ha_confirm": "Révoquer le compte Home Assistant de {guest} ?",
    "new_wifi": "Nouveau code Wi-Fi",
    "new_wifi_confirm": "Générer un nouveau code Wi-Fi pour {guest} ?",
    "apply_wifi": "Appliquer le code Wi-Fi",
    "apply_wifi_confirm": (
        "Coller le brouillon code Wi-Fi sur le séjour de {guest} ?"
    ),
    "wifi_draft": "Brouillon code Wi-Fi",
    "revoke_wifi": "Révoquer le Wi-Fi",
    "revoke_wifi_confirm": "Révoquer le voucher Wi-Fi de {guest} ?",
    "new_door": "Nouveau code porte",
    "new_door_confirm": "Générer un nouveau code porte pour {guest} ?",
    "revoke_door": "Révoquer le code porte",
    "revoke_door_confirm": "Révoquer le code porte de {guest} ?",
    "resend": "Renvoyer la notification",
    "resend_confirm": "Renvoyer le message d'accueil et la notification de {guest} ?",
    "print_voucher": "Imprimer le voucher",
    "print_confirm": "Émettre l'événement d'impression pour {guest} ?",
    "settings_usvegliu": "Réglages Usvegliu",
    "mode_per_stay": "un compte par séjour",
    "mode_shared": "compte locataire unique",
    "role_current": "En cours",
    "role_upcoming": "À venir",
    "role_departing": "Wi-Fi encore actif",
    "role_preview": "Essai 24 h",
}

_EN: Final[dict[str, str]] = {
    "home": "Home",
    "stays": "Stays",
    "history": "History",
    "settings": "Settings",
    "console": "Console",
    "console_intro": (
        "**Current** and **upcoming** stays. "
        "Open a card for the HA account, Wi-Fi and message. "
        "Guests do not see this page."
    ),
    "open_stays": "Open stays",
    "current_wifi": "Current Wi-Fi code",
    "heat_cool": "Heating / cooling",
    "shortcuts": "Shortcuts",
    "tools": "Tools",
    "journal": "Log",
    "current": "Current",
    "next": "Next",
    "upcoming": "Upcoming",
    "wifi_still_active": "Wi-Fi still active",
    "trial": "Trial",
    "open": "Open",
    "read": "Read",
    "create": "Create",
    "apply": "Apply",
    "path": "Path",
    "generate": "Generate",
    "revoke": "Revoke",
    "send": "Send",
    "print": "Print",
    "none": "none",
    "stay": "Stay",
    "reread_calendar": "Reload calendar",
    "reread_calendar_confirm": (
        "Reload the calendar now? Wi-Fi and HA access will follow the bookings."
    ),
    "refresh_dashboards": "Refresh dashboards",
    "refresh_dashboards_confirm": "Rewrite Stay and Console now?",
    "trial_link": "24 h trial link",
    "trial_link_confirm": "Create a 24 h trial Maison link (no calendar)?",
    "export_journal": "Export journal",
    "edit_settings": "Edit settings",
    "all_stays": "All stays",
    "open_stay": "Open stay",
    "no_current": "No stay in progress.",
    "no_next": "No upcoming booking in the window.",
    "sensor_missing": "*Stays sensor unavailable.*",
    "roster_intro": (
        "From the **current** stay to the furthest ahead. Tap a name for the account, "
        "Wi-Fi and message."
    ),
    "no_open_stays": "*No open stays.*",
    "history_intro": (
        "**Closed** stays and recent access create / revoke events. "
        "Wi-Fi codes stay in the CSV file."
    ),
    "past_stays": "Past stays",
    "no_past": "*No closed stays recorded yet.*",
    "access": "Access",
    "no_events": "*No events yet.*",
    "trial_badge": "trial link",
    "back_home": "← Home",
    "new_password": "New password",
    "new_password_confirm": "Generate a new password for {guest}?",
    "revoke_ha": "Revoke HA account",
    "revoke_ha_confirm": "Revoke the Home Assistant account for {guest}?",
    "new_wifi": "New Wi-Fi code",
    "new_wifi_confirm": "Generate a new Wi-Fi code for {guest}?",
    "apply_wifi": "Apply Wi-Fi code",
    "apply_wifi_confirm": "Paste the Wi-Fi code draft onto {guest}'s stay?",
    "wifi_draft": "Wi-Fi code draft",
    "revoke_wifi": "Revoke Wi-Fi",
    "revoke_wifi_confirm": "Revoke the Wi-Fi voucher for {guest}?",
    "new_door": "New door code",
    "new_door_confirm": "Generate a new door code for {guest}?",
    "revoke_door": "Revoke door code",
    "revoke_door_confirm": "Revoke the door code for {guest}?",
    "resend": "Resend notification",
    "resend_confirm": "Resend the welcome message and notification for {guest}?",
    "print_voucher": "Print voucher",
    "print_confirm": "Emit the print event for {guest}?",
    "settings_usvegliu": "Usvegliu settings",
    "mode_per_stay": "one account per stay",
    "mode_shared": "shared guest account",
    "role_current": "Current",
    "role_upcoming": "Upcoming",
    "role_departing": "Wi-Fi still active",
    "role_preview": "24 h trial",
}

_PACKS: Final[dict[str, dict[str, str]]] = {
    LOCALE_FR: _FR,
    LOCALE_EN: _EN,
}

_MONTHS_EN: Final[tuple[str, ...]] = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)

_MONTHS_FR: Final[tuple[str, ...]] = (
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
)


def normalize_console_locale(raw: object) -> str:
    """fr or en for Console copy."""
    return brand_locale({"locale": raw})


def console_t(locale: object, key: str, **kwargs: Any) -> str:
    """Translate one Console string."""
    lang = normalize_console_locale(locale)
    pack = _PACKS.get(lang) or _FR
    text = pack.get(key) or _FR.get(key) or key
    if kwargs:
        return text.format(**kwargs)
    return text


def role_label(role: str, locale: object = LOCALE_FR) -> str:
    """Stay role label on the Console roster."""
    key = {
        "current": "role_current",
        "upcoming": "role_upcoming",
        "departing": "role_departing",
        "preview": "role_preview",
    }.get(str(role or ""), "")
    if not key:
        return str(role or "")
    return console_t(locale, key)


def month_name(month: int, locale: object = LOCALE_FR) -> str:
    """1-based month name."""
    months = _MONTHS_EN if normalize_console_locale(locale) == LOCALE_EN else _MONTHS_FR
    if month < 1 or month > 12:
        return ""
    return months[month - 1]


def empty_sensor_value(locale: object = LOCALE_FR) -> str:
    """Native value when no stay / no voucher."""
    return console_t(locale, "none")


def access_mode_label(mode: str, locale: object = LOCALE_FR) -> str:
    """Human label for access_mode in settings."""
    from .const import ACCESS_PER_STAY, ACCESS_SHARED

    if mode == ACCESS_SHARED:
        return console_t(locale, "mode_shared")
    if mode == ACCESS_PER_STAY:
        return console_t(locale, "mode_per_stay")
    return mode


def pack_for(locale: object) -> Mapping[str, str]:
    """Full string pack (tests / advanced)."""
    lang = normalize_console_locale(locale)
    return _PACKS.get(lang) or _FR
