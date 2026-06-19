import { createRequire } from "node:module";
import fs from "node:fs/promises";
import path from "node:path";

const require = createRequire("C:/Users/Jimmy/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/.pnpm/pptxgenjs@4.0.1/node_modules/pptxgenjs/package.json");
const PptxGenJS = require("pptxgenjs");

const pptx = new PptxGenJS();
pptx.author = "SRTA3353 IoT Group";
pptx.company = "SRTA3353 Machine Learning for IoT";
pptx.subject = "Smart irrigation poster";
pptx.title = "ML-Based Smart Irrigation System Poster";
pptx.lang = "en-US";
pptx.defineLayout({ name: "A3_PORTRAIT", width: 11.69, height: 16.54 });
pptx.layout = "A3_PORTRAIT";
pptx.theme = {
  headFontFace: "Georgia",
  bodyFontFace: "Arial",
  lang: "en-US",
};

const C = {
  paper: "F7F5EE",
  white: "FFFFFF",
  ink: "14211C",
  muted: "5E6B63",
  green: "1F6B4D",
  green2: "9BC8A6",
  teal: "256A7B",
  blue: "2D4F73",
  amber: "E6A33D",
  red: "C75454",
  line: "D8D2C4",
  dark: "10251D",
  softGreen: "F5FBF6",
  softBlue: "F5F8FB",
  softAmber: "FFF8F0",
};

function text(slide, value, x, y, w, h, opts = {}) {
  slide.addText(value, {
    x,
    y,
    w,
    h,
    fontFace: opts.fontFace || "Arial",
    fontSize: opts.fontSize || 10,
    color: opts.color || C.ink,
    bold: opts.bold || false,
    italic: opts.italic || false,
    valign: opts.valign || "top",
    align: opts.align || "left",
    fit: "shrink",
    margin: opts.margin ?? 0.04,
    breakLine: false,
  });
}

function box(slide, x, y, w, h, fill = C.white, line = C.line, radius = true) {
  slide.addShape(radius ? pptx.ShapeType.roundRect : pptx.ShapeType.rect, {
    x,
    y,
    w,
    h,
    rectRadius: radius ? 0.06 : 0,
    fill: { color: fill },
    line: { color: line || fill, width: line ? 0.65 : 0 },
  });
}

function rule(slide, x, y, w, color = C.green, width = 1.2) {
  slide.addShape(pptx.ShapeType.line, { x, y, w, h: 0, line: { color, width } });
}

function arrow(slide, x, y, w, color = C.teal) {
  slide.addShape(pptx.ShapeType.line, {
    x,
    y,
    w,
    h: 0,
    line: { color, width: 1.2, endArrowType: "triangle" },
  });
}

function section(slide, label, title, x, y, w, h, fill = C.white, accent = C.green) {
  box(slide, x, y, w, h, fill, C.line);
  slide.addShape(pptx.ShapeType.rect, {
    x,
    y,
    w: 0.08,
    h,
    fill: { color: accent },
    line: { color: accent, width: 0 },
  });
  text(slide, label.toUpperCase(), x + 0.22, y + 0.18, w - 0.42, 0.17, {
    fontSize: 6.5,
    color: accent,
    bold: true,
  });
  text(slide, title, x + 0.22, y + 0.42, w - 0.42, 0.28, {
    fontSize: 12,
    bold: true,
  });
}

function bulletList(slide, items, x, y, w, lineH = 0.25, color = C.muted) {
  items.forEach((item, i) => {
    slide.addShape(pptx.ShapeType.ellipse, {
      x,
      y: y + i * lineH + 0.06,
      w: 0.06,
      h: 0.06,
      fill: { color: C.green },
      line: { color: C.green, width: 0 },
    });
    text(slide, item, x + 0.14, y + i * lineH, w - 0.14, lineH * 0.9, {
      fontSize: 8.2,
      color,
    });
  });
}

function chip(slide, label, x, y, w, fill = C.softGreen, color = C.green) {
  box(slide, x, y, w, 0.34, fill, fill, true);
  text(slide, label, x + 0.1, y + 0.09, w - 0.2, 0.14, {
    fontSize: 7.3,
    bold: true,
    color,
    align: "center",
  });
}

