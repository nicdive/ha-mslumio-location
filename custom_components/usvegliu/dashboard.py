"""Dedicated Lovelace dashboard for tenants.

Home Assistant 2026 stores Lovelace under a HassKey, not ``hass.data["lovelace"]``.
Cards are written on the live ``LovelaceStorage`` for ``usvegliu-sejour`` when
that dashboard already exists. The dashboard collection is only used to create
the sidebar entry if it is missing.
"""

from __future__ import annotations

import logging
from typing import Any

from .const import (
    ATTR_RESERVATION_KEY,
    DASHBOARD_ICON,
    DASHBOARD_TITLE,
    DASHBOARD_URL,
    DOMAIN,
    OWNER_DASHBOARD_ICON,
    OWNER_DASHBOARD_TITLE,
    OWNER_DASHBOARD_URL,
    SERVICE_APPLY_DASHBOARD,
    SERVICE_EXPORT_JOURNAL,
    SERVICE_GUEST_LINK,
    SERVICE_REFRESH_CALENDAR,
    SERVICE_PRINT,
    SERVICE_REGENERATE_ACCESS,
    SERVICE_REGENERATE_NUKI,
    SERVICE_REGENERATE_VOUCHER,
    SERVICE_RESEND,
    SERVICE_REVOKE_ACCESS,
    SERVICE_REVOKE_NUKI,
    SERVICE_REVOKE_VOUCHER,
)
from .guest_session import credential_attribute_key, stay_view_path

_LOGGER = logging.getLogger(__name__)


def build_dashboard_config(entity_ids: list[str]) -> dict[str, Any]:
    """Return a sections-view Lovelace config limited to the selected entities."""
    climate = [entity for entity in entity_ids if entity.startswith("climate.")]
    covers = [entity for entity in entity_ids if entity.startswith("cover.")]
    lights = [entity for entity in entity_ids if entity.startswith("light.")]
    speakers = [entity for entity in entity_ids if entity.startswith("media_player.")]
    others = [
        entity
        for entity in entity_ids
        if entity not in climate
        and entity not in covers
        and entity not in lights
        and entity not in speakers
    ]
    cards: list[dict[str, Any]] = [
        {
            "type": "markdown",
            "content": (
                "Bienvenue. Ce tableau montre uniquement les équipements "
                "autorisés pour le séjour."
            ),
        }
    ]
    for entity_id in climate:
        cards.append({"type": "thermostat", "entity": entity_id})
    if covers:
        cards.append({"type": "entities", "title": "Volets", "entities": covers})
    if lights:
        cards.append({"type": "entities", "title": "Éclairage", "entities": lights})
    if speakers:
        cards.append({"type": "entities", "title": "Son", "entities": speakers})
    if others:
        cards.append({"type": "entities", "title": "Équipements", "entities": others})
    return {
        "views": [
            {
                "type": "sections",
                "title": DASHBOARD_TITLE,
                "path": "sejour",
                "icon": DASHBOARD_ICON,
                "max_columns": 2,
                "sections": [{"type": "grid", "cards": cards}],
            }
        ]
    }


def frontend_core_with_tenant_panel(existing: dict[str, Any] | None) -> dict[str, Any]:
    """User frontend data so login opens Séjour instead of Home."""
    core = dict(existing or {})
    core["default_panel"] = DASHBOARD_URL
    return core


def frontend_sidebar_with_console(
    existing: dict[str, Any] | None, *, hidden: bool
) -> dict[str, Any]:
    """Show or hide the owner Console in a user's sidebar."""
    sidebar = dict(existing or {})
    hidden_panels = [
        str(panel) for panel in (sidebar.get("hiddenPanels") or []) if panel
    ]
    if hidden and OWNER_DASHBOARD_URL not in hidden_panels:
        hidden_panels.append(OWNER_DASHBOARD_URL)
    if not hidden:
        hidden_panels = [panel for panel in hidden_panels if panel != OWNER_DASHBOARD_URL]
    sidebar["hiddenPanels"] = hidden_panels
    return sidebar


async def _async_user_store(
    hass: object,
    user_id: str,
    *,
    load_store: Any | None = None,
):
    loader = load_store
    if loader is None:
        try:
            from homeassistant.components.frontend.storage import (
                async_user_store as loader,
            )
        except ImportError:
            return None
    return await loader(hass, user_id)


async def async_set_tenant_default_panel(
    hass: object,
    user_id: str | None,
    *,
    load_store: Any | None = None,
) -> None:
    """Land a tenant on ``usvegliu-sejour`` after login and hide Console.

    Home Assistant 2026 opens the Home dashboard. That view walks areas and
    can stay on « Chargement des données… » for a user who may only read a
    handful of entities.
    """
    if not user_id:
        return
    try:
        store = await _async_user_store(hass, user_id, load_store=load_store)
        if store is None:
            return
        core = frontend_core_with_tenant_panel(store.data.get("core"))
        sidebar = frontend_sidebar_with_console(store.data.get("sidebar"), hidden=True)
        if store.data.get("core") != core:
            await store.async_set_item("core", core)
        if store.data.get("sidebar") != sidebar:
            await store.async_set_item("sidebar", sidebar)
    except Exception:  # noqa: BLE001 — frontend storage is not worth aborting access
        _LOGGER.debug("Tableau par défaut locataire non enregistré", exc_info=True)


async def async_reveal_owner_console(
    hass: object,
    user_id: str | None,
    *,
    load_store: Any | None = None,
) -> None:
    """Make Console visible in the sidebar for a manager account."""
    if not user_id:
        return
    try:
        store = await _async_user_store(hass, user_id, load_store=load_store)
        if store is None:
            return
        sidebar = frontend_sidebar_with_console(store.data.get("sidebar"), hidden=False)
        if store.data.get("sidebar") != sidebar:
            await store.async_set_item("sidebar", sidebar)
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Barre latérale Console non mise à jour", exc_info=True)


