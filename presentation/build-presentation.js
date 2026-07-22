const pptxgen = require("pptxgenjs");
const path = require("node:path");

const isLight = process.argv.includes("--light");
const C = isLight
  ? {
      bg: "F7F9FC",
      bg2: "EDF2F8",
      panel: "FFFFFF",
      panel2: "EEF3FA",
      line: "C9D5E5",
      text: "14213D",
      muted: "5E708F",
      footer: "71819C",
      blue: "356AE6",
      blue2: "426EDC",
      cyan: "118AB2",
      green: "078F68",
      amber: "B97912",
      red: "D64255",
      purple: "7048CA",
      white: "FFFFFF",
      black: "08111F",
      device: "0B1424",
      deviceScreen: "111F35",
      deviceLine: "253957",
      screenshotFrame: "DDE5F0",
      screenshotLabel: "0B1424",
      warningPanel: "FFF7E3",
    }
  : {
      bg: "08111F",
      bg2: "0C1627",
      panel: "101C2F",
      panel2: "14233B",
      line: "263753",
      text: "F6F8FC",
      muted: "9AAAC4",
      footer: "7486A6",
      blue: "5B8CFF",
      blue2: "79A2FF",
      cyan: "53D5FF",
      green: "34D399",
      amber: "F6C453",
      red: "FF6677",
      purple: "A986FF",
      white: "FFFFFF",
      black: "02050A",
      device: "0B1424",
      deviceScreen: "111F35",
      deviceLine: "253957",
      screenshotFrame: "050A13",
      screenshotLabel: "0B1424",
      warningPanel: "251C15",
    };

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "Department of Computer Science and Engineering, MBSTU";
pptx.company = "Mawlana Bhashani Science and Technology University";
pptx.subject = "Phone-based IoT movement and anti-theft monitoring system";
pptx.title = `FailureAntyTheft Project Presentation${isLight ? " — Light Theme" : ""}`;
pptx.lang = "en-US";
pptx.theme = {
  headFontFace: "Arial",
  bodyFontFace: "Arial",
  lang: "en-US",
};
pptx.defineLayout({ name: "CUSTOM_WIDE", width: 13.333, height: 7.5 });
pptx.layout = "CUSTOM_WIDE";
pptx.defineSlideMaster({
  title: "CONTENT",
  background: { color: C.bg },
  objects: [],
  slideNumber: { x: 12.45, y: 7.05, w: 0.35, h: 0.18, color: C.footer, fontSize: 8, align: "right" },
});
pptx.layout = "CUSTOM_WIDE";

const S = pptx.ShapeType;
const logoPath = path.join(__dirname, "assets", "mbstu-logo.png");
const dashboardPath = path.join(__dirname, "assets", "dashboard-top.png");
const outputPath = path.join(
  __dirname,
  isLight ? "FailureAntyTheft-Presentation-Light.pptx" : "FailureAntyTheft-Presentation.pptx",
);

const shadows = {
  panel: { type: "outer", color: "000000", opacity: isLight ? 0.12 : 0.22, blur: 2, angle: 45, distance: 1 },
  glow: { type: "outer", color: C.blue, opacity: 0.18, blur: 3, angle: 45, distance: 0.5 },
};

function addText(slide, text, x, y, w, h, options = {}) {
  slide.addText(text, {
    x,
    y,
    w,
    h,
    fontFace: "Arial",
    fontSize: 16,
    color: C.text,
    margin: 0,
    breakLine: false,
    valign: "mid",
    fit: "shrink",
    ...options,
  });
}

function addRect(slide, x, y, w, h, fill, line = C.line, radius = true, options = {}) {
  slide.addShape(radius ? S.roundRect : S.rect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.08,
    fill: { color: fill },
    line: { color: line, width: 1 },
    ...options,
  });
}

function addLine(slide, x, y, w, h, color = C.blue, width = 1.5, arrow = false, dash = "solid") {
  slide.addShape(S.line, {
    x,
    y,
    w,
    h,
    line: {
      color,
      width,
      dash,
      beginArrowType: "none",
      endArrowType: arrow ? "triangle" : "none",
    },
  });
}

function addCircle(slide, x, y, d, fill, line = fill, transparency = 0) {
  slide.addShape(S.ellipse, {
    x,
    y,
    w: d,
    h: d,
    fill: { color: fill, transparency },
    line: { color: line, transparency: line === fill ? transparency : 0, width: 1 },
  });
}

function addPill(slide, text, x, y, w, color = C.blue, options = {}) {
  addRect(slide, x, y, w, 0.34, C.panel2, color, true);
  addText(slide, text, x + 0.08, y + 0.02, w - 0.16, 0.28, {
    fontSize: 9,
    bold: true,
    color,
    align: "center",
    charSpacing: 0.7,
    ...options,
  });
}

function addHeader(slide, number, kicker, title, subtitle) {
  addText(slide, String(number).padStart(2, "0"), 0.55, 0.42, 0.42, 0.3, {
    fontSize: 10,
    bold: true,
    color: C.blue2,
    charSpacing: 1.2,
  });
  addLine(slide, 0.98, 0.57, 0.55, 0, C.line, 1);
  addText(slide, kicker.toUpperCase(), 1.67, 0.4, 3.6, 0.32, {
    fontSize: 9,
    bold: true,
    color: C.blue2,
    charSpacing: 1.5,
  });
  addText(slide, title, 0.55, 0.88, 12.1, 0.55, { fontSize: 27, bold: true });
  if (subtitle) {
    addText(slide, subtitle, 0.55, 1.48, 11.9, 0.4, { fontSize: 11.5, color: C.muted });
  }
  addText(slide, "FailureAntyTheft", 0.55, 7.05, 2.2, 0.18, {
    fontSize: 8,
    bold: true,
    color: C.footer,
  });
}

