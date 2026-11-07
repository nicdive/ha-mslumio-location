(function () {
  const root = document.getElementById("app");
  const token = readToken();
  function readScreen() {
    const tab = new URLSearchParams(window.location.search).get("tab");
    if (
      tab === "climate" ||
      tab === "lights" ||
      tab === "access" ||
      tab === "info" ||
      tab === "pool" ||
      tab === "sound"
    ) {
      return tab;
    }
    return "home";
  }

  let state = null;
  let screen = readScreen();
  let listMode = "reglage";
  let roomId = null;
  let error = "";
  let arrivalNote = "";

  function readToken() {
    const path = window.location.pathname.replace(/\/+$/, "");
    const parts = path.split("/").filter(Boolean);
    const idx = parts.lastIndexOf("s");
    if (idx >= 0 && parts[idx + 1]) return parts[idx + 1];
    return new URLSearchParams(window.location.search).get("token") || "";
  }

  function api(path, options) {
    return fetch(path, {
      ...options,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-Usvegliu-Token": token,
        ...(options && options.headers),
      },
    }).then(async (res) => {
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        const err = new Error(body.error || "error");
        err.status = res.status;
        err.opensOn = body.opens_on || "";
        throw err;
      }
      return body;
    });
  }

  function formatTemp(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
    const n = Number(value);
    return n % 1 === 0 ? String(n) : n.toFixed(1);
  }

  function icon(kind) {
    const icons = {
      home: '<path d="M4 11.2 L12 4.4 L20 11.2 V20 H14.4 V14.2 H9.6 V20 H4 Z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/>',
      climate:
        '<path d="M12 3.6 V8.2" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/><circle cx="12" cy="14.4" r="4.4" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M12 8.2 V10" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>',
      lights:
        '<path d="M12 3.6 a6 6 0 0 1 3.4 10.9 V16.6 H8.6 V14.5 A6 6 0 0 1 12 3.6 Z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/><path d="M9.4 19.2 H14.6" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>',
      access:
        '<circle cx="9.2" cy="12" r="3.4" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M12.4 12 H20 V14.6 H17.4 V17" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>',
      info: '<path d="M4.6 16.6 L7.2 9.2 H9.8 L7.2 16.6 Z M12.2 7.4 H19.4 M12.2 12 H19.4 M12.2 16.6 H17.2" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>',
      pool: '<path d="M4 16.6 C6.2 14.8 8.4 14.8 10.6 16.6 C12.8 18.4 15 18.4 17.2 16.6 C18.2 15.8 19.2 15.6 20 15.8" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/><path d="M4 12.4 C6.2 10.6 8.4 10.6 10.6 12.4 C12.8 14.2 15 14.2 17.2 12.4 C18.2 11.6 19.2 11.4 20 11.6" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/><path d="M8.4 7.2 C9.2 5.6 10.6 5 12 5.8 C13.4 6.6 13.8 8.2 13 9.6" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>',
      sound: '<path d="M4.6 9 H8.4 L13 4.8 V19.2 L8.4 15 H4.6 Z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/><path d="M15.4 9.2 C16.8 10.4 16.8 13.6 15.4 14.8" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/><path d="M17.4 7.2 C19.8 9.2 19.8 14.8 17.4 16.8" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>',
    };
    return `<svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true">${icons[kind] || ""}</svg>`;
  }

  function backArrow() {
    return `<button class="back" type="button" data-act="back" aria-label="Retour">
      <svg width="28" height="12" viewBox="0 0 28 12" aria-hidden="true">
        <path d="M6 1 L1 6 L6 11" fill="none" stroke="currentColor" stroke-width="1.15" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M1.6 6 H27" fill="none" stroke="currentColor" stroke-width="1.15" stroke-linecap="round"/>
      </svg>
    </button>`;
  }

  function powerGlyph(size) {
    return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 3.2 v8.2" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
      <path d="M7.6 6.2 a7 7 0 1 0 8.8 0" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
    </svg>`;
  }

  function windGlyph(size) {
    return `<svg class="wind" width="${size}" height="${size}" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M3.6 8.1 H13.8 C15.7 8.1 17 6.9 17 5.7 C17 4.5 15.9 3.7 14.8 4.1" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      <path d="M3.6 12.2 H18.2 C20 12.2 21.3 13.4 21.3 14.8 C21.3 16.2 19.9 17.2 18.5 16.7" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      <path d="M3.6 16.3 H12.2 C13.6 16.3 14.6 17.2 14.6 18.3 C14.6 19.3 13.7 20.1 12.7 19.7" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    </svg>`;
  }

  function greeting() {
    const hour = new Date().getHours();
    if (hour >= 22 || hour < 6) return "Bonne nuit";
    if (hour < 12) return "Bonjour";
    if (hour < 18) return "Bon après-midi";
    return "Bonsoir";
  }

  function formatStayDates(checkIn, checkOut) {
    const months = [
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
    ];
    const start = checkIn ? new Date(checkIn) : null;
    const end = checkOut ? new Date(checkOut) : null;
    if (!start || !end || Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
      return "";
    }
    if (start.getMonth() === end.getMonth() && start.getFullYear() === end.getFullYear()) {
      return `${start.getDate()} – ${end.getDate()} ${months[start.getMonth()]}`;
    }
    if (start.getFullYear() === end.getFullYear()) {
      return `${start.getDate()} ${months[start.getMonth()]} – ${end.getDate()} ${months[end.getMonth()]}`;
    }
    return `${start.getDate()} ${months[start.getMonth()]} ${start.getFullYear()} – ${end.getDate()} ${months[end.getMonth()]} ${end.getFullYear()}`;
  }

  function modeLabel() {
    if (state && state.mode_label) return state.mode_label;
    return state && state.mode === "heat" ? "Chauffage" : "Climatisation";
  }

  function modeTabLabel() {
    if (state && (state.mode === "heat" || state.mode_label === "Chauffage")) {
      return "Chauffage";
    }
    return "Clim";
  }

  function activityOf(room) {
    const mode = (state && state.mode) || "cool";
    if (!room || !room.on) return "off";
    const measured = Number(room.measured);
    const setpoint = Number(room.setpoint);
    if (!Number.isFinite(measured) || !Number.isFinite(setpoint)) return "idle";
    if (mode === "heat" && setpoint > measured) return "heating";
    if (mode === "cool" && setpoint < measured) return "cooling";
    return "idle";
  }

  function activityClass(room) {
    const activity = activityOf(room);
    if (activity === "heating") return " heating";
    if (activity === "cooling") return " cooling";
    return "";
  }

  function hasAccess() {
    return Boolean(
      ((state && state.locks) || []).length ||
        ((state && state.garages) || []).length ||
        ((state && state.gates) || []).length ||
        ((state && state.shutters) || []).length ||
        ((state && state.alarms) || []).length ||
        ((state && state.doorbells) || []).length ||
        ((state && state.chargers) || []).length
    );
  }

  function stayShareUrl() {
    const info = (state && state.informations) || {};
    const fromState = String(info.lien_maison || "").trim();
    try {
      const page = new URL(window.location.href);
      page.search = "";
      page.hash = "";
      if (page.pathname.indexOf("/s/") !== -1) return page.toString();
    } catch (err) {
      /* ignore */
    }
    return fromState;
  }

  function hasInfo() {
    const info = (state && state.informations) || {};
    const ssid = String(info.wifi_ssid || "").trim();
    const revoked = Boolean(info.voucher_revoked);
    const code = revoked ? "" : String(info.voucher_code || "").trim();
    const nukiRevoked = Boolean(info.nuki_revoked);
    const nuki = nukiRevoked ? "" : String(info.nuki_code || "").trim();
    return Boolean(
      ssid || code || revoked || nuki || nukiRevoked || stayShareUrl() || info.qr_svg
    );
  }

  function metricByKind(kind) {
    return ((state && state.metrics) || []).find((item) => item.kind === kind) || null;
  }

  function hasPool() {
    return Boolean(
      metricByKind("pool_temp") ||
        metricByKind("pool_ph") ||
        ((state && state.pool_lights) || []).length
    );
  }

  function tabItems() {
    const items = [{ id: "home", label: "Maison", icon: "home" }];
    if (((state && state.climates) || []).length) {
      items.push({ id: "climate", label: modeTabLabel(), icon: "climate" });
    }
    if (hasPool()) items.push({ id: "pool", label: "Pool", icon: "pool" });
    if (((state && state.lights) || []).length || ((state && state.scenes) || []).length) {
      items.push({ id: "lights", label: "Lumière", icon: "lights" });
    }
    if (hasAccess()) items.push({ id: "access", label: "Accès", icon: "access" });
    if (((state && state.speakers) || []).length) {
      items.push({ id: "sound", label: "Son", icon: "sound" });
    }
    if (hasInfo()) items.push({ id: "info", label: "Infos", icon: "info" });
    return items;
  }

  function normalizeScreen() {
    if (screen === "room") return;
    const allowed = new Set(tabItems().map((item) => item.id));
    if (!allowed.has(screen)) screen = "home";
  }

  function dock() {
    if (screen === "room") return "";
    return `<nav class="dock" aria-label="Navigation">
      ${tabItems()
        .map(
          (item) => `<button class="dock-item${screen === item.id ? " on" : ""}" type="button" data-act="tab" data-id="${item.id}">
          ${icon(item.icon)}
          <span>${escapeHtml(item.label)}</span>
        </button>`
        )
        .join("")}
    </nav>`;
  }

  function brandBar(withBack) {
    return `<header class="brand${withBack ? " brand-room" : ""}">
      ${withBack ? backArrow() : ""}
      <img class="brand-logo" src="/usvegliu/static/logo-banner.png" width="1490" height="400" alt="U Svegliu, villa Lumio Corsica" />
    </header>`;
  }

  function welcomeHead() {
    const guest = String((state && state.guest) || "").trim();
    const dates = state && state.preview
      ? "Visite d'essai"
      : formatStayDates(state && state.check_in, state && state.check_out);
    return `<div class="hero">
      <p class="kicker">${greeting()}</p>
      <h1 class="welcome">${guest ? escapeHtml(guest) : "Bienvenue"}</h1>
      ${dates ? `<p class="stay-dates">${escapeHtml(dates)}</p>` : ""}
    </div>`;
  }

  function pageHead(title, kicker) {
    return `<div class="hero hero-page">
      ${kicker ? `<p class="kicker">${escapeHtml(kicker)}</p>` : ""}
      <h1 class="welcome">${escapeHtml(title)}</h1>
    </div>`;
  }

  function copyText(text) {
    if (!text) return;
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).catch(() => copyFallback(text));
      return;
    }
    copyFallback(text);
  }

  function copyFallback(text) {
    const el = document.createElement("textarea");
    el.value = text;
    el.setAttribute("readonly", "");
    el.style.position = "fixed";
    el.style.left = "-9999px";
    document.body.appendChild(el);
    el.select();
    try {
      document.execCommand("copy");
    } catch (err) {
      /* ignore */
    }
    document.body.removeChild(el);
  }

  let copiedKey = "";
  let copiedTimer = null;

  function markCopied(key) {
    copiedKey = key;
    if (copiedTimer) clearTimeout(copiedTimer);
    copiedTimer = setTimeout(() => {
      copiedKey = "";
      render();
    }, 1600);
    render();
  }

  function infoRow(label, value, copyable, key) {
    const done = copyable && copiedKey === key;
    return `<div class="info-row">
      <div class="info-copy">
        <div class="info-label">${escapeHtml(label)}</div>
        <div class="info-value">${escapeHtml(value)}</div>
      </div>
      ${
        copyable
          ? `<button class="copy-btn${done ? " done" : ""}" type="button" data-act="copy" data-copy="${escapeAttr(value)}" data-id="${escapeAttr(key)}" aria-label="Copier ${escapeAttr(label)}">${done ? "Copié" : "Copier"}</button>`
          : ""
      }
    </div>`;
  }

  function safeQrSvg(raw) {
    const text = String(raw || "").trim();
    if (!text.startsWith("<svg") || text.indexOf("</svg>") === -1) return "";
    if (/<script/i.test(text) || /on[a-z]+=/i.test(text)) return "";
    return text;
  }

  function shareSection() {
    const info = (state && state.informations) || {};
    const url = stayShareUrl();
    const qr = safeQrSvg(info.qr_svg);
    if (!url && !qr) return "";
    return `<section class="sheet info-sheet share-sheet">
      <div class="info-label">Partager l'app</div>
      ${qr ? `<div class="qr-frame" aria-label="QR code de l'app Maison">${qr}</div>` : ""}
      <p class="share-hint">Scannez pour ouvrir la maison sur un autre téléphone.</p>
      ${url ? infoRow("Lien Maison", url, true, "lien") : ""}
    </section>`;
  }

  function infoSection() {
    const info = (state && state.informations) || {};
    const ssid = String(info.wifi_ssid || "").trim();
    const revoked = Boolean(info.voucher_revoked);
    const code = revoked ? "" : String(info.voucher_code || "").trim();
    const rows = [];
    if (ssid) rows.push(infoRow("Réseau Wi-Fi", ssid, true, "ssid"));
    if (revoked) rows.push(infoRow("Code Wi-Fi", "Révoqué", false, "code"));
    else if (code) rows.push(infoRow("Code Wi-Fi", code, true, "code"));
    const nukiRevoked = Boolean(info.nuki_revoked);
    const nuki = nukiRevoked ? "" : String(info.nuki_code || "").trim();
    if (nukiRevoked) rows.push(infoRow("Code porte", "Révoqué", false, "nuki"));
    else if (nuki) rows.push(infoRow("Code porte", nuki, true, "nuki"));
    const wifi = rows.length ? `<section class="sheet info-sheet">${rows.join("")}</section>` : "";
    const share = shareSection();
    if (!wifi && !share) return "";
    return `${wifi}${share}`;
  }

  function weatherGlyph(kind) {
    const marks = {
      sun: '<circle cx="48" cy="48" r="14" fill="none" stroke="currentColor" stroke-width="2.2"/><g stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M48 12 V22"/><path d="M48 74 V84"/><path d="M12 48 H22"/><path d="M74 48 H84"/><path d="M22.4 22.4 L29.5 29.5"/><path d="M66.5 66.5 L73.6 73.6"/><path d="M73.6 22.4 L66.5 29.5"/><path d="M29.5 66.5 L22.4 73.6"/></g>',
      sun_cloud:
        '<circle cx="36" cy="34" r="11" fill="none" stroke="currentColor" stroke-width="2"/><g stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M36 14 V20"/><path d="M18 34 H24"/><path d="M22.2 20.2 L26.4 24.4"/><path d="M49.8 20.2 L45.6 24.4"/></g><path d="M28 62 H70 C78 62 82 54 76 48 C80 36 64 30 58 40 C50 28 34 34 36 48 C28 48 24 56 28 62 Z" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linejoin="round"/>',
      cloud:
        '<path d="M24 64 H72 C82 64 86 54 80 48 C84 34 66 26 58 38 C50 24 30 30 32 46 C22 46 16 56 24 64 Z" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linejoin="round"/>',
      fog: '<path d="M24 46 H72 C82 46 86 36 80 30 C84 16 66 8 58 20 C50 6 30 12 32 28 C22 28 16 38 24 46 Z" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linejoin="round"/><g stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M22 60 H74"/><path d="M28 72 H68"/></g>',
      drizzle:
        '<path d="M24 48 H72 C82 48 86 38 80 32 C84 18 66 10 58 22 C50 8 30 14 32 30 C22 30 16 40 24 48 Z" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linejoin="round"/><g stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M36 62 V68"/><path d="M48 64 V70"/><path d="M60 62 V68"/></g>',
      rain: '<path d="M24 46 H72 C82 46 86 36 80 30 C84 16 66 8 58 20 C50 6 30 12 32 28 C22 28 16 38 24 46 Z" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linejoin="round"/><g stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M34 58 L28 76"/><path d="M48 60 L42 78"/><path d="M62 58 L56 76"/></g>',
      snow: '<path d="M24 44 H72 C82 44 86 34 80 28 C84 14 66 6 58 18 C50 4 30 10 32 26 C22 26 16 36 24 44 Z" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linejoin="round"/><g stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M36 58 V74"/><path d="M30 64 H42"/><path d="M32 60 L40 72"/><path d="M40 60 L32 72"/><path d="M60 58 V74"/><path d="M54 64 H66"/></g>',
      storm:
        '<path d="M24 42 H70 C80 42 84 32 78 26 C82 12 64 6 56 16 C48 4 30 10 32 24 C22 24 16 34 24 42 Z" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linejoin="round"/><path d="M50 46 L38 64 H50 L42 82 L66 58 H52 Z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>',
    };
    return `<svg class="weather-mark" width="96" height="96" viewBox="0 0 96 96" aria-hidden="true">${marks[kind] || marks.cloud}</svg>`;
  }

  function weatherCard() {
    const weather = state && state.weather;
    if (!weather || weather.temperature === undefined || weather.temperature === null) {
      return "";
    }
    const high = weather.high === null || weather.high === undefined ? "" : `${weather.high}°`;
    const low = weather.low === null || weather.low === undefined ? "" : `${weather.low}°`;
    const range = low && high ? `${low} — ${high}` : high || low;
    const wind =
      weather.wind === null || weather.wind === undefined ? "" : `vent ${weather.wind} km/h`;
    const meta = [range, wind].filter(Boolean).join(" · ");
    return `<section class="weather" aria-label="Météo à Lumio">
      <div class="weather-icon">${weatherGlyph(weather.icon || "cloud")}</div>
      <div class="weather-copy">
        <p class="weather-place">${escapeHtml(weather.place || "Lumio")}</p>
        <p class="weather-label">${escapeHtml(weather.label || "")}</p>
        <p class="weather-temp">${escapeHtml(String(weather.temperature))}°</p>
        ${meta ? `<p class="weather-range">${escapeHtml(meta)}</p>` : ""}
      </div>
    </section>`;
  }

  function outdoorChip() {
    const outdoor = metricByKind("outdoor");
    if (!outdoor) return "";
    return `<aside class="outdoor-chip" aria-label="Température extérieure">
      <span class="outdoor-value">${escapeHtml(formatTemp(outdoor.value))}°</span>
      <span class="outdoor-label">Extérieur</span>
    </aside>`;
  }

  function poolGlyph() {
    return `<svg class="pool-mark" width="72" height="72" viewBox="0 0 72 72" aria-hidden="true">
      <path d="M10 44 C18 38 26 38 34 44 C42 50 50 50 58 44 C61 42 64 41 66 42" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      <path d="M10 32 C18 26 26 26 34 32 C42 38 50 38 58 32 C61 30 64 29 66 30" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      <path d="M28 16 C31 11 36 10 40 13 C44 16 45 22 42 26" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    </svg>`;
  }

  function chargerStatus(item) {
    if (item.state === "charging") return "En charge";
    if (item.state === "plugged") return "Branché";
    if (item.state === "fault") return "Hors service";
    return "Libre";
  }

  function doorbellStatus(item) {
    return item.ringing || item.state === "ringing" ? "Quelqu'un sonne" : "En attente";
  }

  let snapshotStamp = Date.now();
  let snapshotTimer = null;
  let visioOpen = false;
  let visioDismissed = false;

  function snapshotSrc(entityId) {
    return (
      `/api/usvegliu/guest/snapshot?entity_id=${encodeURIComponent(entityId)}` +
      `&token=${encodeURIComponent(token)}&t=${snapshotStamp}`
    );
  }

  function anyRinging() {
    return ((state && state.doorbells) || []).some(
      (item) => item.ringing || item.state === "ringing"
    );
  }

  function scheduleSnapshotRefresh() {
    if (snapshotTimer) {
      clearInterval(snapshotTimer);
      snapshotTimer = null;
    }
    if (!visioOpen || !((state && state.cameras) || []).length) return;
    snapshotTimer = setInterval(() => {
      snapshotStamp = Date.now();
      render();
    }, 4000);
  }

  function gateTarget() {
    const gates = (state && state.gates) || [];
    const garages = (state && state.garages) || [];
    return gates[0] || garages[0] || null;
  }

  function visioPopup() {
    if (!visioOpen) return "";
    const cam = ((state && state.cameras) || [])[0];
    const gate = gateTarget();
    const photo = cam
      ? `<div class="visio-frame">
          <img alt="${escapeAttr(cam.name)}" src="${escapeAttr(snapshotSrc(cam.entity_id))}" />
        </div>`
      : "";
    const openBtn = gate
      ? `<button class="access-action filled visio-open${cam ? "" : " solo"}" type="button" data-act="visio-open" data-id="${escapeAttr(gate.entity_id)}" data-cmd="open">Ouvrir le portail</button>`
      : "";
    return `<aside class="visio-pop" role="dialog" aria-modal="true" aria-label="Interphone">
      <div class="visio-pop-card">
        <p class="visio-pop-kicker">Quelqu'un sonne</p>
        <div class="visio-pop-row">${photo}${openBtn}</div>
        <button class="visio-pop-close" type="button" data-act="visio-close">Fermer</button>
      </div>
    </aside>`;
  }

  function statusCards() {
    const chargers = (state && state.chargers) || [];
    if (!chargers.length) return "";
    return chargers
      .map(
        (item) => `<section class="status-sheet${item.state === "charging" ? " live" : ""}">
        <div class="status-label">Borne</div>
        <div class="status-name">${escapeHtml(item.name)}</div>
        <div class="status-value">${escapeHtml(chargerStatus(item))}</div>
      </section>`
      )
      .join("");
  }

  function poolLights() {
    const lights = (state && state.pool_lights) || [];
    if (!lights.length) return "";
    return `<div class="light-list pool-lights">${lights
      .map(
        (light) => `<button class="row" type="button" data-act="pool-light" data-id="${escapeAttr(light.entity_id)}">
          <span>${escapeHtml(light.name)}</span>
          <span class="${light.on ? "" : "off"}">${light.on ? "Allumée" : "Éteinte"}</span>
        </button>`
      )
      .join("")}</div>`;
  }

  function poolSection() {
    const water = metricByKind("pool_temp");
    const ph = metricByKind("pool_ph");
    const lights = poolLights();
    if (!water && !ph && !lights) return "";
    const temp = water
      ? `<div class="pool-temp">
          <div class="metric-value">${escapeHtml(formatTemp(water.value))}°</div>
          <div class="metric-label">Eau</div>
        </div>`
      : "";
    const hero = water || ph
      ? `<section class="pool-sheet">
      <div class="pool-hero">${poolGlyph()}${temp}</div>
      ${
        ph
          ? `<div class="pool-ph"><span class="metric-label">pH</span><span class="metric-value">${escapeHtml(formatTemp(ph.value))}</span></div>`
          : ""
      }
    </section>`
      : "";
    return `${hero}${lights}`;
  }

  function modeSwitch() {
    return `<div class="segment" role="tablist">
      <button type="button" data-act="mode" data-id="reglage" class="${listMode === "reglage" ? "on" : ""}">Régler</button>
      <button type="button" data-act="mode" data-id="pieces" class="${listMode === "pieces" ? "on" : ""}">Aperçu</button>
    </div>`;
  }

  function piecesView() {
    const rooms = (state && state.climates) || [];
    if (!rooms.length) return "";
    return `<div class="climate-list">${rooms
      .map(
        (room) => `<button class="room-card${activityClass(room)}" type="button" data-act="open" data-id="${escapeAttr(room.entity_id)}">
        <span class="room-card-name">${escapeHtml(room.name)}</span>
        <span class="room-card-temp${room.on ? "" : " off"}">${room.on ? `${formatTemp(room.measured)}°` : "Éteint"}</span>
      </button>`
      )
      .join("")}</div>`;
  }

  function adjustView() {
    const rooms = (state && state.climates) || [];
    if (!rooms.length) return "";
    return `<div class="climate-list">${rooms
      .map((room) => {
        const dim = room.on ? "" : " muted";
        return `<div class="adjust${activityClass(room)}">
          <div class="adjust-top">
            <button class="name${dim}" type="button" data-act="open" data-id="${escapeAttr(room.entity_id)}">${escapeHtml(room.name)}</button>
            <span class="measured${dim}">${formatTemp(room.measured)}°</span>
          </div>
          <div class="adjust-controls">
            <button class="power ${room.on ? "on" : ""}" type="button" data-act="on" data-id="${escapeAttr(room.entity_id)}" aria-label="${room.on ? "Éteindre" : "Allumer"}">${powerGlyph(14)}</button>
            <button class="fan-chip" type="button" data-act="fan" data-id="${escapeAttr(room.entity_id)}" ${room.on ? "" : "disabled"} aria-label="Ventilation">${windGlyph(18)}<span>${room.fan || 2}</span></button>
            <div class="setpoint">
              <button class="chevron" type="button" data-act="minus" data-id="${escapeAttr(room.entity_id)}" ${room.on ? "" : "disabled"} aria-label="Moins">
                <svg width="10" height="16" viewBox="0 0 10 16"><path d="M8 1 L2 8 L8 15" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
              </button>
              <span class="${dim}">${formatTemp(room.setpoint)}°</span>
              <button class="chevron" type="button" data-act="plus" data-id="${escapeAttr(room.entity_id)}" ${room.on ? "" : "disabled"} aria-label="Plus">
                <svg width="10" height="16" viewBox="0 0 10 16"><path d="M2 1 L8 8 L2 15" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
              </button>
            </div>
          </div>
        </div>`;
      })
      .join("")}</div>`;
  }

  function polar(cx, cy, r, angle) {
    const rad = ((angle - 90) * Math.PI) / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
  }

  function arcPath(cx, cy, r, start, sweep) {
    const a = polar(cx, cy, r, start);
    const b = polar(cx, cy, r, start + sweep);
    const large = sweep > 180 ? 1 : 0;
    return `M ${a.x} ${a.y} A ${r} ${r} 0 ${large} 1 ${b.x} ${b.y}`;
  }

  function dialView(room) {
    const min = room.min || 16;
    const max = room.max || 28;
    const setpoint = Number(room.setpoint);
    const progress = Number.isFinite(setpoint) ? (setpoint - min) / (max - min) : 0.5;
    const sweep = 42 + Math.max(0, Math.min(1, progress)) * 118;
    const activity = activityClass(room);
    return `<div class="dial-wrap${activity}">
      <svg width="268" height="268" viewBox="0 0 268 268">
        <circle cx="134" cy="134" r="122" fill="none" stroke="rgba(43,36,28,0.12)" stroke-width="1.5"/>
        ${
          room.on
            ? `<path class="progress" d="${arcPath(134, 134, 122, -8, sweep)}" fill="none" stroke-width="7" stroke-linecap="round"/>`
            : ""
        }
      </svg>
      <div class="dial-center ${room.on ? "" : "off"}">
        <div class="dial-temp">${formatTemp(room.setpoint)}°</div>
        <div class="dial-hint">${room.on ? `Il fait ${formatTemp(room.measured)}°` : "Éteint"}</div>
      </div>
    </div>
    <div class="circles">
      <button class="circle" type="button" data-act="minus" data-id="${escapeAttr(room.entity_id)}" ${room.on ? "" : "disabled"} aria-label="Moins">−</button>
      <button class="circle ${room.on ? "filled" : ""}" type="button" data-act="on" data-id="${escapeAttr(room.entity_id)}" aria-label="${room.on ? "Éteindre" : "Allumer"}">${powerGlyph(20)}</button>
      <button class="circle" type="button" data-act="plus" data-id="${escapeAttr(room.entity_id)}" ${room.on ? "" : "disabled"} aria-label="Plus">+</button>
    </div>
    <div class="fan-line">
      <span class="label">${windGlyph(20)} Air</span>
      <div class="fan-row">
        ${[1, 2, 3]
          .map((n) => {
            const labels = { 1: "Doux", 2: "Moyen", 3: "Fort" };
            return `<button type="button" data-act="fan-set" data-id="${escapeAttr(room.entity_id)}" data-fan="${n}" class="${room.fan === n ? "on" : ""}" ${room.on ? "" : "disabled"}>${labels[n]}</button>`;
          })
          .join("")}
      </div>
    </div>`;
  }

  function climateSection() {
    const rooms = (state && state.climates) || [];
    if (!rooms.length) return "";
    return `${modeSwitch()}${listMode === "pieces" ? piecesView() : adjustView()}`;
  }

  function lightsSection() {
    const lights = (state && state.lights) || [];
    const scenes = (state && state.scenes) || [];
    if (!lights.length && !scenes.length) return "";
    const lightRows = `<div class="light-list">${lights
      .map(
        (light) => `<button class="row" type="button" data-act="light" data-id="${escapeAttr(light.entity_id)}">
          <span>${escapeHtml(light.name)}</span>
          <span class="${light.on ? "" : "off"}">${light.on ? "Allumée" : "Éteinte"}</span>
        </button>`
      )
      .join("")}</div>`;
    const sceneRow = scenes.length
      ? `<div class="scenes">${scenes
          .map(
            (scene) =>
              `<button type="button" data-act="scene" data-id="${escapeAttr(scene.entity_id)}">${escapeHtml(scene.name)}</button>`
          )
          .join("")}</div>`
      : "";
    return `${sceneRow}${lights.length ? lightRows : ""}`;
  }

  function coverStatus(item) {
    if (item.moving) return item.open ? "Ouverture…" : "Fermeture…";
    return item.open ? "Ouvert" : "Fermé";
  }

  function coverAction(item) {
    if (item.moving) return { action: "stop", label: "Stop" };
    return item.open ? { action: "close", label: "Fermer" } : { action: "open", label: "Ouvrir" };
  }

  function accessRow(item, status, action, act, extraClass) {
    return `<div class="access${extraClass || ""}">
      <div class="access-copy">
        <div class="access-name">${escapeHtml(item.name)}</div>
        <div class="access-status">${escapeHtml(status)}</div>
      </div>
      <button class="access-action ${action.filled ? "filled" : ""}" type="button" data-act="${escapeAttr(act)}" data-id="${escapeAttr(item.entity_id)}" data-cmd="${escapeAttr(action.cmd)}">${escapeHtml(action.label)}</button>
    </div>`;
  }

  function alarmStatus(alarm) {
    if (alarm.state === "triggered") return "Alarme";
    if (alarm.state === "pending") return "Armement…";
    if (alarm.state === "armed") return "Armée";
    return "Désarmée";
  }

  function accessSection() {
    const locks = (state && state.locks) || [];
    const garages = (state && state.garages) || [];
    const gates = (state && state.gates) || [];
    const shutters = (state && state.shutters) || [];
    const alarms = (state && state.alarms) || [];
    const doorbells = (state && state.doorbells) || [];
    const chargers = (state && state.chargers) || [];
    if (
      !locks.length &&
      !garages.length &&
      !gates.length &&
      !alarms.length &&
      !shutters.length &&
      !doorbells.length &&
      !chargers.length
    ) {
      return "";
    }
    const lockRows = locks.map((lock) =>
      accessRow(
        lock,
        lock.locked ? "Fermée" : "Ouverte",
        lock.locked ? { label: "Ouvrir", cmd: "unlock", filled: false } : { label: "Fermer", cmd: "lock", filled: true },
        "lock"
      )
    );
    const coverRows = [...garages, ...gates].map((item) => {
      const next = coverAction(item);
      return accessRow(item, coverStatus(item), { label: next.label, cmd: next.action, filled: item.open }, "cover");
    });
    const shutterBlock = shutters.length
      ? shutters
          .map((item) => {
            const next = coverAction(item);
            return accessRow(item, coverStatus(item), { label: next.label, cmd: next.action, filled: item.open }, "cover");
          })
          .join("")
      : "";
    const alarmRows = alarms.map((alarm) =>
      accessRow(
        alarm,
        alarmStatus(alarm),
        alarm.state === "disarmed"
          ? { label: "Armer", cmd: "arm", filled: false }
          : { label: "Désarmer", cmd: "disarm", filled: true },
        "alarm",
        alarm.state === "triggered" ? " triggered" : ""
      )
    );
    const doorbellRows = doorbells.map(
      (item) =>
        `<div class="access${item.ringing || item.state === "ringing" ? " ringing" : ""}">
        <div class="access-copy">
          <div class="access-name">${escapeHtml(item.name)}</div>
          <div class="access-status">${escapeHtml(doorbellStatus(item))}</div>
        </div>
      </div>`
    );
    const chargerRows = chargers.map(
      (item) =>
        `<div class="access${item.state === "charging" ? " live" : ""}">
        <div class="access-copy">
          <div class="access-name">${escapeHtml(item.name)}</div>
          <div class="access-status">${escapeHtml(chargerStatus(item))}</div>
        </div>
      </div>`
    );
    return `<div class="access-list">${doorbellRows.join("")}${lockRows.join("")}${coverRows.join("")}${shutterBlock}${alarmRows.join("")}${chargerRows.join("")}</div>`;
  }

  function speakerStatus(item) {
    if (item.muted) return "Muet";
    if (item.state === "playing") return "En lecture";
    if (item.state === "paused") return "En pause";
    return "Libre";
  }

  function soundSection() {
    const speakers = (state && state.speakers) || [];
    if (!speakers.length) return "";
    const zones = speakers
      .map((item) => {
        const live = item.state === "playing" && !item.muted;
        return `<section class="sound-zone${live ? " live" : ""}">
          <div class="sound-top">
            <div class="sound-name">${escapeHtml(item.name)}</div>
            <button class="sound-status" type="button" data-act="sound" data-id="${escapeAttr(item.entity_id)}" data-cmd="${item.state === "playing" ? "pause" : "play"}">${escapeHtml(speakerStatus(item))}</button>
          </div>
          <div class="sound-vol">
            <button class="chevron" type="button" data-act="sound-vol" data-id="${escapeAttr(item.entity_id)}" data-cmd="down" aria-label="Moins fort">
              <svg width="10" height="16" viewBox="0 0 10 16"><path d="M8 1 L2 8 L8 15" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </button>
            <span>${escapeHtml(String(item.volume || 0))} %</span>
            <button class="chevron" type="button" data-act="sound-vol" data-id="${escapeAttr(item.entity_id)}" data-cmd="up" aria-label="Plus fort">
              <svg width="10" height="16" viewBox="0 0 10 16"><path d="M2 1 L8 8 L2 15" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </button>
            <button class="sound-mute" type="button" data-act="sound" data-id="${escapeAttr(item.entity_id)}" data-cmd="${item.muted ? "unmute" : "mute"}">${item.muted ? "Son" : "Muet"}</button>
          </div>
        </section>`;
      })
      .join("");
    return `<button class="access-action filled sound-cut" type="button" data-act="sound-cut">Tout couper</button>
      <div class="sound-list">${zones}</div>`;
  }

  function homePage() {
    return `${welcomeHead()}${statusCards()}${weatherCard()}`;
  }

  function climateHead() {
    return `<div class="hero hero-page hero-climate">
      ${outdoorChip()}
      <h1 class="welcome">${escapeHtml(modeLabel())}</h1>
    </div>`;
  }

  function climatePage() {
    const body = climateSection();
    if (!body) return `${climateHead()}<p class="empty">Aucun thermostat pour ce séjour.</p>`;
    return `${climateHead()}${body}`;
  }

  function lightsPage() {
    const body = lightsSection();
    if (!body) return `${pageHead("Lumière")}<p class="empty">Aucune lumière pour ce séjour.</p>`;
    return `${pageHead("Lumière")}${body}`;
  }

  function accessPage() {
    const body = accessSection();
    if (!body) return `${pageHead("Accès")}<p class="empty">Aucun accès pour ce séjour.</p>`;
    return `${pageHead("Accès")}${body}`;
  }

  function infoPage() {
    const body = infoSection();
    if (!body) return `${pageHead("Informations")}<p class="empty">Aucune information pour ce séjour.</p>`;
    return `${pageHead("Informations")}${body}`;
  }

  function poolPage() {
    const body = poolSection();
    if (!body) return `${pageHead("Pool")}<p class="empty">Aucune donnée piscine pour ce séjour.</p>`;
    return `${pageHead("Pool")}${body}`;
  }

  function soundPage() {
    const body = soundSection();
    if (!body) return `${pageHead("Son")}<p class="empty">Aucune zone son pour ce séjour.</p>`;
    return `${pageHead("Son")}${body}`;
  }

  function pageView() {
    if (screen === "climate") return climatePage();
    if (screen === "pool") return poolPage();
    if (screen === "lights") return lightsPage();
    if (screen === "access") return accessPage();
    if (screen === "sound") return soundPage();
    if (screen === "info") return infoPage();
    return homePage();
  }

  function appChrome(inner, withBack) {
    return `<div class="shell${withBack ? " shell-room" : ""}">${brandBar(withBack)}${dock()}<main class="stage">${inner}</main>${visioPopup()}</div>`;
  }

  function statusPage(message, kind) {
    return `<div class="status">${brandBar(false)}<p class="${kind || "error"}">${message}</p></div>`;
  }

  function render() {
    if (!token) {
      root.innerHTML = statusPage("Ce lien est incomplet. Demandez-en un à l’accueil.");
      return;
    }
    if (error === "invalid_token") {
      root.innerHTML = statusPage("Ce séjour est clos. Demandez un nouveau lien à l’accueil.");
      return;
    }
    if (error === "too_early") {
      const when = arrivalNote ? ` le ${escapeHtml(arrivalNote)}` : " le jour de votre arrivée";
      root.innerHTML = statusPage(`La maison s’ouvre${when}.`);
      return;
    }
    if (!state) {
      root.innerHTML = statusPage("La maison s’ouvre…", "empty");
      return;
    }
    normalizeScreen();
    if (screen === "room") {
      const room = (state.climates || []).find((item) => item.entity_id === roomId);
      if (!room) {
        screen = "climate";
      } else {
        root.innerHTML = appChrome(
          `${pageHead(room.name, modeLabel())}${dialView(room)}`,
          true
        );
        bind();
        return;
      }
    }
    root.innerHTML = appChrome(pageView(), false);
    bind();
  }

  function bind() {
    root.querySelectorAll("[data-act]").forEach((el) => {
      el.addEventListener("click", onAction);
      el.addEventListener("mousedown", (event) => event.preventDefault());
    });
  }

  function patchList(key, entityId, patch) {
    state[key] = (state[key] || []).map((item) =>
      item.entity_id === entityId ? { ...item, ...patch } : item
    );
  }

  function patchLocal(entityId, patch) {
    patchList("climates", entityId, patch);
  }

  const pendingClimate = {};
  let climateSeq = 0;
  const HOLD_MS = 8000;
  const DEBOUNCE_MS = 280;

  function climateMatches(remote, patch) {
    if (!remote || !patch) return false;
    if ("setpoint" in patch && Number(remote.setpoint) !== Number(patch.setpoint)) {
      return false;
    }
    if ("on" in patch && Boolean(remote.on) !== Boolean(patch.on)) return false;
    if ("fan" in patch && Number(remote.fan) !== Number(patch.fan)) return false;
    return true;
  }

  function holdClimate(entityId, patch) {
    climateSeq += 1;
    const prev = pendingClimate[entityId];
    if (prev && prev.timer) clearTimeout(prev.timer);
    pendingClimate[entityId] = {
      seq: climateSeq,
      patch: { ...(prev && prev.patch), ...patch },
      since: Date.now(),
      timer: null,
    };
    return pendingClimate[entityId];
  }

  function mergeClimateHolds(rooms) {
    return (rooms || []).map((room) => {
      const hold = pendingClimate[room.entity_id];
      if (!hold) return room;
      if (Date.now() - hold.since > HOLD_MS || climateMatches(room, hold.patch)) {
        if (hold.timer) clearTimeout(hold.timer);
        delete pendingClimate[room.entity_id];
        return room;
      }
      return { ...room, ...hold.patch };
    });
  }

  function onAction(event) {
    const button = event.currentTarget;
    const act = button.getAttribute("data-act");
    const id = button.getAttribute("data-id");
    if (act === "back") {
      screen = "climate";
      render();
      return;
    }
    if (act === "tab") {
      screen = id;
      window.scrollTo(0, 0);
      render();
      return;
    }
    if (act === "copy") {
      copyText(button.getAttribute("data-copy") || "");
      markCopied(button.getAttribute("data-id") || "");
      return;
    }
    if (act === "mode") {
      listMode = id;
      render();
      return;
    }
    if (act === "open") {
      roomId = id;
      screen = "room";
      render();
      return;
    }
    const room = (state.climates || []).find((item) => item.entity_id === id);
    if (act === "on" && room) {
      commandClimate(id, { on: !room.on });
      return;
    }
    if (act === "minus" && room) {
      commandClimate(id, { setpoint: clamp(room, Number(room.setpoint) - 1) });
      return;
    }
    if (act === "plus" && room) {
      commandClimate(id, { setpoint: clamp(room, Number(room.setpoint) + 1) });
      return;
    }
    if (act === "fan" && room) {
      const next = room.fan >= 3 ? 1 : (room.fan || 1) + 1;
      commandClimate(id, { fan: next });
      return;
    }
    if (act === "fan-set" && room) {
      commandClimate(id, { fan: Number(button.getAttribute("data-fan")) });
      return;
    }
    if (act === "light" || act === "pool-light") {
      const listKey = act === "pool-light" ? "pool_lights" : "lights";
      const light = ((state && state[listKey]) || []).find((item) => item.entity_id === id);
      if (!light) return;
      commandEntity(listKey, id, light.on ? "off" : "on", { on: !light.on });
      return;
    }
    if (act === "scene") {
      commandEntity("scenes", id, "activate");
      return;
    }
    if (act === "lock") {
      commandEntity("locks", id, button.getAttribute("data-cmd"));
      return;
    }
    if (act === "cover") {
      commandEntity(coverListKey(id), id, button.getAttribute("data-cmd"));
      return;
    }
    if (act === "alarm") {
      commandEntity("alarms", id, button.getAttribute("data-cmd"));
      return;
    }
    if (act === "visio-close") {
      visioOpen = false;
      visioDismissed = true;
      scheduleSnapshotRefresh();
      render();
      return;
    }
    if (act === "visio-open") {
      const gate = gateTarget();
      if (!gate) return;
      commandEntity(coverListKey(gate.entity_id), gate.entity_id, "open", {
        open: true,
        state: "open",
      });
      return;
    }
    if (act === "sound-cut") {
      ((state && state.speakers) || []).forEach((item) => {
        commandEntity("speakers", item.entity_id, "stop", {
          state: "idle",
          muted: false,
        });
      });
      return;
    }
    if (act === "sound") {
      const speaker = ((state && state.speakers) || []).find((item) => item.entity_id === id);
      if (!speaker) return;
      const cmd = button.getAttribute("data-cmd");
      if (cmd === "pause") {
        commandEntity("speakers", id, "pause", { state: "paused" });
        return;
      }
      if (cmd === "play") {
        commandEntity("speakers", id, "play", { state: "playing", muted: false });
        return;
      }
      if (cmd === "mute") {
        commandEntity("speakers", id, "mute", { muted: true });
        return;
      }
      if (cmd === "unmute") {
        commandEntity("speakers", id, "unmute", { muted: false });
      }
      return;
    }
    if (act === "sound-vol") {
      const speaker = ((state && state.speakers) || []).find((item) => item.entity_id === id);
      if (!speaker) return;
      const delta = button.getAttribute("data-cmd") === "up" ? 5 : -5;
      const next = Math.max(0, Math.min(100, Number(speaker.volume || 0) + delta));
      commandEntity(
        "speakers",
        id,
        "volume",
        { volume: next, muted: next === 0 ? speaker.muted : false },
        { value: next }
      );
    }
  }

  function coverListKey(entityId) {
    if ((state.garages || []).some((item) => item.entity_id === entityId)) return "garages";
    if ((state.gates || []).some((item) => item.entity_id === entityId)) return "gates";
    return "shutters";
  }

  function clamp(room, value) {
    const min = Number(room.min || 16);
    const max = Number(room.max || 28);
    return Math.min(max, Math.max(min, value));
  }

  function commandClimate(entityId, body) {
    const hold = holdClimate(entityId, body);
    patchLocal(entityId, hold.patch);
    render();
    hold.timer = setTimeout(() => flushClimate(entityId, hold.seq), DEBOUNCE_MS);
  }

  function flushClimate(entityId, seq) {
    const hold = pendingClimate[entityId];
    if (!hold || hold.seq !== seq) return;
    hold.timer = null;
    const body = hold.patch;
    api("/api/usvegliu/guest/climate", {
      method: "POST",
      body: JSON.stringify({ entity_id: entityId, ...body }),
    })
      .then((updated) => {
        if (!pendingClimate[entityId] || pendingClimate[entityId].seq !== seq) return;
        if (updated && climateMatches(updated, body)) {
          delete pendingClimate[entityId];
          patchLocal(entityId, updated);
        } else if (updated) {
          patchLocal(entityId, { ...updated, ...body });
        }
        render();
      })
      .catch(() => {
        if (!pendingClimate[entityId] || pendingClimate[entityId].seq !== seq) return;
        delete pendingClimate[entityId];
        refresh();
      });
  }

  function commandEntity(listKey, entityId, action, optimistic, extra) {
    if (optimistic) {
      patchList(listKey, entityId, optimistic);
      render();
    }
    api("/api/usvegliu/guest/command", {
      method: "POST",
      body: JSON.stringify({ entity_id: entityId, action, ...(extra || {}) }),
    })
      .then((updated) => {
        if (listKey !== "scenes") patchList(listKey, entityId, updated);
        render();
      })
      .catch(() => refresh());
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function escapeAttr(value) {
    return escapeHtml(value).replace(/"/g, "&quot;");
  }

  function applyState(payload) {
    const next = payload || {};
    if (next.climates) next.climates = mergeClimateHolds(next.climates);
    state = next;
    error = "";
    arrivalNote = "";
    if (anyRinging()) {
      if (!visioDismissed) {
        visioOpen = true;
        screen = "home";
      }
    } else {
      visioOpen = false;
      visioDismissed = false;
    }
    scheduleSnapshotRefresh();
    render();
  }

  function failState(err) {
    const code = err && err.message;
    if (code === "invalid_token") {
      error = "invalid_token";
      arrivalNote = "";
      render();
      return;
    }
    if (code === "too_early") {
      error = "too_early";
      arrivalNote = (err && err.opensOn) || "";
      render();
      return;
    }
    error = "error";
    root.innerHTML = statusPage("La maison est momentanément indisponible.");
  }

  function refresh() {
    if (!token) {
      render();
      return;
    }
    api("/api/usvegliu/guest/state")
      .then(applyState)
      .catch(failState);
  }

  let source = null;
  let pollTimer = null;
  let retries = 0;

  function stopLive() {
    if (source) {
      source.close();
      source = null;
    }
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  function startPoll() {
    if (pollTimer) return;
    pollTimer = setInterval(refresh, 8000);
  }

  function startStream() {
    if (!token || !window.EventSource) {
      startPoll();
      return;
    }
    stopLive();
    const url = "/api/usvegliu/guest/stream?token=" + encodeURIComponent(token);
    source = new EventSource(url);
    source.addEventListener("state", (event) => {
      retries = 0;
      try {
        applyState(JSON.parse(event.data));
      } catch (err) {
        refresh();
      }
    });
    source.addEventListener("expired", () => {
      stopLive();
      failState({ message: "invalid_token" });
    });
    source.onerror = () => {
      retries += 1;
      if (retries < 3) return;
      if (source) {
        source.close();
        source = null;
      }
      startPoll();
    };
  }

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) return;
    refresh();
  });

  render();
  refresh();
  startStream();
})();
