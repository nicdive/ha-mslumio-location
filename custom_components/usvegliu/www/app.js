(function () {
  const root = document.getElementById("app");
  const token = readToken();
  let state = null;
  let screen = "home";
  let section = "climate";
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

  function svg(html) {
    return html;
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

  function brand(withBack) {
    return `<div class="header">
      ${withBack ? backArrow() : ""}
      <div class="brand"${withBack ? ' style="padding-top:14px"' : ""}>USVEGLIU</div>
    </div>`;
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

  function nav() {
    if (!state) return "";
    const climateTitle = modeLabel();
    const hasLock = state.locks && state.locks.length;
    if (!hasLock) return `<h1>${climateTitle}</h1>`;
    return `<h1>${section === "lock" ? "Entrée" : climateTitle}</h1>
      <div class="switch">
        <button type="button" data-act="section" data-id="climate" class="${section === "climate" ? "on" : ""}">${climateTitle}</button>
        <span class="dot">·</span>
        <button type="button" data-act="section" data-id="lock" class="${section === "lock" ? "on" : ""}">Entrée</button>
      </div>`;
  }

  function modeSwitch() {
    return `<div class="switch">
      <button type="button" data-act="mode" data-id="pieces" class="${listMode === "pieces" ? "on" : ""}">Pièces</button>
      <span class="dot">·</span>
      <button type="button" data-act="mode" data-id="reglage" class="${listMode === "reglage" ? "on" : ""}">Réglage</button>
    </div>`;
  }

  function piecesView() {
    const rooms = state.climates || [];
    if (!rooms.length) return `<p class="empty">Aucun thermostat n’est encore autorisé pour ce séjour.</p>`;
    return grouped(rooms)
      .map(
        (group) => `<div>
        <div class="group-label">${escapeHtml(group.name)}</div>
        ${group.rooms
          .map(
            (room) => `<button class="row${activityClass(room)}" type="button" data-act="open" data-id="${escapeAttr(room.entity_id)}">
            <span>${escapeHtml(room.name)}</span>
            <span class="${room.on ? "" : "off"}">${room.on ? `${formatTemp(room.measured)}°` : "Off"}</span>
          </button>`
          )
          .join("")}
      </div>`
      )
      .join("");
  }

  function adjustView() {
    const rooms = state.climates || [];
    if (!rooms.length) return `<p class="empty">Aucun thermostat n’est encore autorisé pour ce séjour.</p>`;
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
        <circle cx="134" cy="134" r="122" fill="none" stroke="#E4DDD3" stroke-width="1.5"/>
        ${
          room.on
            ? `<path class="progress" d="${arcPath(134, 134, 122, -8, sweep)}" fill="none" stroke-width="7" stroke-linecap="round"/>`
            : ""
        }
      </svg>
      <div class="dial-center ${room.on ? "" : "off"}">
        <div class="dial-temp">${formatTemp(room.setpoint)}°</div>
        <div class="dial-hint">${room.on ? `il fait ${formatTemp(room.measured)}°` : "éteint"}</div>
      </div>
    </div>
    <div class="circles">
      <button class="circle" type="button" data-act="minus" data-id="${escapeAttr(room.entity_id)}" ${room.on ? "" : "disabled"} aria-label="Moins">−</button>
      <button class="circle ${room.on ? "filled" : ""}" type="button" data-act="on" data-id="${escapeAttr(room.entity_id)}" aria-label="${room.on ? "Éteindre" : "Allumer"}">${powerGlyph(20)}</button>
      <button class="circle" type="button" data-act="plus" data-id="${escapeAttr(room.entity_id)}" ${room.on ? "" : "disabled"} aria-label="Plus">+</button>
    </div>
    <div class="fan-line">
      <span class="label">Air</span>
      <div class="fan-row" style="margin:0">
        ${[1, 2, 3]
          .map((n, i) => {
            const labels = { 1: "Doux", 2: "Moyen", 3: "Fort" };
            return `${i ? '<span class="dot">·</span>' : ""}<button type="button" data-act="fan-set" data-id="${escapeAttr(room.entity_id)}" data-fan="${n}" class="${room.fan === n ? "on" : ""}" ${room.on ? "" : "disabled"}>${labels[n]}</button>`;
          })
          .join("")}
      </div>
    </div>`;
  }

  function lockView() {
    const locks = state.locks || [];
    if (!locks.length) return `<p class="empty">Aucune serrure n’est autorisée pour ce séjour.</p>`;
    return locks
      .map((lock) => {
        const closed = lock.locked;
        return `<div class="lock-card">
          <div class="sub" style="margin-bottom:8px">${escapeHtml(lock.name)}</div>
          <div class="lock-status">${closed ? "Fermée" : "Ouverte"}</div>
          <button class="lock-action ${closed ? "filled" : ""}" type="button" data-act="lock" data-id="${escapeAttr(lock.entity_id)}" data-lock="${closed ? "unlock" : "lock"}">
            ${closed ? "Ouvrir" : "Fermer"}
          </button>
        </div>`;
      })
      .join("");
  }

  function render() {
    if (!token) {
      root.innerHTML = `<div class="brand">USVEGLIU</div><p class="error">Lien incomplet. Demandez un nouveau lien à la maison.</p>`;
      return;
    }
    if (error === "invalid_token") {
      root.innerHTML = `<div class="brand">USVEGLIU</div><p class="error">Ce lien n’est plus valable. Le séjour est terminé, ou un nouvel essai est nécessaire.</p>`;
      return;
    }
    if (!state) {
      root.innerHTML = `<div class="brand">USVEGLIU</div><p class="empty">Ouverture de la maison…</p>`;
      return;
    }
    if (screen === "room") {
      const room = (state.climates || []).find((item) => item.entity_id === roomId);
      if (!room) {
        screen = "home";
      } else {
        root.innerHTML = `${brand(true)}<h1>${modeLabel()}</h1><div class="room-name">${escapeHtml(room.name)}</div>${dialView(room)}`;
        bind();
        return;
      }
    }
    if (section === "lock") {
      root.innerHTML = `${brand(false)}${nav()}${lockView()}`;
      bind();
      return;
    }
    root.innerHTML = `${brand(false)}${nav()}${modeSwitch()}${listMode === "reglage" ? adjustView() : piecesView()}`;
    bind();
  }

  function bind() {
    root.querySelectorAll("[data-act]").forEach((el) => {
      el.addEventListener("click", onAction);
      el.addEventListener("mousedown", (event) => event.preventDefault());
    });
  }

  function patchLocal(entityId, patch) {
    state.climates = (state.climates || []).map((room) =>
      room.entity_id === entityId ? { ...room, ...patch } : room
    );
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
    if (act === "section") {
      section = id;
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
    if (act === "lock") {
      commandLock(id, button.getAttribute("data-lock"));
    }
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

  function commandLock(entityId, action) {
    api("/api/usvegliu/guest/lock", {
      method: "POST",
      body: JSON.stringify({ entity_id: entityId, action }),
    })
      .then((updated) => {
        state.locks = (state.locks || []).map((item) =>
          item.entity_id === entityId ? { ...item, ...updated } : item
        );
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
    if (!state.climates.length && state.locks.length) section = "lock";
    render();
  }

  function failState(err) {
    error = err && err.message === "invalid_token" ? "invalid_token" : "error";
    if (error !== "invalid_token") {
      root.innerHTML = `<div class="brand">USVEGLIU</div><p class="error">Impossible d’ouvrir la maison pour le moment.</p>`;
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