function addNotes(slide, notes) {
  slide.addNotes(notes);
}

function addBulletList(slide, items, x, y, w, options = {}) {
  const rowH = options.rowH || 0.62;
  items.forEach((item, index) => {
    const yy = y + index * rowH;
    addCircle(slide, x, yy + 0.14, 0.15, options.bulletColor || C.blue, options.bulletColor || C.blue);
    addText(slide, item.title, x + 0.28, yy, w - 0.28, 0.26, {
      fontSize: options.titleSize || 14,
      bold: true,
      color: options.titleColor || C.text,
    });
    if (item.detail) {
      addText(slide, item.detail, x + 0.28, yy + 0.27, w - 0.28, rowH - 0.28, {
        fontSize: options.detailSize || 10.5,
        color: C.muted,
        valign: "top",
      });
    }
  });
}

function addIconBadge(slide, label, x, y, d, color, symbol) {
  addCircle(slide, x, y, d, color, color, 84);
  addText(slide, symbol, x, y, d, d, { fontSize: d * 15, bold: true, color, align: "center" });
  if (label) addText(slide, label, x - 0.15, y + d + 0.07, d + 0.3, 0.22, { fontSize: 8, color: C.muted, align: "center" });
}

function addPhone(slide, x, y, w, h, color = C.blue) {
  addRect(slide, x, y, w, h, C.device, color, true, { line: { color, width: 1.5 }, shadow: shadows.glow });
  addRect(slide, x + 0.13, y + 0.35, w - 0.26, h - 0.62, C.deviceScreen, C.deviceLine, true);
  addRect(slide, x + w * 0.33, y + 0.13, w * 0.34, 0.08, color, color, true);
  addCircle(slide, x + w / 2 - 0.07, y + h - 0.2, 0.14, color, color, 5);
  addLine(slide, x + 0.25, y + h * 0.6, w * 0.18, -0.15, C.green, 1.5);
  addLine(slide, x + w * 0.43, y + h * 0.45, w * 0.18, 0.22, C.green, 1.5);
  addLine(slide, x + w * 0.61, y + h * 0.67, w * 0.18, -0.35, C.green, 1.5);
}

function addShield(slide, x, y, size, color = C.blue) {
  slide.addShape(S.pentagon, {
    x,
    y,
    w: size,
    h: size * 1.08,
    rotate: 180,
    fill: { color, transparency: 82 },
    line: { color, width: 1.8 },
  });
  addLine(slide, x + size * 0.28, y + size * 0.52, size * 0.17, size * 0.18, C.white, 2.2);
  addLine(slide, x + size * 0.45, y + size * 0.7, size * 0.3, -size * 0.35, C.white, 2.2);
}

function addNode(slide, x, y, w, h, title, detail, color, symbol) {
  addRect(slide, x, y, w, h, C.panel, C.line, true, { shadow: shadows.panel });
  addCircle(slide, x + 0.22, y + 0.25, 0.44, color, color, 82);
  addText(slide, symbol, x + 0.22, y + 0.25, 0.44, 0.44, { fontSize: 16, bold: true, color, align: "center" });
  addText(slide, title, x + 0.78, y + 0.18, w - 0.96, 0.34, { fontSize: 13, bold: true });
  addText(slide, detail, x + 0.78, y + 0.55, w - 0.96, h - 0.68, { fontSize: 9.5, color: C.muted, valign: "top" });
}

// Slide 1 — Cover
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, { x: 0, y: 0, w: 13.333, h: 7.5, fill: { color: C.bg }, line: { transparency: 100 } });
  slide.addShape(S.ellipse, { x: 8.35, y: -2.2, w: 7.0, h: 7.0, fill: { color: C.blue, transparency: 88 }, line: { transparency: 100 } });
  slide.addShape(S.ellipse, { x: 9.55, y: 3.4, w: 4.8, h: 4.8, fill: { color: C.purple, transparency: 91 }, line: { transparency: 100 } });
  for (let i = 0; i < 5; i += 1) {
    addCircle(slide, 8.55 + i * 0.83, 1.07 + (i % 2) * 0.42, 0.09, C.cyan, C.cyan, 15);
    if (i < 4) addLine(slide, 8.64 + i * 0.83, 1.12 + (i % 2) * 0.42, 0.74, (i % 2 === 0 ? 0.42 : -0.42), C.line, 1);
  }
  slide.addImage({ path: logoPath, x: 0.72, y: 0.48, w: 0.78, h: 0.78 });
  addText(slide, "MAWLANA BHASHANI SCIENCE AND TECHNOLOGY UNIVERSITY", 1.67, 0.47, 6.0, 0.32, {
    fontSize: 10,
    bold: true,
    color: C.text,
    charSpacing: 0.7,
  });
  addText(slide, "Department of Computer Science and Engineering", 1.67, 0.82, 5.4, 0.26, {
    fontSize: 10,
    color: C.muted,
  });
  addPill(slide, "PROJECT PRESENTATION", 0.72, 1.72, 1.75, C.cyan);
  addText(slide, "FailureAntyTheft", 0.72, 2.28, 7.35, 0.84, { fontSize: 39, bold: true });
  addText(slide, "A phone-based IoT movement detection and anti-theft alert system", 0.72, 3.2, 6.9, 0.76, {
    fontSize: 20,
    color: C.blue2,
    bold: false,
    valign: "top",
  });
  addText(slide, "Local-first  •  Real-time  •  No dedicated sensor hardware", 0.72, 4.17, 6.6, 0.32, {
    fontSize: 11,
    color: C.muted,
  });
  addRect(slide, 0.72, 5.55, 6.35, 0.9, C.panel, C.line, true);
  addText(slide, "PRESENTED BY", 0.98, 5.72, 1.2, 0.22, { fontSize: 8.5, bold: true, color: C.blue2, charSpacing: 1.2 });
  addText(slide, "[Presenter Name]  •  [Student ID]", 0.98, 5.98, 4.2, 0.25, { fontSize: 13, bold: true });
  addText(slide, "July 2026", 5.35, 5.86, 1.4, 0.28, { fontSize: 10, color: C.muted, align: "right" });
  addPhone(slide, 9.0, 2.05, 1.75, 3.55, C.blue);
  addShield(slide, 10.38, 3.0, 1.7, C.green);
  addCircle(slide, 8.45, 5.38, 0.28, C.red, C.red, 10);
  addLine(slide, 8.72, 5.52, 0.9, -0.4, C.red, 1.3, true, "dash");
  addText(slide, "MOTION", 8.1, 5.72, 1.0, 0.22, { fontSize: 8, bold: true, color: C.red, align: "center" });
  addText(slide, "Official MBSTU logo source: mbstu.ac.bd", 0.72, 7.06, 3.2, 0.18, { fontSize: 7.5, color: C.footer });
  addNotes(slide, "Good morning/afternoon. Our project is FailureAntyTheft, a local IoT anti-theft system that converts ordinary smartphones into wireless motion sensors. Add presenter names and student IDs on this slide before presenting.");
}

