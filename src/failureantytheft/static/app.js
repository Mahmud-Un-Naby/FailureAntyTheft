const app = {
  health: null,
  devices: [],
  events: [],
  selected: null,
  points: new Map(),
  activeEvent: null,
  pendingDevices: new Set(),
  editingId: null,
  loading: false,
  refreshTimer: null,
  ws: null,
  wsRetry: 0,
  audioContext: null,
  alarmTimer: null,
};

const $ = (id) => document.getElementById(id);

async function request(url, options = {}) {
  const response = await fetch(url, options);
  if (response.ok) {
    if (response.status === 204) return null;
    return response.json();
  }

  let message = `${response.status} ${response.statusText}`;
  const raw = await response.text();
  try {
    const payload = JSON.parse(raw);
    message = payload.detail || message;
  } catch {
    if (raw) message = raw;
  }
  throw new Error(message);
}

function escapeHtml(value) {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (character) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" })[
        character
      ],
  );
}

function humanize(value) {
  return String(value || "unknown")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.valueOf())
    ? "—"
    : new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(date);
}

function relativeTime(value) {
  if (!value) return "Never seen";
  const elapsed = Date.now() - new Date(value).valueOf();
  if (!Number.isFinite(elapsed)) return "Unknown";
  const seconds = Math.max(0, Math.round(elapsed / 1000));
  if (seconds < 10) return "Just now";
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return formatDate(value);
}

function endpointLabel(value) {
  try {
    const url = new URL(value);
    return url.host;
  } catch {
    return value;
  }
}

function runtimeFor(device) {
  return (
    device.runtime || {
      last_state: "offline",
      desired_armed: false,
      last_motion_score: 0,
      last_seen_at: null,
    }
  );
}

function showToast(message, type = "success") {
  const toast = document.createElement("div");
  toast.className = `toast ${type === "error" ? "error" : ""}`;
  toast.textContent = message;
  $("toast-region").appendChild(toast);
  window.setTimeout(() => toast.remove(), 4200);
}

function setHealthState(mode, title, detail) {
  $("health-dot").className = `status-dot ${mode}`;
  $("health-label").textContent = title;
  $("health").textContent = detail;
}

function renderHealth() {
  if (!app.health) {
    setHealthState("error", "Server unavailable", "Retrying local connection…");
    return;
  }
  const transport = String(app.health.transport || "local").toUpperCase();
  const count = app.devices.length;
  setHealthState(
    "online",
    "System operational",
    `${transport} · ${count} ${count === 1 ? "sensor" : "sensors"}`,
  );
}

function renderSummary() {
  const total = app.devices.length;
  const online = app.devices.filter((device) => runtimeFor(device).last_state !== "offline").length;
  const armed = app.devices.filter((device) => runtimeFor(device).desired_armed).length;
  const activeAlerts = app.events.filter((event) => event.state === "active").length;

  $("metric-total").textContent = total;
  $("metric-online").textContent = online;
  $("metric-armed").textContent = armed;
  $("metric-alerts").textContent = activeAlerts;
  $("device-count").textContent = total;

  $("metric-total-note").textContent = total
    ? `${total} configured ${total === 1 ? "device" : "devices"}`
    : "No sensors registered";
  $("metric-online-note").textContent = total
    ? `${online} of ${total} reporting`
    : "Waiting for devices";
  $("metric-armed-note").textContent = armed
    ? `${armed} actively protected`
    : "Protection is inactive";
  $("metric-alerts-note").textContent = activeAlerts
    ? `${activeAlerts} ${activeAlerts === 1 ? "event needs" : "events need"} review`
    : "No action required";
  $("metric-alerts").closest(".metric-card").classList.toggle("has-alerts", activeAlerts > 0);

  $("arm-all").disabled = total === 0 || app.pendingDevices.size > 0;
  $("disarm-all").disabled = total === 0 || app.pendingDevices.size > 0;
}