function miniNode(slide, label, detail, x, y, w, h, fill, accent) {
  box(slide, x, y, w, h, fill, C.line);
  slide.addShape(pptx.ShapeType.rect, {
    x,
    y,
    w: 0.06,
    h,
    fill: { color: accent },
    line: { color: accent, width: 0 },
  });
  text(slide, label, x + 0.15, y + 0.13, w - 0.25, 0.2, {
    fontSize: 8.8,
    bold: true,
  });
  text(slide, detail, x + 0.15, y + 0.4, w - 0.25, h - 0.46, {
    fontSize: 6.8,
    color: C.muted,
  });
}

function thresholdBar(slide, x, y, w) {
  text(slide, "Soil status threshold", x, y - 0.23, w, 0.18, {
    fontSize: 7.8,
    bold: true,
  });
  slide.addShape(pptx.ShapeType.rect, { x, y, w: w * 0.3, h: 0.26, fill: { color: C.red }, line: { color: C.red, width: 0 } });
  slide.addShape(pptx.ShapeType.rect, { x: x + w * 0.3, y, w: w * 0.4, h: 0.26, fill: { color: C.green2 }, line: { color: C.green2, width: 0 } });
  slide.addShape(pptx.ShapeType.rect, { x: x + w * 0.7, y, w: w * 0.3, h: 0.26, fill: { color: C.teal }, line: { color: C.teal, width: 0 } });
  text(slide, "DRY < 30%", x + 0.05, y + 0.07, w * 0.28, 0.1, { fontSize: 5.7, bold: true, color: C.white });
  text(slide, "OPTIMAL", x + w * 0.42, y + 0.07, w * 0.2, 0.1, { fontSize: 5.7, bold: true, color: C.ink, align: "center" });
  text(slide, "WET > 70%", x + w * 0.74, y + 0.07, w * 0.22, 0.1, { fontSize: 5.7, bold: true, color: C.white });
}

function smallTable(slide, x, y, colW, rowH, rows, fontSize = 6.4) {
  rows.forEach((row, r) => {
    let cx = x;
    const head = r === 0;
    row.forEach((cell, c) => {
      box(slide, cx, y + r * rowH, colW[c], rowH, head ? C.dark : r % 2 ? C.white : "FBFAF6", C.line, false);
      text(slide, String(cell), cx + 0.05, y + r * rowH + 0.05, colW[c] - 0.1, rowH - 0.08, {
        fontSize,
        bold: head,
        color: head ? C.white : C.ink,
      });
      cx += colW[c];
    });
  });
}

const slide = pptx.addSlide();
slide.background = { color: C.paper };

// Header
slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 11.69, h: 2.0, fill: { color: C.dark }, line: { color: C.dark, width: 0 } });
slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 0.18, h: 16.54, fill: { color: C.amber }, line: { color: C.amber, width: 0 } });
rule(slide, 0.5, 0.46, 0.36, C.green2, 2);
text(slide, "SRTA3353 MACHINE LEARNING FOR IOT | PROJECT 2", 0.96, 0.35, 4.8, 0.22, {
  fontSize: 7.2,
  color: C.green2,
  bold: true,
});
text(slide, "Machine Learning-Based Smart Irrigation System", 0.5, 0.72, 9.8, 0.52, {
  fontFace: "Georgia",
  fontSize: 24,
  color: C.white,
  bold: true,
});
text(slide, "Predicting soil dryness before plant stress occurs using Raspberry Pi 400, sensors, Streamlit, and notifications", 0.52, 1.28, 8.8, 0.27, {
  fontSize: 10.5,
  color: "DCE9DD",
});
chip(slide, "Raspberry Pi 400", 0.5, 1.62, 1.45, "17372B", C.green2);
chip(slide, "DHT11", 2.08, 1.62, 0.8, "17372B", C.green2);
chip(slide, "Soil + MCP3008", 3.02, 1.62, 1.35, "17372B", C.green2);
chip(slide, "Relay Pump", 4.5, 1.62, 1.05, "17372B", C.green2);
chip(slide, "Streamlit", 5.68, 1.62, 1.0, "17372B", C.green2);
chip(slide, "Telegram/Favoriot", 6.82, 1.62, 1.45, "17372B", C.green2);