// Slide 2 — Problem
{
  const slide = pptx.addSlide("CONTENT");
  addHeader(slide, 2, "Problem & opportunity", "Why build this system?", "Portable assets need monitoring, but dedicated IoT hardware adds cost and setup effort.");
  addRect(slide, 0.55, 2.07, 4.1, 4.48, C.panel, C.line, true, { shadow: shadows.panel });
  addText(slide, "The core problem", 0.87, 2.38, 2.8, 0.35, { fontSize: 18, bold: true });
  addBulletList(slide, [
    { title: "Portable assets are easy to move", detail: "Bags, drawers, bicycles and lab equipment may be unattended." },
    { title: "Raw sensor noise causes false alarms", detail: "A useful detector must distinguish noise from sustained movement." },
    { title: "Commercial hardware is unnecessary", detail: "Most smartphones already contain accelerometers, Wi-Fi and batteries." },
    { title: "Cloud dependence adds friction", detail: "A classroom demo should work privately on a local network." },
  ], 0.9, 2.97, 3.4, { rowH: 0.82, bulletColor: C.red, titleSize: 12.5, detailSize: 9.3 });

  addText(slide, "Opportunity", 5.12, 2.24, 2.2, 0.35, { fontSize: 14, bold: true, color: C.green });
  addText(slide, "Reuse hardware people already own", 5.12, 2.68, 6.7, 0.55, { fontSize: 25, bold: true });
  addText(slide, "Turn a phone into a sensor node and a laptop into the complete local monitoring platform.", 5.12, 3.31, 6.9, 0.52, { fontSize: 13, color: C.muted });
  addPhone(slide, 5.25, 4.25, 1.15, 1.9, C.cyan);
  addLine(slide, 6.56, 5.19, 1.25, 0, C.blue, 2, true);
  addNode(slide, 7.95, 4.46, 2.1, 1.45, "Local server", "Collect, detect, store", C.purple, "≋");
  addLine(slide, 10.2, 5.19, 1.0, 0, C.blue, 2, true);
  addNode(slide, 11.3, 4.46, 1.48, 1.45, "Alert", "See + hear", C.red, "!");
  addPill(slide, "LOW COST", 5.15, 6.23, 1.25, C.green);
  addPill(slide, "PRIVATE LAN", 6.54, 6.23, 1.42, C.blue2);
  addPill(slide, "REUSABLE", 8.1, 6.23, 1.25, C.purple);
  addNotes(slide, "The project starts from a practical observation: phones already contain the required sensing and networking hardware. The engineering challenge is not simply reading acceleration; it is producing a reliable, understandable alert without dedicated hardware or cloud services.");
}