function renderDevices() {
  const container = $("devices");
  if (!app.devices.length) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">＋</div>
        <strong>No phone sensors yet</strong>
        <p>Add a phone running Phyphox to begin monitoring a bag, drawer, bicycle, or other object.</p>
        <button class="button button-primary" type="button" data-open-register>Add your first sensor</button>
      </div>`;
    return;
  }

  container.innerHTML = app.devices
    .map((device) => {
      const runtime = runtimeFor(device);
      const currentState = runtime.last_state || "offline";
      const desiredArmed = Boolean(runtime.desired_armed);
      const pending = app.pendingDevices.has(device.device_id);
      const score = Number(runtime.last_motion_score || 0);
      const selected = app.selected === device.device_id;
      const action = desiredArmed ? "disarm" : "arm";
      const actionLabel = pending ? "Working…" : desiredArmed ? "Disarm" : "Arm device";

      return `
        <article class="device-card ${selected ? "selected" : ""} ${currentState === "alarm" ? "alarm" : ""}" data-device="${device.device_id}">
          <div class="device-card-head">
            <div class="device-identity">
              <div class="device-avatar" aria-hidden="true">▯</div>
              <div><h3>${escapeHtml(device.name)}</h3><p>${escapeHtml(device.device_id)}</p></div>
            </div>
            <button class="device-menu-button" type="button" data-action="edit" aria-label="Edit ${escapeHtml(device.name)}" title="Edit sensor">•••</button>
          </div>
          <div class="device-status-line">
            <span class="state-chip ${currentState}"><i></i>${humanize(currentState)}</span>
            <div class="motion-reading"><span>Motion</span><strong>${score.toFixed(2)}</strong></div>
          </div>
          <div class="device-meta">
            <div class="device-meta-row"><span>Last contact</span><strong>${relativeTime(runtime.last_seen_at)}</strong></div>
            <div class="device-meta-row"><span>Endpoint</span><strong title="${escapeHtml(device.source_url)}">${escapeHtml(endpointLabel(device.source_url))}</strong></div>
            <div class="device-meta-row"><span>Sensitivity</span><strong>${Number(device.sensitivity).toFixed(1)} m/s²</strong></div>
          </div>
          <div class="device-actions">
            <button class="button button-secondary view-live" type="button" data-action="live">${selected ? "Monitoring" : "View live"}</button>
            <button class="button ${desiredArmed ? "button-secondary" : "button-primary"}" type="button" data-action="${action}" ${pending ? "disabled" : ""}>${actionLabel}</button>
          </div>
        </article>`;
    })
    .join("");
}

function eventTypeDetails(event) {
  if (event.type === "movement_detected") {
    return { label: "Movement detected", detail: "Motion threshold exceeded", icon: "!", style: "movement" };
  }
  return { label: "Connection warning", detail: "Sensor stopped reporting", icon: "⌁", style: "" };
}

function filteredEvents() {
  const filter = $("event-filter").value;
  if (filter === "all") return app.events;
  if (filter === "active") return app.events.filter((event) => event.state === "active");
  return app.events.filter((event) => event.type === filter);
}

function renderEvents() {
  const events = filteredEvents();
  $("event-count").textContent = app.events.length;
  if (!events.length) {
    $("events").innerHTML = `<tr class="table-empty"><td colspan="6">No events match this view.</td></tr>`;
    return;
  }

  $("events").innerHTML = events
    .map((event) => {
      const details = eventTypeDetails(event);
      const active = event.state === "active";
      return `
        <tr>
          <td><div class="event-title"><span class="event-icon ${details.style}">${details.icon}</span><span><strong>${details.label}</strong><small>${details.detail}</small></span></div></td>
          <td>${escapeHtml(event.device_id)}</td>
          <td title="${escapeHtml(formatDate(event.started_at))}">${relativeTime(event.started_at)}</td>
          <td><span class="severity-badge ${event.severity}">${humanize(event.severity)}</span></td>
          <td><span class="event-state ${active ? "active" : ""}"><i></i>${humanize(event.state)}</span></td>
          <td>${active ? `<button class="button button-secondary" type="button" data-event="${escapeHtml(event.event_id)}">Acknowledge</button>` : ""}</td>
        </tr>`;
    })
    .join("");
}

function renderAll() {
  renderHealth();
  renderSummary();
  renderDevices();
  renderEvents();
  syncAlarmFromEvents();
  drawChart();
}

async function load({ quiet = false } = {}) {
  if (app.loading) return;
  app.loading = true;
  $("refresh").disabled = true;
  try {
    const [health, devices, events] = await Promise.all([
      request("/api/health"),
      request("/api/devices"),
      request("/api/events"),
    ]);
    app.health = health;
    app.devices = devices;
    app.events = events;
    if (app.selected && !devices.some((device) => device.device_id === app.selected)) {
      app.selected = null;
    }
    if (!app.selected && devices.length) app.selected = devices[0].device_id;
    renderAll();
    subscribeToSelected();
  } catch (error) {
    app.health = null;
    renderHealth();
    if (!quiet) showToast(`Could not refresh: ${error.message}`, "error");
  } finally {
    app.loading = false;
    $("refresh").disabled = false;
  }
}

function scheduleLoad() {
  window.clearTimeout(app.refreshTimer);
  app.refreshTimer = window.setTimeout(() => load({ quiet: true }), 280);
}

async function commandDevice(deviceId, action, { quiet = false } = {}) {
  if (app.pendingDevices.has(deviceId)) return;
  app.pendingDevices.add(deviceId);
  renderSummary();
  renderDevices();
  try {
    await request(`/api/devices/${encodeURIComponent(deviceId)}/${action}`, { method: "POST" });
    if (!quiet) showToast(`${deviceId} ${action === "arm" ? "is calibrating" : "was disarmed"}.`);
    window.setTimeout(() => load({ quiet: true }), 350);
  } catch (error) {
    showToast(`Command failed: ${error.message}`, "error");
  } finally {
    app.pendingDevices.delete(deviceId);
    renderSummary();
    renderDevices();
  }
}

async function commandAll(action) {
  const targets = app.devices.filter((device) => device.enabled !== false);
  if (!targets.length) return;
  for (const device of targets) app.pendingDevices.add(device.device_id);
  renderSummary();
  renderDevices();
  const results = await Promise.allSettled(
    targets.map((device) =>
      request(`/api/devices/${encodeURIComponent(device.device_id)}/${action}`, { method: "POST" }),
    ),
  );
  app.pendingDevices.clear();
  const failed = results.filter((result) => result.status === "rejected").length;
  if (failed) showToast(`${failed} device command${failed === 1 ? "" : "s"} failed.`, "error");
  else showToast(`${targets.length} ${targets.length === 1 ? "device" : "devices"} ${action === "arm" ? "are calibrating" : "were disarmed"}.`);
  renderSummary();
  renderDevices();
  window.setTimeout(() => load({ quiet: true }), 350);
}

async function acknowledge(eventId) {
  try {
    await request(`/api/events/${encodeURIComponent(eventId)}/acknowledge`, { method: "POST" });
    stopAlarm();
    $("alarm").classList.add("hidden");
    app.activeEvent = null;
    showToast("Alert acknowledged and sensor disarmed.");
    window.setTimeout(() => load({ quiet: true }), 350);
  } catch (error) {
    showToast(`Could not acknowledge alert: ${error.message}`, "error");
  }
}

function selectDevice(deviceId, { scroll = false } = {}) {
  app.selected = deviceId;
  if (!app.points.has(deviceId)) app.points.set(deviceId, []);
  renderDevices();
  drawChart();
  subscribeToSelected();
  if (scroll) $("monitoring").scrollIntoView({ behavior: "smooth", block: "start" });
}

function subscribeToSelected() {
  if (!app.selected || app.ws?.readyState !== WebSocket.OPEN) return;
  app.ws.send(JSON.stringify({ action: "subscribe_chart", device_id: app.selected }));
}

function setWebSocketStatus(status) {
  $("ws-status").textContent = status;
  $("ws-status").style.color = status === "Live" ? "var(--green)" : "";
}

function connectWebSocket() {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  setWebSocketStatus("Connecting");
  app.ws = new WebSocket(`${protocol}://${location.host}/ws`);

  app.ws.onopen = () => {
    app.wsRetry = 0;
    setWebSocketStatus("Live");
    subscribeToSelected();
  };

  app.ws.onmessage = (message) => {
    let envelope;
    try {
      envelope = JSON.parse(message.data);
    } catch {
      return;
    }
    const payload = envelope.payload;
    if (envelope.type === "chart" && payload.device_id === app.selected) {
      const points = app.points.get(payload.device_id) || [];
      points.push(Number(payload.motion_score || 0));
      if (points.length > 120) points.shift();
      app.points.set(payload.device_id, points);
      drawChart();
    } else if (envelope.type === "alert") {
      if (payload.state === "active" && payload.type === "movement_detected") {
        showAlarm(payload);
      }
      scheduleLoad();
    } else if (envelope.type === "state") {
      scheduleLoad();
    }
  };

  app.ws.onclose = () => {
    setWebSocketStatus("Reconnecting");
    const delay = Math.min(10000, 1000 * 2 ** app.wsRetry);
    app.wsRetry = Math.min(app.wsRetry + 1, 4);
    window.setTimeout(connectWebSocket, delay);
  };

  app.ws.onerror = () => app.ws?.close();
}