// Problem and ML angle
section(slide, "Problem & objective", "From reactive watering to predictive irrigation", 0.45, 2.25, 5.25, 1.9, C.white, C.green);
text(slide, "Traditional automatic watering only reacts when soil is already dry. The proposed system predicts whether soil will become dry soon using current environment and moisture trend.", 0.68, 3.0, 4.78, 0.52, {
  fontSize: 8.4,
  color: C.muted,
});
text(slide, "Main ML output: Dry Soon / Not Dry Soon", 0.68, 3.62, 3.2, 0.2, {
  fontSize: 8.6,
  bold: true,
  color: C.green,
});
thresholdBar(slide, 3.55, 3.62, 1.85);

section(slide, "Decision logic", "Safe hybrid control keeps the demo reliable", 5.95, 2.25, 5.25, 1.9, C.softGreen, C.teal);
smallTable(slide, 6.2, 2.95, [1.5, 1.65, 1.55], 0.26, [
  ["Condition", "Recommend", "Control"],
  ["DRY", "Pump ON", "Pump ON"],
  ["WET", "Pump OFF", "Pump OFF"],
  ["OPTIMAL + Dry Soon", "Alert only", "Pump ON early"],
], 5.9);
text(slide, "Demo setting: ML_CONTROL_MODE=recommend", 6.2, 4.02, 4.35, 0.12, {
  fontSize: 5.6,
  bold: true,
  color: C.teal,
});

// Architecture
section(slide, "System architecture", "Sensing, processing, action, and visualization are integrated in one loop", 0.45, 4.45, 10.75, 2.35, C.white, C.blue);
miniNode(slide, "Sensors", "DHT11 temp/humidity\nsoil sensor AO", 0.75, 5.28, 1.55, 0.88, C.softGreen, C.green);
arrow(slide, 2.38, 5.72, 0.55, C.teal);
miniNode(slide, "ADC", "MCP3008 converts analog soil signal to digital", 3.0, 5.28, 1.55, 0.88, C.softBlue, C.teal);
arrow(slide, 4.62, 5.72, 0.55, C.teal);
miniNode(slide, "Raspberry Pi", "full_monitor.py\npreprocess + predict", 5.25, 5.22, 1.75, 1.02, C.softGreen, C.green);
arrow(slide, 7.08, 5.72, 0.55, C.teal);
miniNode(slide, "Outputs", "relay pump, OLED,\nTelegram alerts", 7.7, 5.28, 1.55, 0.88, C.softAmber, C.amber);
arrow(slide, 9.32, 5.72, 0.55, C.teal);
miniNode(slide, "Dashboard", "plant_data.csv\nStreamlit + Favoriot", 9.95, 5.28, 1.0, 0.88, C.softBlue, C.blue);
text(slide, "Streamlit reads plant_data.csv while full_monitor.py writes new readings. Auto-refresh updates the dashboard display only.", 0.75, 6.38, 9.65, 0.18, {
  fontSize: 7.2,
  bold: true,
  color: C.green,
});

// Hardware
section(slide, "Hardware implementation", "Required sensors and actuator are covered", 0.45, 7.08, 5.25, 2.4, C.white, C.green);
bulletList(slide, [
  "Raspberry Pi 400 runs the monitoring script.",
  "DHT11 provides temperature and humidity.",
  "Soil moisture AO is read through MCP3008 channel 0.",
  "Relay on GPIO18 controls the DC water pump.",
  "OLED SSD1306 shows live local status.",
], 0.72, 7.9, 4.65, 0.24);
text(slide, "Wiring hints: enable SPI for MCP3008, I2C for OLED, verify DHT pin D4/D17.", 0.72, 9.1, 4.5, 0.18, {
  fontSize: 6.5,
  color: C.green,
  bold: true,
});