// Slide 3 — Solution overview
{
  const slide = pptx.addSlide("CONTENT");
  addHeader(slide, 3, "Solution overview", "One phone. One local server. One clear response.", "FailureAntyTheft covers the complete IoT loop: sense, communicate, process, store, visualize and act.");
  const cards = [
    { x: 0.55, title: "1  SENSE", color: C.cyan, symbol: "≈", body: "Phyphox exposes live X, Y and Z acceleration plus device time from each phone." },
    { x: 4.46, title: "2  DECIDE", color: C.purple, symbol: "◇", body: "A deterministic detector calibrates a baseline, filters noise and verifies sustained movement." },
    { x: 8.37, title: "3  RESPOND", color: C.red, symbol: "!", body: "The dashboard updates in real time, persists the event and plays a repeating siren." },
  ];
  cards.forEach((card) => {
    addRect(slide, card.x, 2.18, 3.56, 2.6, C.panel, C.line, true, { shadow: shadows.panel });
    addIconBadge(slide, "", card.x + 0.3, 2.48, 0.58, card.color, card.symbol);
    addText(slide, card.title, card.x + 1.06, 2.5, 2.08, 0.3, { fontSize: 11, bold: true, color: card.color, charSpacing: 0.8 });
    addText(slide, card.body, card.x + 0.3, 3.26, 2.96, 1.08, { fontSize: 13, color: C.text, valign: "top" });
  });
  addRect(slide, 0.55, 5.13, 11.38, 1.32, C.panel2, C.line, true);
  addText(slide, "DESIGN PRINCIPLE", 0.86, 5.39, 1.55, 0.22, { fontSize: 8.5, bold: true, color: C.blue2, charSpacing: 1.2 });
  addText(slide, "Local-first by default", 2.55, 5.27, 2.6, 0.4, { fontSize: 17, bold: true });
  addText(slide, "No paid cloud, no custom mobile app and no silent fallback when MQTT is configured.", 5.15, 5.29, 6.3, 0.42, { fontSize: 12, color: C.muted });
  addPill(slide, "MULTI-PHONE", 2.55, 5.83, 1.4, C.cyan);
  addPill(slide, "REAL-TIME", 4.08, 5.83, 1.2, C.green);
  addPill(slide, "AUDITABLE", 5.42, 5.83, 1.2, C.amber);
  addNotes(slide, "The solution is deliberately simple for the operator while remaining modular internally. Phones sense, the server decides, and the dashboard responds. The whole system remains on the local network.");
}

// Slide 4 — Architecture
{
  const slide = pptx.addSlide("CONTENT");
  addHeader(slide, 4, "System architecture", "A modular local IoT pipeline", "Typed messages separate collection, detection, persistence and presentation while one FastAPI process supervises the application.");

  addText(slide, "SENSOR LAYER", 0.55, 2.07, 1.5, 0.23, { fontSize: 8, bold: true, color: C.cyan, charSpacing: 1.1 });
  addPhone(slide, 0.72, 2.55, 0.88, 1.62, C.cyan);
  addPhone(slide, 1.25, 3.35, 0.88, 1.62, C.blue);
  addText(slide, "Phones + Phyphox", 0.55, 5.2, 1.9, 0.28, { fontSize: 12, bold: true, align: "center" });
  addText(slide, "HTTP /get polling", 0.55, 5.5, 1.9, 0.24, { fontSize: 9, color: C.muted, align: "center" });

  addLine(slide, 2.25, 3.67, 0.63, 0, C.blue, 2, true);
  addNode(slide, 2.93, 2.9, 1.85, 1.55, "Collector", "Validate LAN URL\nCursor + deduplication\nNormalize telemetry", C.cyan, "⇣");
  addLine(slide, 4.86, 3.67, 0.57, 0, C.blue, 2, true);

  slide.addShape(S.hexagon, { x: 5.47, y: 2.78, w: 1.66, h: 1.78, fill: { color: C.purple, transparency: 80 }, line: { color: C.purple, width: 1.6 }, shadow: shadows.glow });
  addText(slide, "MQTT", 5.7, 3.16, 1.2, 0.35, { fontSize: 18, bold: true, color: C.purple, align: "center" });
  addText(slide, "Mosquitto\ntyped topics", 5.72, 3.58, 1.16, 0.58, { fontSize: 9, color: C.muted, align: "center" });
  addLine(slide, 7.14, 3.67, 0.56, 0, C.blue, 2, true);

  addNode(slide, 7.76, 2.47, 2.2, 2.4, "Per-device runtime", "Ordered inbox\nPure detector\nState transitions\nAlert publication", C.green, "◆");
  addLine(slide, 9.96, 3.12, 0.68, -0.55, C.green, 1.6, true);
  addLine(slide, 9.96, 4.18, 0.68, 0.58, C.amber, 1.6, true);
  addNode(slide, 10.69, 2.02, 2.08, 1.34, "FastAPI + WS", "Commands and live UI", C.blue, "↯");
  addNode(slide, 10.69, 4.42, 2.08, 1.34, "SQLite", "Devices, state, events", C.amber, "▤");

  addLine(slide, 11.72, 3.36, 0, 0.87, C.blue2, 1.4, true, "dash");
  addText(slide, "HTTP queries", 11.86, 3.68, 0.75, 0.2, { fontSize: 7.5, color: C.muted, rotate: 90, align: "center" });
  addRect(slide, 4.28, 5.65, 5.18, 0.74, C.panel2, C.line, true);
  addText(slide, "Browser dashboard", 4.55, 5.83, 1.55, 0.25, { fontSize: 12, bold: true });
  addText(slide, "Live chart  •  controls  •  siren  •  event history", 6.15, 5.83, 2.98, 0.25, { fontSize: 10, color: C.muted, align: "right" });
  addLine(slide, 10.69, 2.69, -1.2, 3.07, C.blue, 1.7, true);
  addLine(slide, 4.45, 5.65, 1.1, -1.16, C.blue, 1.3, true, "dash");
  addText(slide, "arm / disarm / acknowledge", 4.55, 4.81, 2.4, 0.23, { fontSize: 8, color: C.blue2 });
  addNotes(slide, "Explain the architecture from left to right. Phyphox is polled over HTTP. The collector validates and normalizes readings. MQTT decouples components. Each phone has its own ordered runtime and deterministic detector. SQLite is the durable authority. FastAPI and WebSocket serve the dashboard and accept commands. The browser produces the audible alarm.");
}