async def async_apply_console_visibility(
    hass: object,
    *,
    load_store: Any | None = None,
    list_users: Any | None = None,
) -> None:
    """Hide Console from tenants; show it to admins and Users."""
    from .access import is_tenant_user, user_can_manage_stays

    users: list[Any] = []
    if callable(list_users):
        users = list(await list_users())
    else:
        auth = getattr(hass, "auth", None)
        getter = getattr(auth, "async_get_users", None) if auth is not None else None
        if not callable(getter):
            return
        try:
            users = list(await getter())
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Liste des utilisateurs indisponible", exc_info=True)
            return
    for user in users:
        if getattr(user, "system_generated", False):
            continue
        user_id = getattr(user, "id", None)
        if not user_id:
            continue
        if is_tenant_user(user):
            await async_set_tenant_default_panel(
                hass, str(user_id), load_store=load_store
            )
        elif user_can_manage_stays(user):
            await async_reveal_owner_console(
                hass, str(user_id), load_store=load_store
            )


def _jinja_quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _service_tap(
    service: str,
    confirm: str,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tap: dict[str, Any] = {
        "action": "call-service",
        "service": f"{DOMAIN}.{service}",
        "service_data": dict(data or {}),
    }
    if confirm:
        tap["confirmation"] = {"text": confirm}
    return tap


def _action_row(
    name: str,
    icon: str,
    service: str,
    confirm: str,
    *,
    reservation_id: str = "",
    extra: dict[str, Any] | None = None,
    action_name: str = "OK",
) -> dict[str, Any]:
    data: dict[str, Any] = dict(extra or {})
    if reservation_id:
        data[ATTR_RESERVATION_KEY] = reservation_id
    return {
        "type": "button",
        "name": name,
        "icon": icon,
        "action_name": action_name,
        "tap_action": _service_tap(service, confirm, data),
    }


def _navigate_row(
    name: str, icon: str, path: str, *, action_name: str = "Ouvrir"
) -> dict[str, Any]:
    return {
        "type": "button",
        "name": name,
        "icon": icon,
        "action_name": action_name,
        "tap_action": {"action": "navigate", "navigation_path": path},
    }


def _entities_actions(title: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "type": "entities",
        "title": title,
        "show_header_toggle": False,
        "state_color": False,
        "entities": rows,
    }


def _stay_markdown(
    entity_id: str,
    reservation_id: str,
    reglages_entity_id: str = "",
    *,
    locale: str = "fr",
) -> str:
    """Live Jinja: secrets stay on the sensor, not in the Lovelace file.

    Guest paste uses ``s.message_invite`` (built per villa brand: Usvegliu
    or 49 Ledbury), never a hardcoded house name.
    """
    from .console_i18n import console_t as t

    entity = _jinja_quote(entity_id)
    key = _jinja_quote(reservation_id)
    attr = _jinja_quote(credential_attribute_key(reservation_id))
    reglages = _jinja_quote(reglages_entity_id) if reglages_entity_id else ""
    settings_line = (
        f"{{% set reglages = state_attr('{reglages}', 'settings') or {{}} %}}\n"
        if reglages
        else "{% set reglages = {} %}\n"
    )
    en = locale == "en"
    back = t(locale, "back_home")
    all_stays = t(locale, "all_stays")
    open_home = t(locale, "open_stay") if en else "Ouvrir la maison"
    msg_title = "Message to send" if en else "Message à envoyer"
    msg_hint = (
        "Select the text, then copy. Maison link and Wi-Fi only — no Home Assistant account."
        if en
        else "Sélectionnez le texte, puis copiez. Lien Maison et Wi-Fi seulement, sans compte Home Assistant."
    )
    ha_account = "Home Assistant account" if en else "Compte Home Assistant"
    username_l = "Username" if en else "Identifiant"
    password_l = "Password" if en else "Mot de passe"
    revoked = "revoked" if en else "révoqué"
    door_l = "Door" if en else "Porte"
    stay_board = "Stay dashboard" if en else "Tableau séjour"
    early = (
        "*HA account and Maison link open on arrival day. Access codes are already in the message.*"
        if en
        else "*Compte HA et lien Maison s'ouvrent le jour d'arrivée. Les codes d'accès sont déjà dans le message.*"
    )
    trial_note = (
        "*24 h trial link — no HA account or Wi-Fi.*"
        if en
        else "*Lien d'essai 24 h — pas de compte HA ni de Wi-Fi.*"
    )
    no_pwd = (
        "Password: *not stored.* Tap **New password** below to show one."
        if en
        else "Mot de passe : *non enregistré.* Touchez **Nouveau mot de passe** ci-dessous pour en afficher un."
    )
    guest_mail = "Guest email" if en else "Mail locataire"
    sent = "sent" if en else "envoyé"
    send_j = "send J−" if en else "envoi J−"
    copy_smtp = (
        " — copy the message (no SMTP service)"
        if en
        else " — copiez le message (aucun service SMTP)"
    )
    no_email = (
        "*No address in the calendar description — copy the message below.*"
        if en
        else "*Pas d'adresse dans la description du calendrier — copiez le message ci-dessous.*"
    )
    no_ssid = (
        "*Network name missing. Set **Wi-Fi network name** in Usvegliu options.*"
        if en
        else "*Nom du réseau manquant. Renseigner **Nom du réseau Wi-Fi** dans les options Usvegliu.*"
    )
    closed = (
        "*Stay closed or not yet provisioned.*"
        if en
        else "*Séjour clos ou pas encore provisionné.*"
    )
    return (
        f"{{% set rows = state_attr('{entity}', 'stays') or [] %}}\n"
        f"{{% set comptes = state_attr('{entity}', 'comptes') or {{}} %}}\n"
        f"{settings_line}"
        f"{{% set found = rows | selectattr('reservation_id', 'equalto', '{key}') | list %}}\n"
        f"{{% set s = found[0] if found else none %}}\n"
        f"{{% set c = comptes.get('{key}') %}}\n"
        f"{{% set plat = state_attr('{entity}', '{attr}') %}}\n"
        "{% set identifiant = (c.identifiant if c else none) or (s.username if s else none) %}\n"
        "{% set mdp = plat or (c.code_compte if c else none) "
        "or (c.mot_de_passe if c else none) "
        "or (s.code_compte if s else none) "
        "or (s.mot_de_passe if s else none) %}\n"
        f"{{% set ssid = ((s.wifi_ssid if s else '') or (s.reseau_wifi if s else '') "
        f"or reglages.wifi_ssid or state_attr('{entity}', 'reseau_wifi') "
        f"or state_attr('{entity}', 'wifi_ssid') "
        f"or reglages.brand_wifi_default or 'Usvegliu-Guest') | trim %}}\n"
        f"[{back}](/{OWNER_DASHBOARD_URL}/console) · "
        f"[{all_stays}](/{OWNER_DASHBOARD_URL}/liste)\n"
        "\n"
        "{% if s %}\n"
        "{% set debut = (s.check_in or '')[:10] %}\n"
        "{% set fin = (s.check_out or '')[:10] %}\n"
        "**{{ debut }} → {{ fin }}**\n"
        "\n"
        "{% if not s.essai and s.acces_actif == False %}\n"
        f"{early}\n"
        "\n"
        "{% endif %}\n"
        "{% if s.essai %}\n"
        f"{trial_note}\n"
        "\n"
        f"{{% if s.lien_maison %}}[{open_home}]({{{{ s.lien_maison }}}}){{% endif %}}\n"
        "{% else %}\n"
        "{% if s.access_revoked %}\n"
        f"**{ha_account}** — *{revoked}*\n"
        "{% else %}\n"
        f"### {ha_account}\n"
        f"{username_l} : `{{{{ identifiant or '—' }}}}`\n"
        "\n"
        "{% if mdp %}\n"
        f"{password_l} :\n"
        "\n"
        "## `{{ mdp }}`\n"
        "{% else %}\n"
        f"{no_pwd}\n"
        "{% endif %}\n"
        "{% endif %}\n"
        "\n"
        "**Wi-Fi** : "
        "{% if ssid %}{{ ssid }} · {% endif %}"
        f"{{% if s.voucher_revoked %}}*{revoked}*\n"
        "{% else %}`{{ s.voucher_code or '—' }}`\n"
        "{% endif %}\n"
        "\n"
        f"**{door_l}** : "
        f"{{% if s.nuki_revoked %}}*{revoked}*\n"
        "{% elif s.nuki_code %}`{{ s.nuki_code }}`\n"
        "{% else %}—\n"
        "{% endif %}\n"
        "\n"
        "{% if s.lien_maison %}[Maison]({{ s.lien_maison }}){% endif %}"
        f" · [{stay_board}](/"
        f"{DASHBOARD_URL})\n"
        "{% endif %}\n"
        "\n"
        f"### {msg_title}\n"
        f"{msg_hint}\n"
        "{% if not s.essai %}\n"
        "{% if s.guest_email %}\n"
        f"{guest_mail} : `{{{{ s.guest_email }}}}`"
        "{% if reglages.guest_mail_service %}"
        f"{{% if s.welcome_mail_sent %}} — {sent}"
        f"{{% else %}} — {send_j}{{{{ reglages.guest_mail_days or 2 }}}}"
        "{% endif %}\n"
        f"{{% else %}}{copy_smtp}\n"
        "{% endif %}\n"
        "{% else %}\n"
        f"{no_email}\n"
        "{% endif %}\n"
        "{% endif %}\n"
        "{% if not s.essai and not ssid %}\n"
        "\n"
        f"{no_ssid}\n"
        "{% endif %}\n"
        "\n"
        "```\n"
        "{{ s.message_invite }}\n"
        "```\n"
        "{% else %}\n"
        f"{closed}\n"
        "{% endif %}\n"
    )


def _settings_markdown(entity_id: str) -> str:
    """Live Jinja from the settings sensor — no secrets in Lovelace."""
    entity = _jinja_quote(entity_id)
    return (
        f"{{% set a = state_attr('{entity}', 'settings') or {{}} %}}\n"
        "### Calendrier\n"
        "- Réservations : `{{ a.calendar or '—' }}`\n"
        "- Avant arrivée : **{{ a.lead_days }}** j · après séjour : "
        "**{{ a.extra_days }}** j\n"
        "- Horizon : **{{ a.lookahead_days }}** j · durée max : "
        "**{{ a.max_stay_days }}** j\n"
        "- Titres ignorés : `{{ a.title_blocklist or '—' }}`\n"
        "\n"
        "### Accès locataire\n"
        "- Comptes HA : **{{ 'oui' if a.enable_access else 'non' }}** "
        "({{ a.access_mode_label or '—' }})\n"
        "- Vouchers Wi-Fi ({{ a.voucher_provider or 'unifi' }}) : "
        "**{{ 'oui' if a.enable_vouchers else 'non' }}**\n"
        "- Code PIN Nuki : **{{ 'oui' if a.enable_nuki else 'non' }}**"
        "{% if a.enable_nuki and not a.nuki_configured %} "
        "· jeton manquant, mail sans PIN{% endif %}"
        "{% if not a.enable_nuki %} "
        "· mail sans code porte{% endif %}\n"
        "- Internet pendant le séjour : "
        "**{{ 'oui' if a.allow_remote else 'non' }}**\n"
        "- Entités : **{{ a.tenant_entity_count }}** · appareils : "
        "**{{ a.tenant_device_count }}**\n"
        "\n"
        "### Wi-Fi\n"
        "- Réseau : `{{ a.wifi_ssid or '—' }}`\n"
        "- Appareils / voucher : **{{ a.device_limit }}**\n"
        "- Débit : **{{ a.download_mbps }}** / **{{ a.upload_mbps }}** Mbit/s\n"
        "\n"
        "### Maison\n"
        "- Site : `{{ a.site or a.host or '—' }}`\n"
        "- Mode démo web app : **{{ 'oui' if a.demo_mode else 'non' }}**\n"
        "- Chauffage / clim : `{{ a.house_mode_entity or 'non configuré' }}`\n"
        "- Extérieur : `{{ a.outdoor_temperature or '—' }}`\n"
        "- Piscine : `{{ a.pool_temperature or '—' }}` · "
        "pH : `{{ a.pool_ph or '—' }}`\n"
        "- Code alarme enregistré : "
        "**{{ 'oui' if a.alarm_configured else 'non' }}**\n"
        "\n"
        "### Journal\n"
        "- Fichier : `{{ a.journal_path or '—' }}`\n"
        "- Notification : `{{ a.notify_service or 'persistante seulement' }}`\n"
        "- Mail locataire : `{{ a.guest_mail_service or 'désactivé' }}` "
        "(J−{{ a.guest_mail_days }})\n"
        "- Impression auto : **{{ 'oui' if a.print_event else 'non' }}**\n"
        "- URL web app : `{{ a.guest_base_url or 'interne HA' }}`\n"
        "- Thème : `{{ a.guest_theme or 'usvegliu' }}` · "
        "Langue : `{{ a.guest_locale or 'fr' }}`\n"
    )


def _featured_markdown(
    entity_id: str, role: str, empty: str, *, open_label: str, trial_badge: str
) -> str:
    """Live card for the current or next stay. No secrets."""
    entity = _jinja_quote(entity_id)
    role_q = _jinja_quote(role)
    open_q = _jinja_quote(open_label)
    trial_q = _jinja_quote(trial_badge)
    return (
        f"{{% set rows = state_attr('{entity}', 'stays') or [] %}}\n"
        f"{{% set found = rows | selectattr('role', 'equalto', '{role_q}') | list %}}\n"
        "{% set s = found[0] if found else none %}\n"
        "{% if s %}\n"
        "## {{ s.guest }}\n"
        "\n"
        "{% if s.sejour_libelle %}{{ s.sejour_libelle }}"
        "{% else %}{{ (s.check_in or '')[:10] }} → {{ (s.check_out or '')[:10] }}"
        "{% endif %}\n"
        "\n"
        "**{{ s.role_label }}**"
        f"{{% if s.essai %}} · {trial_q}{{% endif %}}\n"
        "\n"
        f"[{open_q}](/{OWNER_DASHBOARD_URL}/{{{{ s.vue }}}})\n"
        "{% else %}\n"
        f"*{empty}*\n"
        "{% endif %}\n"
    )


def _roster_markdown(entity_id: str, *, locale: str = "fr") -> str:
    """Ordered clickable stay list. Secrets stay on the detail subview."""
    from .console_i18n import console_t as t

    entity = _jinja_quote(entity_id)
    link = f"/{OWNER_DASHBOARD_URL}/{{{{ s.vue }}}}"
    group = (
        "{% if group %}\n"
        "\n### {{ titre }}\n"
        "{% for s in group %}\n"
        f"- [**{{{{ s.guest }}}}**]({link}) · "
        "{{ (s.check_in or '')[:10] }} → {{ (s.check_out or '')[:10] }}"
        "{% if s.role_label %} · {{ s.role_label }}{% endif %}\n"
        "{% endfor %}\n"
        "{% endif %}\n"
    )
    return (
        f"{{% set rows = state_attr('{entity}', 'stays') or [] %}}\n"
        f"{t(locale, 'roster_intro')}\n"
        "{% if not rows %}\n"
        f"\n{t(locale, 'no_open_stays')}\n"
        "{% endif %}\n"
        "{% set group = rows | selectattr('role', 'equalto', 'current') | list %}\n"
        f"{{% set titre = '{t(locale, 'current')}' %}}\n"
        f"{group}"
        "{% set group = rows | selectattr('role', 'equalto', 'upcoming') | list %}\n"
        f"{{% set titre = '{t(locale, 'upcoming')}' %}}\n"
        f"{group}"
        "{% set group = rows | selectattr('role', 'equalto', 'departing') | list %}\n"
        f"{{% set titre = '{t(locale, 'wifi_still_active')}' %}}\n"
        f"{group}"
        "{% set group = rows | selectattr('role', 'equalto', 'preview') | list %}\n"
        f"{{% set titre = '{t(locale, 'trial')}' %}}\n"
        f"{group}"
    )


def _history_markdown(entity_id: str, *, locale: str = "fr") -> str:
    """Closed stays and journal actions. No voucher codes."""
    from .console_i18n import console_t as t

    entity = _jinja_quote(entity_id)
    return (
        f"{{% set hist = state_attr('{entity}', 'historique') or [] %}}\n"
        f"{{% set journal = state_attr('{entity}', 'journal') or [] %}}\n"
        f"{t(locale, 'history_intro')}\n"
        "\n"
        f"### {t(locale, 'past_stays')}\n"
        "{% if hist %}\n"
        "{% for h in hist | reverse %}\n"
        "- **{{ h.guest }}** · {{ (h.check_in or '')[:10] }} → "
        "{{ (h.check_out or '')[:10] }}\n"
        "{% endfor %}\n"
        "{% else %}\n"
        f"{t(locale, 'no_past')}\n"
        "{% endif %}\n"
        "\n"
        f"### {t(locale, 'access')}\n"
        "{% if journal %}\n"
        "{% for j in journal %}\n"
        "- `{{ j.horodatage }}` · **{{ j.libelle or j.action }}**"
        "{% if j.locataire %} · {{ j.locataire }}{% endif %}"
        "{% if j.debut %} · {{ j.debut }} → {{ j.fin }}{% endif %}\n"
        "{% endfor %}\n"
        "{% else %}\n"
        f"{t(locale, 'no_events')}\n"
        "{% endif %}\n"
    )


def _heading(text: str, icon: str, *, subtitle: bool = False) -> dict[str, Any]:
    return {
        "type": "heading",
        "heading": text,
        "heading_style": "subtitle" if subtitle else "title",
        "icon": icon,
    }


def _tile(entity_id: str, name: str, icon: str) -> dict[str, Any]:
    return {
        "type": "tile",
        "entity": entity_id,
        "name": name,
        "icon": icon,
        "vertical": False,
    }


def _stay_action_rows(
    guest: str, reservation_id: str, *, locale: str = "fr"
) -> list[dict[str, Any]]:
    from .console_i18n import console_t as t

    return [
        _action_row(
            t(locale, "new_password"),
            "mdi:account-key",
            SERVICE_REGENERATE_ACCESS,
            t(locale, "new_password_confirm", guest=guest),
            reservation_id=reservation_id,
            action_name=t(locale, "generate"),
        ),
        _action_row(
            t(locale, "revoke_ha"),
            "mdi:account-off",
            SERVICE_REVOKE_ACCESS,
            t(locale, "revoke_ha_confirm", guest=guest),
            reservation_id=reservation_id,
            action_name=t(locale, "revoke"),
        ),
        _action_row(
            t(locale, "new_wifi"),
            "mdi:wifi-sync",
            SERVICE_REGENERATE_VOUCHER,
            t(locale, "new_wifi_confirm", guest=guest),
            reservation_id=reservation_id,
            action_name=t(locale, "generate"),
        ),
        _action_row(
            t(locale, "revoke_wifi"),
            "mdi:wifi-off",
            SERVICE_REVOKE_VOUCHER,
            t(locale, "revoke_wifi_confirm", guest=guest),
            reservation_id=reservation_id,
            action_name=t(locale, "revoke"),
        ),
        _action_row(
            t(locale, "new_door"),
            "mdi:dialpad",
            SERVICE_REGENERATE_NUKI,
            t(locale, "new_door_confirm", guest=guest),
            reservation_id=reservation_id,
            action_name=t(locale, "generate"),
        ),
        _action_row(
            t(locale, "revoke_door"),
            "mdi:lock-off",
            SERVICE_REVOKE_NUKI,
            t(locale, "revoke_door_confirm", guest=guest),
            reservation_id=reservation_id,
            action_name=t(locale, "revoke"),
        ),
        _action_row(
            t(locale, "resend"),
            "mdi:bell-ring",
            SERVICE_RESEND,
            t(locale, "resend_confirm", guest=guest),
            reservation_id=reservation_id,
            action_name=t(locale, "send"),
        ),
        _action_row(
            t(locale, "print_voucher"),
            "mdi:printer",
            SERVICE_PRINT,
            t(locale, "print_confirm", guest=guest),
            reservation_id=reservation_id,
            action_name=t(locale, "print"),
        ),
    ]


def _tools_card(locale: str = "fr") -> dict[str, Any]:
    from .console_i18n import console_t as t

    return _entities_actions(
        t(locale, "tools"),
        [
            _action_row(
                t(locale, "reread_calendar"),
                "mdi:calendar-refresh",
                SERVICE_REFRESH_CALENDAR,
                t(locale, "reread_calendar_confirm"),
                action_name=t(locale, "read"),
            ),
            _action_row(
                t(locale, "refresh_dashboards"),
                "mdi:view-dashboard-edit",
                SERVICE_APPLY_DASHBOARD,
                t(locale, "refresh_dashboards_confirm"),
                action_name=t(locale, "apply"),
            ),
            _action_row(
                t(locale, "trial_link"),
                "mdi:link-plus",
                SERVICE_GUEST_LINK,
                t(locale, "trial_link_confirm"),
                extra={"essai": True},
                action_name=t(locale, "create"),
            ),
            _action_row(
                t(locale, "export_journal"),
                "mdi:file-download-outline",
                SERVICE_EXPORT_JOURNAL,
                "",
                action_name=t(locale, "path"),
            ),
            {
                "type": "button",
                "name": t(locale, "edit_settings"),
                "icon": "mdi:cog",
                "action_name": t(locale, "open"),
                "tap_action": {
                    "action": "navigate",
                    "navigation_path": "/config/integrations/integration/usvegliu",
                },
            },
        ],
    )


def _home_tools_card(locale: str = "fr") -> dict[str, Any]:
    from .console_i18n import console_t as t

    return _entities_actions(
        t(locale, "shortcuts"),
        [
            _action_row(
                t(locale, "reread_calendar"),
                "mdi:calendar-refresh",
                SERVICE_REFRESH_CALENDAR,
                t(locale, "reread_calendar_confirm"),
                action_name=t(locale, "read"),
            ),
            _action_row(
                t(locale, "trial_link"),
                "mdi:link-plus",
                SERVICE_GUEST_LINK,
                t(locale, "trial_link_confirm"),
                extra={"essai": True},
                action_name=t(locale, "create"),
            ),
            _navigate_row(
                t(locale, "all_stays"),
                "mdi:format-list-bulleted",
                f"/{OWNER_DASHBOARD_URL}/liste",
                action_name=t(locale, "open"),
            ),
            _navigate_row(
                t(locale, "history"),
                "mdi:history",
                f"/{OWNER_DASHBOARD_URL}/historique",
                action_name=t(locale, "open"),
            ),
            _navigate_row(
                t(locale, "settings"),
                "mdi:tune",
                f"/{OWNER_DASHBOARD_URL}/reglages",
                action_name=t(locale, "open"),
            ),
        ],
    )


def _home_view_sections(
    *,
    sejours_entity_id: str,
    voucher_entity_id: str,
    house_mode_entity: str | None,
    locale: str = "fr",
) -> list[dict[str, Any]]:
    from .console_i18n import console_t as t

    status: list[dict[str, Any]] = [
        _heading(t(locale, "console"), "mdi:desk"),
        {
            "type": "markdown",
            "content": t(locale, "console_intro"),
        },
    ]
    tiles: list[dict[str, Any]] = []
    if sejours_entity_id:
        tiles.append(
            _tile(sejours_entity_id, t(locale, "open_stays"), "mdi:account-group")
        )
    if voucher_entity_id:
        tiles.append(
            _tile(voucher_entity_id, t(locale, "current_wifi"), "mdi:wifi")
        )
    if house_mode_entity:
        tiles.append(
            _tile(house_mode_entity, t(locale, "heat_cool"), "mdi:sun-snowflake")
        )
    if tiles:
        status.extend(tiles)
    status.append(_home_tools_card(locale))
    sections: list[dict[str, Any]] = [
        {"type": "grid", "column_span": 2, "cards": status}
    ]
    if sejours_entity_id:
        sections.append(
            {
                "type": "grid",
                "cards": [
                    _heading(t(locale, "current"), "mdi:home-account", subtitle=True),
                    {
                        "type": "markdown",
                        "content": _featured_markdown(
                            sejours_entity_id,
                            "current",
                            t(locale, "no_current"),
                            open_label=t(locale, "open_stay"),
                            trial_badge=t(locale, "trial_badge"),
                        ),
                    },
                ],
            }
        )
        sections.append(
            {
                "type": "grid",
                "cards": [
                    _heading(
                        t(locale, "next"), "mdi:calendar-arrow-right", subtitle=True
                    ),
                    {
                        "type": "markdown",
                        "content": _featured_markdown(
                            sejours_entity_id,
                            "upcoming",
                            t(locale, "no_next"),
                            open_label=t(locale, "open_stay"),
                            trial_badge=t(locale, "trial_badge"),
                        ),
                    },
                ],
            }
        )
    return sections


def _liste_view_sections(
    *, sejours_entity_id: str, locale: str = "fr"
) -> list[dict[str, Any]]:
    from .console_i18n import console_t as t

    return [
        {
            "type": "grid",
            "column_span": 2,
            "cards": [
                _heading(t(locale, "stays"), "mdi:format-list-bulleted"),
                {
                    "type": "markdown",
                    "content": _roster_markdown(sejours_entity_id, locale=locale)
                    if sejours_entity_id
                    else t(locale, "sensor_missing"),
                },
            ],
        }
    ]


def _history_view_sections(
    *, sejours_entity_id: str, locale: str = "fr"
) -> list[dict[str, Any]]:
    from .console_i18n import console_t as t

    cards: list[dict[str, Any]] = [
        _heading(t(locale, "history"), "mdi:history"),
        {
            "type": "markdown",
            "content": _history_markdown(sejours_entity_id, locale=locale)
            if sejours_entity_id
            else t(locale, "sensor_missing"),
        },
        _entities_actions(
            t(locale, "journal"),
            [
                _action_row(
                    t(locale, "export_journal"),
                    "mdi:file-download-outline",
                    SERVICE_EXPORT_JOURNAL,
                    "",
                    action_name=t(locale, "path"),
                )
            ],
        ),
    ]
    return [{"type": "grid", "column_span": 2, "cards": cards}]


def _stay_subview(
    stay: dict[str, Any],
    *,
    sejours_entity_id: str,
    reglages_entity_id: str,
    locale: str = "fr",
) -> dict[str, Any]:
    from .console_i18n import console_t as t

    reservation_id = str(stay.get("reservation_id") or stay.get("key") or "")
    guest = str(stay.get("guest") or t(locale, "stay"))
    path = str(stay.get("vue") or stay_view_path(reservation_id))
    cards: list[dict[str, Any]] = [
        _heading(guest, "mdi:home-account"),
        {
            "type": "markdown",
            "content": _stay_markdown(
                sejours_entity_id,
                reservation_id,
                reglages_entity_id,
                locale=locale,
            ),
        },
    ]
    if (
        sejours_entity_id
        and reservation_id
        and not stay.get("essai")
        and not stay.get("access_revoked")
    ):
        cards.append(
            {
                "type": "entity",
                "entity": sejours_entity_id,
                "attribute": credential_attribute_key(reservation_id),
                "name": (
                    "Home Assistant password"
                    if locale == "en"
                    else "Mot de passe Home Assistant"
                ),
                "icon": "mdi:form-textbox-password",
                "state_color": False,
            }
        )
    if not stay.get("essai") and reservation_id:
        cards.append(
            _entities_actions(
                "Actions",
                _stay_action_rows(guest, reservation_id, locale=locale),
            )
        )
    return {
        "type": "sections",
        "title": guest,
        "path": path,
        "icon": "mdi:home-account",
        "subview": True,
        "max_columns": 1,
        "sections": [{"type": "grid", "column_span": 2, "cards": cards}],
    }


def _settings_view_sections(
    *,
    reglages_entity_id: str,
    house_mode_entity: str | None,
    outdoor_entity: str | None,
    pool_temp_entity: str | None,
    pool_ph_entity: str | None,
    tenant_entities: list[str],
    locale: str = "fr",
) -> list[dict[str, Any]]:
    from .console_i18n import console_t as t

    overview: list[dict[str, Any]] = [
        _heading(t(locale, "settings_usvegliu"), "mdi:tune"),
        {
            "type": "markdown",
            "content": (
                "Live values. To change them: **Edit settings**. "
                "API key and alarm code are not shown."
                if locale == "en"
                else "Valeurs en vigueur. Pour les changer : **Modifier les réglages**. "
                "La clé API et le code alarme ne sont pas affichés."
            ),
        },
    ]
    if reglages_entity_id:
        overview.append(
            {
                "type": "markdown",
                "content": _settings_markdown(reglages_entity_id),
            }
        )
    overview.append(_tools_card(locale))
    sections: list[dict[str, Any]] = [
        {"type": "grid", "column_span": 2, "cards": overview}
    ]
    house_tiles = [
        _tile(entity, name, icon)
        for entity, name, icon in (
            (house_mode_entity, t(locale, "heat_cool"), "mdi:sun-snowflake"),
            (
                outdoor_entity,
                "Outdoor temperature" if locale == "en" else "Température extérieure",
                "mdi:thermometer",
            ),
            (
                pool_temp_entity,
                "Pool temperature" if locale == "en" else "Température piscine",
                "mdi:pool-thermometer",
            ),
            (
                pool_ph_entity,
                "Pool pH" if locale == "en" else "pH piscine",
                "mdi:ph",
            ),
        )
        if entity
    ]
    if house_tiles:
        sections.append(
            {
                "type": "grid",
                "column_span": 2,
                "cards": [
                    _heading(
                        "House" if locale == "en" else "Maison",
                        "mdi:home-thermometer",
                        subtitle=True,
                    ),
                    *house_tiles,
                ],
            }
        )
    if tenant_entities:
        sections.append(
            {
                "type": "grid",
                "column_span": 2,
                "cards": [
                    _heading(
                        "Guest equipment" if locale == "en" else "Équipements locataire",
                        "mdi:dots-grid",
                        subtitle=True,
                    ),
                    {
                        "type": "entities",
                        "title": (
                            "Allowed for stays"
                            if locale == "en"
                            else "Autorisés pour les séjours"
                        ),
                        "show_header_toggle": False,
                        "entities": tenant_entities[:24],
                    },
                ],
            }
        )
    return sections


def build_owner_dashboard_config(
    stays: list[dict[str, Any]],
    *,
    sejours_entity_id: str,
    reglages_entity_id: str = "",
    voucher_entity_id: str = "",
    house_mode_entity: str | None = None,
    outdoor_entity: str | None = None,
    pool_temp_entity: str | None = None,
    pool_ph_entity: str | None = None,
    tenant_entities: list[str] | None = None,
    locale: str = "fr",
) -> dict[str, Any]:
    """Owner console: current + next, clickable stays, history, settings."""
    from .console_i18n import console_t as t

    views: list[dict[str, Any]] = [
        {
            "type": "sections",
            "title": t(locale, "home"),
            "path": "console",
            "icon": "mdi:desk",
            "max_columns": 2,
            "sections": _home_view_sections(
                sejours_entity_id=sejours_entity_id,
                voucher_entity_id=voucher_entity_id,
                house_mode_entity=house_mode_entity,
                locale=locale,
            ),
        },
        {
            "type": "sections",
            "title": t(locale, "stays"),
            "path": "liste",
            "icon": "mdi:format-list-bulleted",
            "max_columns": 1,
            "sections": _liste_view_sections(
                sejours_entity_id=sejours_entity_id, locale=locale
            ),
        },
        {
            "type": "sections",
            "title": t(locale, "history"),
            "path": "historique",
            "icon": "mdi:history",
            "max_columns": 1,
            "sections": _history_view_sections(
                sejours_entity_id=sejours_entity_id, locale=locale
            ),
        },
        {
            "type": "sections",
            "title": t(locale, "settings"),
            "path": "reglages",
            "icon": "mdi:tune",
            "max_columns": 2,
            "sections": _settings_view_sections(
                reglages_entity_id=reglages_entity_id,
                house_mode_entity=house_mode_entity,
                outdoor_entity=outdoor_entity,
                pool_temp_entity=pool_temp_entity,
                pool_ph_entity=pool_ph_entity,
                tenant_entities=list(tenant_entities or []),
                locale=locale,
            ),
        },
    ]
    for stay in stays:
        if stay.get("reservation_id") or stay.get("key"):
            views.append(
                _stay_subview(
                    stay,
                    sejours_entity_id=sejours_entity_id,
                    reglages_entity_id=reglages_entity_id,
                    locale=locale,
                )
            )
    return {"views": views}


def dashboard_card_count(config: dict[str, Any]) -> int:
    """How many cards the config will show, across every view."""
    total = 0
    for view in config.get("views") or []:
        cards = list(view.get("cards") or [])
        for section in view.get("sections") or []:
            cards.extend(section.get("cards") or [])
        total += len(cards)
    return total


def _lovelace_bundle(hass: object) -> Any:
    data = getattr(hass, "data", None)
    if data is None:
        return None
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA

        bundle = data.get(LOVELACE_DATA)
        if bundle is not None:
            return bundle
    except Exception:  # noqa: BLE001 — HA is optional in unit tests
        pass
    getter = getattr(data, "get", None)
    if callable(getter):
        return getter("lovelace")
    return None


def _dashboard_map(hass: object) -> dict[Any, Any]:
    bundle = _lovelace_bundle(hass)
    if bundle is None:
        return {}
    dashboards = getattr(bundle, "dashboards", None)
    if isinstance(dashboards, dict):
        return dashboards
    if isinstance(bundle, dict):
        inner = bundle.get("dashboards")
        if isinstance(inner, dict):
            return inner
    return {}


def _dashboard_url_path(dashboard: object) -> str | None:
    path = getattr(dashboard, "url_path", None)
    if isinstance(path, str) and path:
        return path
    config = getattr(dashboard, "config", None)
    if isinstance(config, dict):
        value = config.get("url_path")
        if isinstance(value, str) and value:
            return value
    return None


def _find_dashboard(dashboards: dict[Any, Any], url: str) -> Any | None:
    """Match a live Lovelace dashboard by URL, even if the dict key differs."""
    found = dashboards.get(url)
    if found is not None:
        return found
    for key, dashboard in dashboards.items():
        if key == url or str(key) == url:
            return dashboard
        if _dashboard_url_path(dashboard) == url:
            return dashboard
    return None


def _websocket_command_maps(hass: object) -> list[dict[Any, Any]]:
    data = getattr(hass, "data", None)
    if data is None:
        return []
    maps: list[dict[Any, Any]] = []
    seen: set[int] = set()

    def _add(candidate: object) -> None:
        if not isinstance(candidate, dict) or id(candidate) in seen:
            return
        if not any(str(key).startswith("lovelace/dashboards") for key in candidate):
            return
        seen.add(id(candidate))
        maps.append(candidate)

    getter = getattr(data, "get", None)
    raw = getter("websocket_api") if callable(getter) else None
    try:
        from homeassistant.components.websocket_api import DOMAIN as WS_DOMAIN

        keyed = getter(WS_DOMAIN) if callable(getter) else None
        _add(keyed)
        _add(getattr(keyed, "commands", None))
        _add(getattr(keyed, "handlers", None))
    except Exception:  # noqa: BLE001 — HA is optional in unit tests
        pass
    _add(raw)
    _add(getattr(raw, "commands", None))
    _add(getattr(raw, "handlers", None))
    values = getattr(data, "values", None)
    if callable(values):
        for value in list(values()):
            _add(value)
            _add(getattr(value, "commands", None))
            _add(getattr(value, "handlers", None))
    return maps


def _bound_owner(entry: object) -> Any:
    fn: Any = entry[0] if isinstance(entry, (tuple, list)) and entry else entry
    nested = getattr(fn, "func", None)
    if callable(nested):
        fn = nested
    return getattr(fn, "__self__", None)


def _is_dashboard_collection(obj: object) -> bool:
    if obj is None or not callable(getattr(obj, "async_create_item", None)):
        return False
    name = type(obj).__name__
    if name == "DashboardsCollection":
        return True
    items_fn = getattr(obj, "async_items", None)
    if not callable(items_fn):
        return False
    try:
        items = list(items_fn() or [])
    except Exception:  # noqa: BLE001
        return "dashboard" in name.lower()
    return any(isinstance(item, dict) and "url_path" in item for item in items) or (
        "dashboard" in name.lower()
    )


def find_dashboard_collection(hass: object):
    """Return the live Lovelace dashboard collection, or None."""
    for commands in _websocket_command_maps(hass):
        for key, entry in commands.items():
            if not str(key).startswith("lovelace/dashboards"):
                continue
            owner = _bound_owner(entry)
            collection = getattr(owner, "storage_collection", None)
            if callable(getattr(collection, "async_create_item", None)):
                return collection
            if callable(getattr(owner, "async_create_item", None)):
                return owner
    bundle = _lovelace_bundle(hass)
    for name in ("dashboards_collection", "storage_collection"):
        collection = getattr(bundle, name, None)
        if _is_dashboard_collection(collection):
            return collection
    data = getattr(hass, "data", None)
    values = getattr(data, "values", None) if data is not None else None
    if callable(values):
        for value in list(values()):
            if _is_dashboard_collection(value):
                return value
            nested = getattr(value, "storage_collection", None)
            if _is_dashboard_collection(nested):
                return nested
    return None


def _collection_item_for_url(collection: object, url: str) -> dict[str, Any] | None:
    items_fn = getattr(collection, "async_items", None)
    for item in items_fn() if callable(items_fn) else []:
        if isinstance(item, dict) and item.get("url_path") == url:
            return item
    return None


async def _async_attach_storage_dashboard(
    hass: object,
    *,
    url: str,
    title: str,
    icon: str,
    require_admin: bool,
) -> Any | None:
    """Register a storage dashboard when the Lovelace collection is unreachable."""
    dashboards = _dashboard_map(hass)
    found = _find_dashboard(dashboards, url)
    if found is not None:
        return found
    try:
        from homeassistant.components import frontend
        from homeassistant.components.lovelace.dashboard import LovelaceStorage
    except Exception:  # noqa: BLE001 — unit tests have no Home Assistant
        return None
    item = {
        "id": url,
        "url_path": url,
        "title": title,
        "icon": icon,
        "require_admin": require_admin,
        "show_in_sidebar": True,
        "mode": "storage",
    }
    try:
        storage = LovelaceStorage(hass, item)
    except Exception:  # noqa: BLE001
        _LOGGER.debug("LovelaceStorage indisponible pour %s", url, exc_info=True)
        return None
    dashboards[url] = storage
    try:
        frontend.async_register_built_in_panel(
            hass,
            "lovelace",
            frontend_url_path=url,
            require_admin=require_admin,
            show_in_sidebar=True,
            sidebar_title=title,
            sidebar_icon=icon,
            config={"mode": "storage"},
        )
    except Exception:  # noqa: BLE001 — panel may already exist
        _LOGGER.debug("Panneau %s non enregistré", url, exc_info=True)
    return storage


async def _async_save_named_dashboard(
    hass: object,
    *,
    url: str,
    title: str,
    icon: str,
    require_admin: bool,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Create a Lovelace storage dashboard if needed and save its cards."""
    cards = dashboard_card_count(config)
    dashboards = _dashboard_map(hass)
    dashboard = _find_dashboard(dashboards, url)
    collection = find_dashboard_collection(hass)

    if collection is not None:
        existing = _collection_item_for_url(collection, url)
        if existing is None and dashboard is None:
            try:
                await collection.async_create_item(
                    {
                        "url_path": url,
                        "title": title,
                        "icon": icon,
                        "require_admin": require_admin,
                        "show_in_sidebar": True,
                        "mode": "storage",
                    }
                )
            except Exception:  # noqa: BLE001 — already exists or API drift
                _LOGGER.debug("Création du tableau %s ignorée", url, exc_info=True)
        elif existing is not None and (
            bool(existing.get("require_admin")) != bool(require_admin)
            or not existing.get("show_in_sidebar", True)
        ):
            try:
                await collection.async_update_item(
                    existing["id"],
                    {
                        "require_admin": require_admin,
                        "show_in_sidebar": True,
                    },
                )
            except Exception:  # noqa: BLE001
                _LOGGER.debug("Mise à jour du tableau %s ignorée", url, exc_info=True)
        dashboards = _dashboard_map(hass)
        dashboard = _find_dashboard(dashboards, url) or dashboard

    if dashboard is None:
        dashboard = await _async_attach_storage_dashboard(
            hass,
            url=url,
            title=title,
            icon=icon,
            require_admin=require_admin,
        )

    if dashboard is None:
        known = ", ".join(str(key) for key in _dashboard_map(hass) if key) or "aucun"
        _LOGGER.warning(
            "Tableau %s introuvable : cartes non écrites (présents : %s)",
            url,
            known,
        )
        return {"ok": False, "url": url, "cards": cards, "reason": "dashboard_missing"}

    saver = getattr(dashboard, "async_save", None)
    if not callable(saver):
        return {"ok": False, "url": url, "cards": cards, "reason": "save_unavailable"}
    await saver(config)
    return {"ok": True, "url": url, "cards": cards, "reason": "saved"}


async def async_ensure_dashboard(hass: object, entity_ids: list[str]) -> dict[str, Any]:
    """Create ``usvegliu-sejour`` if needed and save its cards."""
    config = build_dashboard_config(entity_ids)
    result = await _async_save_named_dashboard(
        hass,
        url=DASHBOARD_URL,
        title=DASHBOARD_TITLE,
        icon=DASHBOARD_ICON,
        require_admin=False,
        config=config,
    )
    result["entities"] = list(entity_ids)
    return result


async def async_ensure_owner_dashboard(
    hass: object,
    stays: list[dict[str, Any]],
    *,
    sejours_entity_id: str,
    reglages_entity_id: str = "",
    voucher_entity_id: str = "",
    house_mode_entity: str | None = None,
    outdoor_entity: str | None = None,
    pool_temp_entity: str | None = None,
    pool_ph_entity: str | None = None,
    tenant_entities: list[str] | None = None,
    locale: str = "fr",
) -> dict[str, Any]:
    """Create the owner console dashboard and save its cards."""
    config = build_owner_dashboard_config(
        stays,
        sejours_entity_id=sejours_entity_id,
        reglages_entity_id=reglages_entity_id,
        voucher_entity_id=voucher_entity_id,
        house_mode_entity=house_mode_entity,
        outdoor_entity=outdoor_entity,
        pool_temp_entity=pool_temp_entity,
        pool_ph_entity=pool_ph_entity,
        tenant_entities=tenant_entities,
        locale=locale,
    )
    result = await _async_save_named_dashboard(
        hass,
        url=OWNER_DASHBOARD_URL,
        title=OWNER_DASHBOARD_TITLE,
        icon=OWNER_DASHBOARD_ICON,
        require_admin=False,
        config=config,
    )
    try:
        await async_apply_console_visibility(hass)
    except Exception:  # noqa: BLE001 — sidebar prefs must not block the cards
        _LOGGER.debug("Visibilité Console non appliquée", exc_info=True)
    return result