// Data / ML
section(slide, "Data processing & ML", "The model predicts dryness in the next 10 minutes", 5.95, 7.08, 5.25, 2.4, C.softBlue, C.teal);
smallTable(slide, 6.18, 7.86, [1.35, 1.65, 1.55], 0.25, [
  ["Input", "Processing", "Output"],
  ["Soil raw", "calibrate", "soil_value"],
  ["Soil %", "threshold", "soil_status"],
  ["Current/previous", "subtract", "change_rate"],
  ["DHT missing", "no average", "Unknown"],
], 5.8);
text(slide, "ML features: soil_value, temperature, humidity, previous_soil_value, moisture_change_rate, pump_status.", 6.18, 9.15, 4.55, 0.18, {
  fontSize: 6.9,
  color: C.teal,
  bold: true,
});

// Dashboard and notifications
section(slide, "Dashboard & notifications", "Student 5 work: monitoring, alerts, and cloud path", 0.45, 9.78, 5.25, 2.28, C.softGreen, C.green);
bulletList(slide, [
  "Streamlit dashboard is the main monitoring interface.",
  "Separate charts: soil moisture, temperature, humidity, moisture trend.",
  "Alert banners for DRY, WET, Dry Soon, DHT Missing, and stale data.",
  "Telegram sends alerts once per warning type per cooldown period.",
  "Favoriot REST payload remains optional cloud visualization.",
], 0.72, 10.55, 4.55, 0.3);

// Demo
section(slide, "Demo scenarios", "Show normal, abnormal, and ML-predicted states", 5.95, 9.78, 5.25, 2.28, C.white, C.amber);
smallTable(slide, 6.18, 10.55, [1.45, 1.95, 1.2], 0.24, [
  ["Scenario", "Action", "Expected result"],
  ["Optimal", "medium-moist soil", "Pump OFF"],
  ["Dry", "dry condition", "Pump ON"],
  ["Dry Soon", "warm/drying trend", "Alert"],
  ["Wet", "very wet soil", "Pump OFF"],
  ["DHT fault", "missing DHT data", "Unknown"],
], 5.2);

// Criteria / contribution bottom
section(slide, "Assessment evidence", "The poster, demo, and report can point to each scoring area", 0.45, 12.36, 10.75, 2.85, C.white, C.blue);
smallTable(slide, 0.72, 13.08, [2.2, 3.35, 3.95], 0.31, [
  ["Criteria", "Evidence", "Marks focus"],
  ["Problem relevance", "Predictive smart agriculture watering", "5"],
  ["Hardware integration", "Pi 400, DHT11, soil, MCP3008, OLED, relay, pump", "10"],
  ["Data communication", "Streamlit, CSV, Telegram, Favoriot REST payload", "5"],
  ["Decision logic", "Threshold baseline + Decision Tree ML", "5"],
  ["Demo/documentation", "README, Student Guide, tests, demo scenarios", "10"],
], 5.9);
miniNode(slide, "Student 4", "Data processing, missing-data handling, feature extraction, baseline vs ML comparison.", 0.72, 14.98, 4.8, 0.58, C.softGreen, C.green);
miniNode(slide, "Student 5", "Streamlit dashboard, charts, Telegram alerts, monitoring/debug, Favoriot connectivity.", 5.85, 14.98, 4.75, 0.58, C.softBlue, C.teal);

// Footer
rule(slide, 0.45, 15.82, 10.75, C.line, 0.5);
text(slide, "Project files: full_monitor.py, streamlit_app.py, plant_monitor/, plant_data.csv, models/dryness_model.joblib", 0.45, 15.95, 7.4, 0.16, {
  fontSize: 6.2,
  color: C.muted,
});
text(slide, "ML-Based Smart Irrigation System", 8.25, 15.95, 2.95, 0.16, {
  fontSize: 6.2,
  color: C.muted,
  bold: true,
  align: "right",
});

const out = "\\\\wsl.localhost\\Ubuntu\\home\\jimmy_linux\\anaconda_projects\\iot\\project\\soil-moisture-iot\\outputs\\manual-20260615-smart-irrigation\\poster\\ML-Based_Smart_Irrigation_System_Poster.pptx";
await fs.mkdir(path.dirname(out), { recursive: true });
await pptx.writeFile({ fileName: out });
console.log(out);