// Slide 5 — Data flow
{
  const slide = pptx.addSlide("CONTENT");
  addHeader(slide, 5, "Sensor-to-alert flow", "What happens after the phone moves?", "Every stage removes ambiguity before the operator is interrupted.");
  const steps = [
    ["01", "Sample", "Phyphox emits time + X/Y/Z", C.cyan],
    ["02", "Collect", "Poll, validate and deduplicate", C.blue],
    ["03", "Normalize", "Publish typed telemetry", C.purple],
    ["04", "Score", "Magnitude → EMA → baseline delta", C.green],
    ["05", "Confirm", "3 crossings inside 0.5 s", C.amber],
    ["06", "Alert", "Persist, push UI and sound siren", C.red],
  ];
  steps.forEach((step, index) => {
    const x = 0.55 + index * 2.05;
    addCircle(slide, x + 0.53, 2.27, 0.62, step[3], step[3], 80);
    addText(slide, step[0], x + 0.53, 2.27, 0.62, 0.62, { fontSize: 13, bold: true, color: step[3], align: "center" });
    if (index < steps.length - 1) addLine(slide, x + 1.18, 2.58, 0.82, 0, C.line, 1.6, true);
    addText(slide, step[1], x + 0.04, 3.1, 1.6, 0.3, { fontSize: 14, bold: true, align: "center" });
    addText(slide, step[2], x - 0.02, 3.48, 1.76, 0.75, { fontSize: 9.5, color: C.muted, align: "center", valign: "top" });
  });
  addRect(slide, 0.55, 4.65, 11.96, 1.45, C.panel, C.line, true, { shadow: shadows.panel });
  addText(slide, "WHY DEVICE TIME MATTERS", 0.85, 4.93, 2.0, 0.23, { fontSize: 8.5, bold: true, color: C.blue2, charSpacing: 1 });
  addText(slide, "Buffered samples are judged by the phone’s sample time—not by clustered HTTP arrival time.", 0.85, 5.27, 6.4, 0.45, { fontSize: 16, bold: true });
  addText(slide, "This preserves the sustained-movement rule and prevents network timing from changing the detector’s decision.", 7.62, 5.04, 4.4, 0.65, { fontSize: 11, color: C.muted, valign: "mid" });
  addNotes(slide, "Walk through the six stages. Emphasize that one noisy sample is not enough. The collector uses a cursor and device time for deduplication. The detector requires three threshold crossings within half a second before creating an alert.");
}

// Slide 6 — Detector and state machine
{
  const slide = pptx.addSlide("CONTENT");
  addHeader(slide, 6, "Detection logic", "Calibrate first. Filter noise. Confirm sustained movement.", "The detector is a pure, replayable state machine with no network, database or clock dependencies.");
  const states = [
    { x: 0.65, y: 2.34, w: 1.45, label: "OFFLINE", color: C.muted },
    { x: 2.55, y: 2.34, w: 1.55, label: "DISARMED", color: C.blue2 },
    { x: 4.55, y: 2.34, w: 1.7, label: "CALIBRATING", color: C.purple },
    { x: 6.72, y: 2.34, w: 1.4, label: "ARMED", color: C.green },
    { x: 8.57, y: 2.34, w: 1.72, label: "SUSPICIOUS", color: C.amber },
    { x: 10.75, y: 2.34, w: 1.52, label: "ALARM", color: C.red },
  ];
  states.forEach((state, index) => {
    addRect(slide, state.x, state.y, state.w, 0.86, C.panel, state.color, true, { line: { color: state.color, width: 1.4 } });
    addCircle(slide, state.x + 0.16, state.y + 0.33, 0.2, state.color, state.color, 0);
    addText(slide, state.label, state.x + 0.43, state.y + 0.2, state.w - 0.52, 0.46, { fontSize: 10.2, bold: true, color: state.color, align: "center" });
    if (index < states.length - 1) addLine(slide, state.x + state.w, state.y + 0.43, states[index + 1].x - (state.x + state.w), 0, C.line, 1.6, true);
  });
  addText(slide, "valid sample", 1.74, 1.98, 1.1, 0.2, { fontSize: 7.5, color: C.muted, align: "center" });
  addText(slide, "arm", 3.94, 1.98, 0.5, 0.2, { fontSize: 7.2, color: C.muted, align: "center" });
  addText(slide, "baseline ready", 5.97, 1.98, 0.92, 0.2, { fontSize: 7.2, color: C.muted, align: "center" });
  addText(slide, "score > threshold", 7.85, 1.98, 1.25, 0.2, { fontSize: 7.5, color: C.muted, align: "center" });
  addText(slide, "3 crossings / 0.5 s", 9.94, 1.98, 1.25, 0.2, { fontSize: 7.5, color: C.muted, align: "center" });

  addLine(slide, 11.5, 3.22, -8.12, 0.78, C.red, 1.25, true, "dash");
  addRect(slide, 5.86, 3.62, 2.02, 0.29, C.bg, C.red, true, { line: { color: C.red, transparency: 55, width: 0.7 } });
  addText(slide, "ACKNOWLEDGE → DISARMED", 5.94, 3.66, 1.86, 0.2, { fontSize: 7.2, bold: true, color: C.red, align: "center" });
  addPill(slide, "SCORE NORMAL → ARMED", 8.2, 3.48, 1.72, C.amber, { fontSize: 6.8 });

  addRect(slide, 0.65, 4.42, 5.65, 1.55, C.panel, C.line, true);
  addText(slide, "CALIBRATION", 0.95, 4.67, 1.28, 0.22, { fontSize: 8.5, bold: true, color: C.purple, charSpacing: 1 });
  addText(slide, "5 s placement delay + 2 s sampling window", 0.95, 5.05, 4.5, 0.33, { fontSize: 16, bold: true });
  addText(slide, "Median magnitude becomes the baseline; excessive variance rejects calibration.", 0.95, 5.47, 4.9, 0.27, { fontSize: 10, color: C.muted });

  addRect(slide, 6.67, 4.42, 5.6, 1.55, C.panel, C.line, true);
  addText(slide, "MOTION SCORE", 6.97, 4.67, 1.45, 0.22, { fontSize: 8.5, bold: true, color: C.green, charSpacing: 1 });
  addText(slide, "score = | EMA(√(x² + y² + z²)) − baseline |", 6.97, 5.04, 4.8, 0.36, { fontSize: 16, bold: true });
  addText(slide, "Sensitivity sets the threshold; α = 0.35 smooths short sensor noise.", 6.97, 5.48, 4.8, 0.27, { fontSize: 10, color: C.muted });
  addNotes(slide, "The detector states make behavior predictable. After arming, the operator gets five seconds to place the phone, followed by a two-second stable calibration. The detector computes acceleration magnitude, smooths it with an exponential moving average, compares it with the median baseline and requires three crossings within 0.5 seconds. Acknowledgement disarms the device.");
}