function selectedDevice() {
  return app.devices.find((device) => device.device_id === app.selected);
}

function resizeCanvas(canvas, context) {
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  const width = Math.max(canvas.clientWidth, 1);
  const height = Math.max(canvas.clientHeight, 1);
  if (canvas.width !== Math.floor(width * ratio) || canvas.height !== Math.floor(height * ratio)) {
    canvas.width = Math.floor(width * ratio);
    canvas.height = Math.floor(height * ratio);
  }
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  return { width, height };
}

function drawChart() {
  const canvas = $("chart");
  const context = canvas.getContext("2d");
  const { width, height } = resizeCanvas(canvas, context);
  const device = selectedDevice();
  const online = device && runtimeFor(device).last_state !== "offline";
  const points = app.selected ? app.points.get(app.selected) || [] : [];
  context.clearRect(0, 0, width, height);

  $("chart-label").textContent = device ? device.name : "No sensor selected";
  $("chart-subtitle").textContent = online
    ? `Streaming movement from ${device.name}.`
    : device
      ? `${device.name} is currently offline.`
      : "Select a sensor to begin monitoring.";
  const empty = $("chart-empty");
  empty.classList.toggle("hidden", points.length > 0);
  empty.querySelector("strong").textContent = online
    ? "Waiting for live samples"
    : device
      ? "Sensor is offline"
      : "No live signal selected";
  empty.querySelector("p").textContent = online
    ? "Keep the Phyphox experiment running."
    : device
      ? "Start Phyphox and confirm the phone is reachable."
      : "Choose “View live” on a device card.";
  $("chart-status").classList.toggle("active", Boolean(online));
  $("chart-status").innerHTML = `<i></i>${online ? "Live" : device ? "Offline" : "Waiting"}`;
  $("chart-value").textContent = points.length ? points.at(-1).toFixed(2) : "0.00";
  if (!points.length) return;

  const padding = { top: 18, right: 18, bottom: 18, left: 18 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const maximum = Math.max(1.5, ...points) * 1.15;
  const coordinates = points.map((value, index) => ({
    x: padding.left + (index / Math.max(points.length - 1, 119)) * plotWidth,
    y: padding.top + plotHeight - (value / maximum) * plotHeight,
  }));

  const fill = context.createLinearGradient(0, padding.top, 0, height - padding.bottom);
  fill.addColorStop(0, "rgba(91, 140, 255, 0.28)");
  fill.addColorStop(1, "rgba(91, 140, 255, 0)");
  context.beginPath();
  context.moveTo(coordinates[0].x, height - padding.bottom);
  for (const point of coordinates) context.lineTo(point.x, point.y);
  context.lineTo(coordinates.at(-1).x, height - padding.bottom);
  context.closePath();
  context.fillStyle = fill;
  context.fill();

  context.beginPath();
  coordinates.forEach((point, index) => {
    if (index === 0) context.moveTo(point.x, point.y);
    else context.lineTo(point.x, point.y);
  });
  context.lineWidth = 2.2;
  context.lineJoin = "round";
  context.lineCap = "round";
  context.strokeStyle = "#79a2ff";
  context.shadowColor = "rgba(91, 140, 255, 0.35)";
  context.shadowBlur = 8;
  context.stroke();
  context.shadowBlur = 0;

  const last = coordinates.at(-1);
  context.beginPath();
  context.arc(last.x, last.y, 4, 0, Math.PI * 2);
  context.fillStyle = "#dce7ff";
  context.fill();
}

function audioConstructor() {
  return window.AudioContext || window.webkitAudioContext;
}

async function enableAudio() {
  const Audio = audioConstructor();
  if (!Audio) {
    showToast("This browser does not support Web Audio.", "error");
    return;
  }
  app.audioContext ||= new Audio();
  await app.audioContext.resume();
  $("enable-audio").classList.add("enabled");
  $("enable-audio").lastElementChild.textContent = "Alert sound on";
  if ("Notification" in window && Notification.permission === "default") {
    await Notification.requestPermission();
  }
  playBeep();
  showToast("Alert sound enabled.");
}

function playBeep() {
  if (!app.audioContext) return;
  const oscillator = app.audioContext.createOscillator();
  const gain = app.audioContext.createGain();
  oscillator.type = "sine";
  oscillator.frequency.setValueAtTime(760, app.audioContext.currentTime);
  oscillator.frequency.exponentialRampToValueAtTime(980, app.audioContext.currentTime + 0.14);
  gain.gain.setValueAtTime(0.0001, app.audioContext.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.1, app.audioContext.currentTime + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, app.audioContext.currentTime + 0.2);
  oscillator.connect(gain);
  gain.connect(app.audioContext.destination);
  oscillator.start();
  oscillator.stop(app.audioContext.currentTime + 0.21);
}

function startAlarm() {
  playBeep();
  if (!app.alarmTimer) app.alarmTimer = window.setInterval(playBeep, 900);
}

function stopAlarm() {
  if (app.alarmTimer) window.clearInterval(app.alarmTimer);
  app.alarmTimer = null;
}

function showAlarm(alert) {
  app.activeEvent = alert.event_id;
  $("alarm-text").textContent = `${alert.device_id} · motion score ${Number(alert.motion_score || 0).toFixed(2)}`;
  $("alarm").classList.remove("hidden");
  startAlarm();
  if ("Notification" in window && Notification.permission === "granted") {
    new Notification("Movement detected", {
      body: `${alert.device_id} requires attention.`,
      tag: alert.event_id,
    });
  }
}

function syncAlarmFromEvents() {
  const movement = app.events.find(
    (event) => event.state === "active" && event.type === "movement_detected",
  );
  if (!movement) {
    if (app.activeEvent) stopAlarm();
    app.activeEvent = null;
    $("alarm").classList.add("hidden");
    return;
  }
  app.activeEvent = movement.event_id;
  $("alarm-text").textContent = `${movement.device_id} · detected ${relativeTime(movement.started_at)}`;
  $("alarm").classList.remove("hidden");
}

function openCreateDialog() {
  app.editingId = null;
  $("register").reset();
  $("device-enabled").checked = true;
  $("device-id").disabled = false;
  $("dialog-title").textContent = "Add a phone sensor";
  $("dialog-description").textContent = "Enter the private address shown by Phyphox.";
  $("submit-device").textContent = "Add sensor";
  $("form-status").textContent = "";
  $("form-status").className = "form-status";
  updateSensitivityLabel();
  $("device-dialog").showModal();
  window.setTimeout(() => $("device-id").focus(), 50);
}

function openEditDialog(deviceId) {
  const device = app.devices.find((item) => item.device_id === deviceId);
  if (!device) return;
  app.editingId = deviceId;
  $("device-id").value = device.device_id;
  $("device-id").disabled = true;
  $("device-name").value = device.name;
  $("source-url").value = device.source_url;
  $("sensitivity").value = device.sensitivity;
  $("device-enabled").checked = device.enabled;
  $("dialog-title").textContent = "Edit phone sensor";
  $("dialog-description").textContent = `Update ${device.name}'s connection and detection settings.`;
  $("submit-device").textContent = "Save changes";
  $("form-status").textContent = "";
  $("form-status").className = "form-status";
  updateSensitivityLabel();
  $("device-dialog").showModal();
  window.setTimeout(() => $("device-name").focus(), 50);
}

function closeDeviceDialog() {
  $("device-dialog").close();
  app.editingId = null;
}

function updateSensitivityLabel() {
  $("sensitivity-value").textContent = Number($("sensitivity").value).toFixed(1);
}

async function saveDevice(event) {
  event.preventDefault();
  const editing = Boolean(app.editingId);
  const body = {
    name: $("device-name").value.trim(),
    source_url: $("source-url").value.trim(),
    sensitivity: Number($("sensitivity").value),
    enabled: $("device-enabled").checked,
  };
  if (!editing) body.device_id = $("device-id").value.trim();

  const endpoint = editing
    ? `/api/devices/${encodeURIComponent(app.editingId)}`
    : "/api/devices";
  const method = editing ? "PATCH" : "POST";
  $("submit-device").disabled = true;
  $("submit-device").textContent = editing ? "Saving…" : "Adding…";
  $("form-status").textContent = "";
  try {
    const saved = await request(endpoint, {
      method,
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    app.selected = saved.device_id;
    $("form-status").className = "form-status success";
    $("form-status").textContent = editing ? "Changes saved." : "Sensor added.";
    showToast(editing ? "Sensor settings updated." : "Phone sensor registered.");
    window.setTimeout(closeDeviceDialog, 280);
    await load({ quiet: true });
  } catch (error) {
    $("form-status").className = "form-status";
    $("form-status").textContent = error.message;
  } finally {
    $("submit-device").disabled = false;
    $("submit-device").textContent = editing ? "Save changes" : "Add sensor";
  }
}

function updateClock() {
  $("clock").textContent = new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date());
}

function toggleNavigation(open) {
  document.body.classList.toggle("nav-open", open);
}

$("devices").addEventListener("click", (event) => {
  if (event.target.closest("[data-open-register]")) {
    openCreateDialog();
    return;
  }
  const card = event.target.closest("[data-device]");
  if (!card) return;
  const deviceId = card.dataset.device;
  const action = event.target.closest("[data-action]")?.dataset.action;
  if (action === "arm" || action === "disarm") commandDevice(deviceId, action);
  else if (action === "edit") openEditDialog(deviceId);
  else if (action === "live") selectDevice(deviceId, { scroll: true });
  else selectDevice(deviceId);
});

$("events").addEventListener("click", (event) => {
  const button = event.target.closest("[data-event]");
  if (button) acknowledge(button.dataset.event);
});

$("register").addEventListener("submit", saveDevice);
$("sensitivity").addEventListener("input", updateSensitivityLabel);
$("event-filter").addEventListener("change", renderEvents);
$("refresh").addEventListener("click", () => load());
$("arm-all").addEventListener("click", () => commandAll("arm"));
$("disarm-all").addEventListener("click", () => commandAll("disarm"));
$("enable-audio").addEventListener("click", enableAudio);
$("ack").addEventListener("click", () => app.activeEvent && acknowledge(app.activeEvent));
$("open-register").addEventListener("click", openCreateDialog);
$("open-register-secondary").addEventListener("click", openCreateDialog);
$("guide-add").addEventListener("click", openCreateDialog);
$("close-dialog").addEventListener("click", closeDeviceDialog);
$("cancel-dialog").addEventListener("click", closeDeviceDialog);
$("device-dialog").addEventListener("click", (event) => {
  if (event.target === $("device-dialog")) closeDeviceDialog();
});
$("mobile-menu").addEventListener("click", () => toggleNavigation(true));
$("sidebar-backdrop").addEventListener("click", () => toggleNavigation(false));
document.querySelectorAll(".nav-item").forEach((link) => {
  link.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
    link.classList.add("active");
    toggleNavigation(false);
  });
});

let resizeTimer;
window.addEventListener("resize", () => {
  window.clearTimeout(resizeTimer);
  resizeTimer = window.setTimeout(drawChart, 100);
});

updateClock();
window.setInterval(updateClock, 1000);
window.setInterval(() => load({ quiet: true }), 10000);
load();
connectWebSocket();
