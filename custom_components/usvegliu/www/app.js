(function () {
  const root = document.getElementById("app");
  const token = readToken();
  let state = null;
  let screen = "home";
  let listMode = "pieces";
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

  function grouped(rooms) {
    const groups = [];
    rooms.forEach((room) => {
      const name = room.group || "Maison";
      const last = groups[groups.length - 1];
      if (last && last.name === name) last.rooms.push(room);
      else groups.push({ name, rooms: [room] });
    });
    return groups;
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

  function masthead(withBack) {
    if (withBack) {
      return `<header class="masthead masthead-room">
        ${backArrow()}
        <div class="wordmark">Usvegliu</div>
      </header>`;
    }
    if (!state) {
      return `<header class="masthead"><div class="wordmark">Usvegliu</div></header>`;
    }
    const guest = String(state.guest || "").trim();
    const dates = state.preview
      ? "Visite d'essai"
      : formatStayDates(state.check_in, state.check_out);
    return `<header class="masthead">
      <div class="wordmark">Usvegliu</div>
      <p class="kicker">${greeting()}</p>
      <h1 class="welcome">${guest ? escapeHtml(guest) : "Bienvenue"}</h1>
      ${dates ? `<p class="stay-dates">${escapeHtml(dates)}</p>` : ""}
    </header>`;
  }

  function modeLabel() {
    if (state && state.mode_label) return state.mode_label;
    return state && state.mode === "heat" ? "Chauffage" : "Climatisation";
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

  function modeSwitch() {
    return `<div class="segment" role="tablist">
      <button type="button" data-act="mode" data-id="pieces" class="${listMode === "pieces" ? "on" : ""}">Pièces</button>
      <button type="button" data-act="mode" data-id="reglage" class="${listMode === "reglage" ? "on" : ""}">Régler</button>
    </div>`;
  }

  function sectionTitle(title) {
    return `<h2 class="panel-title">${escapeHtml(title)}</h2>`;
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

  function piecesView() {
    const rooms = state.climates || [];
    if (!rooms.length) return "";
    return grouped(rooms)
      .map(
        (group) => `<div>
        <div class="group-label">${escapeHtml(group.name)}</div>
        ${group.rooms
          .map(
            (room) => `<button class="row${activityClass(room)}" type="button" data-act="open" data-id="${escapeAttr(room.entity_id)}">
            <span>${escapeHtml(room.name)}</span>
            <span class="${room.on ? "" : "off"}">${room.on ? `${formatTemp(room.measured)}°` : "Éteint"}</span>`
          </button>`
          )
          .join("")}
      </div>`
      )
      .join("");
  }

  function adjustView() {
    const rooms = state.climates || [];
    if (!rooms.length) return "";
    return grouped(rooms)
      .map(
        (group) => `<div>
        <div class="group-label">${escapeHtml(group.name)}</div>
        ${group.rooms
          .map((room) => {
            const dim = room.on ? "" : " muted";
            return `<div class="adjust${activityClass(room)}">
              <button class="power ${room.on ? "on" : ""}" type="button" data-act="on" data-id="${escapeAttr(room.entity_id)}" aria-label="${room.on ? "Éteindre" : "Allumer"}">${powerGlyph(14)}</button>
              <button class="name${dim}" type="button" data-act="open" data-id="${escapeAttr(room.entity_id)}">${escapeHtml(room.name)}</button>
              <span class="measured${dim}">${formatTemp(room.measured)}°</span>
              <button class="badge" type="button" data-act="fan" data-id="${escapeAttr(room.entity_id)}" ${room.on ? "" : "disabled"}>${room.fan || 2}</button>
              <div class="setpoint">
                <button class="chevron" type="button" data-act="minus" data-id="${escapeAttr(room.entity_id)}" ${room.on ? "" : "disabled"} aria-label="Moins">
                  <svg width="10" height="16" viewBox="0 0 10 16"><path d="M8 1 L2 8 L8 15" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </button>
                <span class="${dim}">${formatTemp(room.setpoint)}°</span>
                <button class="chevron" type="button" data-act="plus" data-id="${escapeAttr(room.entity_id)}" ${room.on ? "" : "disabled"} aria-label="Plus">
                  <svg width="10" height="16" viewBox="0 0 10 16"><path d="M2 1 L8 8 L2 15" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </button>
              </div>
            </div>`;
          })
          .join("")}
      </div>`
      )
      .join("");
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
      <span class="label">Air</span>
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
    const rooms = state.climates || [];
    if (!rooms.length) return "";
    return `<section class="panel">
      ${sectionTitle(modeLabel())}
      ${modeSwitch()}
      ${listMode === "reglage" ? adjustView() : piecesView()}
    </section>`;
  }

  function lightsSection() {
    const lights = state.lights || [];
    const scenes = state.scenes || [];
    if (!lights.length && !scenes.length) return "";
    const lightRows = grouped(lights)
      .map((group) => {
        const label = lights.length && group.name !== "Maison" ? `<div class="group-label">${escapeHtml(group.name)}</div>` : "";
        return `${label}${group.rooms
          .map(
            (light) => `<button class="row" type="button" data-act="light" data-id="${escapeAttr(light.entity_id)}">
            <span>${escapeHtml(light.name)}</span>
            <span class="${light.on ? "" : "off"}">${light.on ? "Allumée" : "Éteinte"}</span>`
          </button>`
          )
          .join("")}`;
      })
      .join("");
    const sceneRow = scenes.length
      ? `<div class="scenes">${scenes
          .map(
            (scene) =>
              `<button type="button" data-act="scene" data-id="${escapeAttr(scene.entity_id)}">${escapeHtml(scene.name)}</button>`
          )
          .join("")}</div>`
      : "";
    return `<section class="panel">${sectionTitle("Lumière")}${lightRows}${sceneRow}</section>`;
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
    const locks = state.locks || [];
    const garages = state.garages || [];
    const gates = state.gates || [];
    const shutters = state.shutters || [];
    const alarms = state.alarms || [];
    if (!locks.length && !garages.length && !gates.length && !alarms.length && !shutters.length) return "";
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
      ? `<div class="group-label">Volets</div>${shutters
          .map((item) => {
            const next = coverAction(item);
            return accessRow(item, coverStatus(item), { label: next.label, cmd: next.action, filled: item.open }, "cover");
          })
          .join("")}`
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
    return `<section class="panel">${sectionTitle("Accès")}${lockRows.join("")}${coverRows.join("")}${shutterBlock}${alarmRows.join("")}</section>`;
  }

  function homeView() {
    const body = `${metricsView()}${climateSection()}${lightsSection()}${accessSection()}`;
    if (!body.trim()) {
      return `${masthead(false)}<p class="empty">Les équipements de votre séjour apparaîtront ici.</p>`;
    }
    return `${masthead(false)}${body}`;
  }

  function statusPage(message, kind) {
    return `<div class="status"><header class="masthead"><div class="wordmark">Usvegliu</div></header><p class="${kind || "error"}">${message}</p></div>`;
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
    if (screen === "room") {
      const room = (state.climates || []).find((item) => item.entity_id === roomId);
      if (!room) {
        screen = "home";
      } else {
        root.innerHTML = `${masthead(true)}<div class="room-hero"><p class="kicker">${escapeHtml(modeLabel())}</p><h1 class="welcome">${escapeHtml(room.name)}</h1></div>${dialView(room)}`;
        bind();
        return;
      }
    }
    root.innerHTML = homeView();
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

  function onAction(event) {
    const button = event.currentTarget;
    const act = button.getAttribute("data-act");
    const id = button.getAttribute("data-id");
    if (act === "back") {
      screen = "home";
      render();
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
    patchLocal(entityId, body);
    render();
    api("/api/usvegliu/guest/climate", {
      method: "POST",
      body: JSON.stringify({ entity_id: entityId, ...body }),
    })
      .then((updated) => {
        patchLocal(entityId, updated);
        render();
      })
      .catch(() => refresh());
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
    state = payload;
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