// Slide 7 — Dashboard
{
  const slide = pptx.addSlide("CONTENT");
  addHeader(slide, 7, "Operator experience", "A professional real-time security console", "The interface turns low-level sensor data into one clear operational view.");
  addRect(slide, 0.55, 2.03, 8.5, 4.72, C.screenshotFrame, C.line, true, { shadow: shadows.panel });
  slide.addImage({ path: dashboardPath, x: 0.68, y: 2.16, w: 8.24, h: 4.46 });
  addRect(slide, 0.79, 6.3, 1.83, 0.25, C.screenshotLabel, C.line, true);
  addText(slide, "LIVE DASHBOARD CAPTURE", 0.89, 6.33, 1.63, 0.18, { fontSize: 6.8, bold: true, color: C.blue2, charSpacing: 0.8, align: "center" });

  addText(slide, "Designed for fast decisions", 9.48, 2.12, 3.1, 0.38, { fontSize: 18, bold: true });
  addBulletList(slide, [
    { title: "At-a-glance health", detail: "Online, armed and active-alert counts." },
    { title: "Independent sensors", detail: "Arm, disarm, edit and monitor each phone." },
    { title: "Live WebSocket chart", detail: "Selected-device motion score without raw-data overload." },
    { title: "Actionable alarm", detail: "Visual banner, repeating siren and acknowledge workflow." },
    { title: "Auditable history", detail: "Persistent events with CSV export." },
  ], 9.5, 2.74, 3.0, { rowH: 0.74, bulletColor: C.blue2, titleSize: 11.5, detailSize: 8.7 });
  addNotes(slide, "This is a live capture of the implemented dashboard. Point out the health summary, device cards, live chart, quick-start guide, event history and sound control. The interface intentionally sends chart-ready motion scores rather than overwhelming the browser with raw XYZ data.");
}

// Slide 8 — Technology stack
{
  const slide = pptx.addSlide("CONTENT");
  addHeader(slide, 8, "Technology stack", "Simple tools, clear responsibilities", "Each technology was selected for local reliability, testability and low operational cost.");
  const stack = [
    ["PHONE SENSOR", "Phyphox", "Accelerometer access + remote HTTP API", C.cyan, "P"],
    ["BACKEND", "Python + FastAPI + asyncio", "Lifecycle, REST commands and WebSocket delivery", C.blue, "Py"],
    ["MESSAGING", "MQTT + Mosquitto", "Typed publish/subscribe topics and reconnect behavior", C.purple, "M"],
    ["PERSISTENCE", "SQLite (WAL)", "Device configuration, runtime state and event history", C.amber, "DB"],
    ["FRONT END", "HTML + CSS + JavaScript", "Responsive dashboard, canvas chart and Web Audio siren", C.green, "UI"],
    ["QUALITY", "Pytest + Ruff + mypy + Docker", "Replay tests, static checks and reproducible broker", C.red, "✓"],
  ];
  stack.forEach((item, index) => {
    const col = index % 2;
    const row = Math.floor(index / 2);
    const x = 0.55 + col * 6.08;
    const y = 2.08 + row * 1.43;
    addRect(slide, x, y, 5.72, 1.13, C.panel, C.line, true, { shadow: shadows.panel });
    addCircle(slide, x + 0.25, y + 0.26, 0.61, item[3], item[3], 82);
    addText(slide, item[4], x + 0.25, y + 0.26, 0.61, 0.61, { fontSize: item[4].length > 1 ? 11 : 17, bold: true, color: item[3], align: "center" });
    addText(slide, item[0], x + 1.03, y + 0.18, 1.42, 0.2, { fontSize: 7.5, bold: true, color: item[3], charSpacing: 1 });
    addText(slide, item[1], x + 1.03, y + 0.42, 4.25, 0.27, { fontSize: 13, bold: true });
    addText(slide, item[2], x + 1.03, y + 0.73, 4.25, 0.22, { fontSize: 8.8, color: C.muted });
  });
  addRect(slide, 0.55, 6.46, 11.8, 0.32, C.panel2, C.line, true);
  addText(slide, "Deployment: one laptop runs the application, Mosquitto, SQLite and dashboard; phones remain sensor nodes on the same private LAN.", 0.75, 6.5, 11.4, 0.22, { fontSize: 9.2, color: C.muted, align: "center" });
  addNotes(slide, "The stack demonstrates a complete IoT architecture without overcomplicating deployment. Python and asyncio supervise the components, MQTT models IoT messaging, SQLite avoids another server, and the browser supplies a platform-independent control surface and siren.");
}

