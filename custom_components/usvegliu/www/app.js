(function () {
  const root = document.getElementById("app");
  const token = readToken();
  function readScreen() {
    const tab = new URLSearchParams(window.location.search).get("tab");
    if (tab === "climate" || tab === "lights" || tab === "access" || tab === "info") {
      return tab;
    }
    return "home";
  }

  let state = null;
  let screen = readScreen();
  let listMode = "reglage";
  let roomId = null;
  let error = "";

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
        ((state && state.alarms) || []).length
    );
  }

  function hasInfo() {
    const info = (state && state.informations) || {};
    const ssid = String(info.wifi_ssid || "").trim();
    const revoked = Boolean(info.voucher_revoked);
    const code = revoked ? "" : String(info.voucher_code || "").trim();
    return Boolean(ssid || code || revoked);
  }

  function tabItems() {
    const items = [{ id: "home", label: "Maison", icon: "home" }];
    if (((state && state.climates) || []).length) {
      items.push({ id: "climate", label: modeTabLabel(), icon: "climate" });
    }
    if (((state && state.lights) || []).length || ((state && state.scenes) || []).length) {
      items.push({ id: "lights", label: "Lumière", icon: "lights" });
    }
    if (hasAccess()) items.push({ id: "access", label: "Accès", icon: "access" });
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
      <div class="wordmark">Usvegliu</div>
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

  function infoSection() {
    const info = (state && state.informations) || {};
    const ssid = String(info.wifi_ssid || "").trim();
    const revoked = Boolean(info.voucher_revoked);
    const code = revoked ? "" : String(info.voucher_code || "").trim();
    if (!ssid && !code && !revoked) return "";
    const rows = [];
    if (ssid) rows.push(infoRow("Réseau Wi-Fi", ssid, true, "ssid"));
    if (revoked) rows.push(infoRow("Code Wi-Fi", "Révoqué", false, "code"));
    else if (code) rows.push(infoRow("Code Wi-Fi", code, true, "code"));
    return `<section class="sheet info-sheet">${rows.join("")}</section>`;
  }

  function metricsView() {
    const metrics = (state && state.metrics) || [];
    if (!metrics.length) return "";
    return `<div class="atmosphere">${metrics
      .map((item) => {
        const suffix = item.unit === "°" || !item.unit ? (item.kind === "pool_ph" ? "" : item.unit || "°") : item.unit;
        const shown = item.kind === "pool_ph" ? formatTemp(item.value) : `${formatTemp(item.value)}${suffix === "°" ? "°" : ""}`;
        return `<div class="metric">
          <div class="metric-value">${escapeHtml(shown)}${suffix && suffix !== "°" ? `<span class="metric-unit">${escapeHtml(suffix)}</span>` : ""}</div>
          <div class="metric-label">${escapeHtml(item.label)}</div>
        </div>`;
      })
      .join("")}</div>`;
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
    if (!locks.length && !garages.length && !gates.length && !alarms.length && !shutters.length) {
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
    return `<div class="access-list">${lockRows.join("")}${coverRows.join("")}${shutterBlock}${alarmRows.join("")}</div>`;
  }

  function homePage() {
    const metrics = metricsView();
    return `${welcomeHead()}${metrics}`;
  }

  function climatePage() {
    const body = climateSection();
    if (!body) return `${pageHead(modeLabel())}<p class="empty">Aucun thermostat pour ce séjour.</p>`;
    return `${pageHead(modeLabel())}${body}`;
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

  function pageView() {
    if (screen === "climate") return climatePage();
    if (screen === "lights") return lightsPage();
    if (screen === "access") return accessPage();
    if (screen === "info") return infoPage();
    return homePage();
  }

  function appChrome(inner, withBack) {
    return `<div class="shell${withBack ? " shell-room" : ""}">${brandBar(withBack)}${dock()}<main class="stage">${inner}</main></div>`;
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
    if (act === "light") {
      const light = (state.lights || []).find((item) => item.entity_id === id);
      if (!light) return;
      commandEntity("lights", id, light.on ? "off" : "on", { on: !light.on });
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

  function commandEntity(listKey, entityId, action, optimistic) {
    if (optimistic) {
      patchList(listKey, entityId, optimistic);
      render();
    }
    api("/api/usvegliu/guest/command", {
      method: "POST",
      body: JSON.stringify({ entity_id: entityId, action }),
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
    render();
  }

  function failState(err) {
    error = err && err.message === "invalid_token" ? "invalid_token" : "error";
    if (error !== "invalid_token") {
      root.innerHTML = statusPage("La maison est momentanément indisponible.");
      return;
    }
    render();
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