// Slide 9 — Validation
{
  const slide = pptx.addSlide("CONTENT");
  addHeader(slide, 9, "Engineering evidence", "Verified in tests—and against a real phone", "Automated replay protects detector behavior while live checks prove the Phyphox integration path.");
  const metrics = [
    ["105", "tests passed", "1 environment-gated skip", C.green],
    ["84%", "coverage at handoff", "Core detector: 94%", C.blue],
    ["200", "live /config status", "Phone measuring = true", C.cyan],
    ["4", "verified buffers", "acc_time + accX/Y/Z", C.purple],
  ];
  metrics.forEach((metric, index) => {
    const x = 0.55 + index * 3.05;
    addRect(slide, x, 2.12, 2.7, 1.66, C.panel, C.line, true, { shadow: shadows.panel });
    addText(slide, metric[0], x + 0.22, 2.34, 2.26, 0.58, { fontSize: 29, bold: true, color: metric[3] });
    addText(slide, metric[1], x + 0.22, 2.96, 2.26, 0.25, { fontSize: 11.5, bold: true });
    addText(slide, metric[2], x + 0.22, 3.29, 2.26, 0.22, { fontSize: 8.7, color: C.muted });
  });

  addRect(slide, 0.55, 4.16, 7.32, 2.18, C.panel, C.line, true);
  addText(slide, "Test strategy", 0.86, 4.45, 2.0, 0.33, { fontSize: 17, bold: true });
  addBulletList(slide, [
    { title: "Pure detector unit tests", detail: "Calibration, noise filtering, crossings and transitions." },
    { title: "Recorded-shape replay", detail: "Stationary data stays quiet; movement triggers exactly once." },
    { title: "Integration checks", detail: "Repository, API, runtime, WebSocket assets and live MQTT round-trip." },
  ], 0.88, 4.9, 6.42, { rowH: 0.43, bulletColor: C.green, titleSize: 10.5, detailSize: 8.5 });

  addRect(slide, 8.22, 4.16, 4.13, 2.18, C.panel2, C.blue, true, { line: { color: C.blue, width: 1.4 } });
  addText(slide, "LIVE PHONE RESULT", 8.54, 4.48, 1.8, 0.22, { fontSize: 8, bold: true, color: C.blue2, charSpacing: 1 });
  addText(slide, "Saikat", 8.54, 4.88, 2.0, 0.36, { fontSize: 21, bold: true });
  addPill(slide, "DISARMED • ONLINE", 10.18, 4.89, 1.72, C.green, { fontSize: 7.5 });
  addText(slide, "The collector’s default time buffer was corrected from t to acc_time using the phone’s live /config evidence.", 8.54, 5.44, 3.33, 0.58, { fontSize: 10, color: C.muted, valign: "top" });
  addNotes(slide, "This slide separates synthetic evidence from physical evidence. The current suite has 105 passing tests and one environment-gated MQTT test. A live phone returned HTTP 200, confirmed measurement, exposed the four expected buffers and transitioned online in the dashboard. Coverage figures are from the final handoff report.");
}

// Slide 10 — Demo
{
  const slide = pptx.addSlide("CONTENT");
  addHeader(slide, 10, "Live demonstration", "A seven-step proof in under two minutes", "Use a private hotspot or Wi-Fi network where the phone and laptop can communicate directly.");
  const demo = [
    ["1", "START", "Open Acceleration with g and enable remote access", C.cyan],
    ["2", "CONNECT", "Register the displayed private URL", C.blue],
    ["3", "VERIFY", "Device appears Disarmed—not Offline", C.green],
    ["4", "SOUND", "Click Sound off and hear the test siren", C.purple],
    ["5", "ARM", "Keep still for 5 s placement + 2 s calibration", C.amber],
    ["6", "MOVE", "Move the phone; observe Alarm + siren", C.red],
    ["7", "CLOSE", "Acknowledge, disarm and show event history", C.green],
  ];
  demo.forEach((item, index) => {
    const col = index < 4 ? 0 : 1;
    const row = col === 0 ? index : index - 4;
    const x = col === 0 ? 0.65 : 6.77;
    const y = 2.02 + row * 1.03;
    addCircle(slide, x, y + 0.04, 0.53, item[3], item[3], 80);
    addText(slide, item[0], x, y + 0.04, 0.53, 0.53, { fontSize: 12, bold: true, color: item[3], align: "center" });
    addText(slide, item[1], x + 0.76, y, 1.1, 0.25, { fontSize: 8.5, bold: true, color: item[3], charSpacing: 1 });
    addText(slide, item[2], x + 0.76, y + 0.28, 4.85, 0.35, { fontSize: 11.5, bold: true });
    if (row < (col === 0 ? 3 : 2)) addLine(slide, x + 0.265, y + 0.62, 0, 0.39, C.line, 1.3, true);
  });
  addRect(slide, 6.77, 5.36, 5.4, 1.02, C.warningPanel, C.amber, true, { line: { color: C.amber, width: 1.2 } });
  addText(slide, "DEMO SAFETY NET", 7.05, 5.56, 1.58, 0.22, { fontSize: 8, bold: true, color: C.amber, charSpacing: 1 });
  addText(slide, "Keep a screenshot and event-history explanation ready if venue Wi-Fi isolates devices.", 8.64, 5.46, 3.2, 0.48, { fontSize: 10.5, color: C.text });
  addNotes(slide, "This is the recommended live demo order. Use a personal hotspot if institutional Wi-Fi blocks peer-to-peer traffic. Wait the full seven seconds after arming before movement. If the live network fails, use the dashboard screenshot and explain the verified live-phone report rather than improvising configuration changes on stage.");
}

// Slide 11 — Limitations and roadmap
{
  const slide = pptx.addSlide("CONTENT");
  addHeader(slide, 11, "Honest scope", "What the prototype does—and what comes next", "The current system is presentation-ready on a trusted LAN, but it is not a certified security product.");
  addRect(slide, 0.55, 2.08, 5.55, 4.42, C.panel, C.red, true, { line: { color: C.red, transparency: 45, width: 1.2 } });
  addText(slide, "CURRENT LIMITATIONS", 0.88, 2.41, 2.15, 0.25, { fontSize: 9, bold: true, color: C.red, charSpacing: 1.2 });
  addBulletList(slide, [
    { title: "Trusted private LAN only", detail: "No authentication or TLS for public deployment." },
    { title: "Browser is the alarm endpoint", detail: "The tab must remain open with audio enabled." },
    { title: "Default Phyphox profile", detail: "Custom experiments may expose different buffer names." },
    { title: "Prototype acceptance scope", detail: "One live phone verified; multi-phone physical stress testing remains." },
    { title: "Not theft prevention", detail: "It detects and reports movement; it does not physically secure an asset." },
  ], 0.9, 2.92, 4.72, { rowH: 0.65, bulletColor: C.red, titleSize: 11.2, detailSize: 8.8 });

  addRect(slide, 6.42, 2.08, 5.9, 4.42, C.panel, C.green, true, { line: { color: C.green, transparency: 45, width: 1.2 } });
  addText(slide, "ROADMAP", 6.76, 2.41, 1.2, 0.25, { fontSize: 9, bold: true, color: C.green, charSpacing: 1.2 });
  const roadmap = [
    ["01", "Auto-discover buffers", "Read /config and map experiments automatically."],
    ["02", "Secure remote access", "Authentication, HTTPS and role-based controls."],
    ["03", "Mobile/PWA notifications", "Background push when the dashboard is not visible."],
    ["04", "Multi-sensor correlation", "Combine simultaneous movement to reduce false alarms."],
    ["05", "Packaged deployment", "Install as a background service with guided setup."],
  ];
  roadmap.forEach((item, index) => {
    const y = 2.94 + index * 0.66;
    addText(slide, item[0], 6.76, y, 0.42, 0.24, { fontSize: 8.5, bold: true, color: C.green });
    addText(slide, item[1], 7.22, y, 2.25, 0.24, { fontSize: 10.8, bold: true });
    addText(slide, item[2], 9.46, y, 2.42, 0.28, { fontSize: 8.7, color: C.muted, valign: "top" });
  });
  addNotes(slide, "Be explicit about scope. This is a trusted-LAN classroom prototype, not a certified security product. The next engineering priorities are automatic Phyphox configuration discovery, authentication and TLS, mobile background notifications, multi-sensor correlation and packaged deployment.");
}

// Slide 12 — Conclusion
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.ellipse, { x: -1.8, y: 3.8, w: 6, h: 6, fill: { color: C.blue, transparency: 90 }, line: { transparency: 100 } });
  slide.addShape(S.ellipse, { x: 9.7, y: -2.5, w: 5.8, h: 5.8, fill: { color: C.green, transparency: 92 }, line: { transparency: 100 } });
  addPill(slide, "CONCLUSION", 5.84, 0.74, 1.62, C.green);
  addText(slide, "A complete IoT loop—built from devices we already own", 1.35, 1.42, 10.63, 0.72, { fontSize: 29, bold: true, align: "center" });
  addText(slide, "FailureAntyTheft proves that a smartphone, a local network and a carefully designed detector can deliver practical real-time monitoring without dedicated hardware or paid cloud services.", 2.02, 2.33, 9.28, 0.82, { fontSize: 14, color: C.muted, align: "center", valign: "top" });
  const summary = [
    ["105", "passing tests", C.green],
    ["REAL-TIME", "WebSocket updates", C.blue],
    ["LOCAL", "privacy by default", C.purple],
    ["AUDIBLE", "actionable alarm", C.red],
  ];
  summary.forEach((item, index) => {
    const x = 1.04 + index * 3.06;
    addRect(slide, x, 3.65, 2.48, 1.28, C.panel, C.line, true, { shadow: shadows.panel });
    addText(slide, item[0], x + 0.15, 3.88, 2.18, 0.42, { fontSize: item[0].length > 5 ? 17 : 24, bold: true, color: item[2], align: "center" });
    addText(slide, item[1], x + 0.15, 4.39, 2.18, 0.22, { fontSize: 9.5, color: C.muted, align: "center" });
  });
  addText(slide, "Questions?", 4.55, 5.55, 4.25, 0.62, { fontSize: 31, bold: true, align: "center" });
  addText(slide, "Thank you", 5.64, 6.25, 2.06, 0.28, { fontSize: 11, color: C.blue2, align: "center", charSpacing: 1 });
  slide.addImage({ path: logoPath, x: 12.03, y: 6.62, w: 0.57, h: 0.57 });
  addNotes(slide, "In conclusion, FailureAntyTheft demonstrates the entire IoT cycle using ordinary devices: sensing, local communication, deterministic processing, persistence, visualization and an audible response. Thank the audience and invite questions.");
}

pptx.writeFile({ fileName: outputPath });
