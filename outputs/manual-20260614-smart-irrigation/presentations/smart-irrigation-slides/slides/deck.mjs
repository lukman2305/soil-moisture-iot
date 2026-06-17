import { layers, shape, text } from "@oai/artifact-tool";

const W = 1280;
const H = 720;

const C = {
  paper: "#F7F5EE",
  paper2: "#EFEAE0",
  ink: "#14211C",
  muted: "#5E6B63",
  green: "#1F6B4D",
  green2: "#9BC8A6",
  teal: "#256A7B",
  blue: "#2D4F73",
  amber: "#E6A33D",
  red: "#C75454",
  line: "#D8D2C4",
  white: "#FFFFFF",
  dark: "#10251D",
};

const titleFont = "Georgia";
const bodyFont = "Arial";

function bg(fill = C.paper) {
  return shape({
    geometry: "rect",
    position: { left: 0, top: 0 },
    width: W,
    height: H,
    fill,
    line: { color: fill, width: 0 },
  });
}

function box(x, y, width, height, fill = C.white, line = C.line, radius = 10) {
  return shape({
    geometry: "rect",
    position: { left: x, y },
    width,
    height,
    fill,
    line: line ? { color: line, width: 1 } : { color: fill, width: 0 },
    borderRadius: radius,
  });
}

function txt(value, x, y, width, height, style = {}) {
  return text(value, {
    position: { left: x, y },
    width,
    height,
    style: {
      fontFamily: bodyFont,
      fontSize: 18,
      color: C.ink,
      ...style,
    },
  });
}

function kicker(label, x = 70, y = 42, color = C.green) {
  return [
    shape({
      name: "kicker-marker",
      geometry: "rect",
      position: { left: x, top: y + 9 },
      width: 34,
      height: 3,
      fill: color,
      line: { color, width: 0 },
    }),
    txt(label.toUpperCase(), x + 46, y, 500, 28, {
      fontSize: 12,
      bold: true,
      color,
    }),
  ];
}

function title(claim) {
  return txt(claim, 70, 78, 980, 82, {
    fontFamily: titleFont,
    fontSize: 36,
    bold: true,
    color: C.ink,
  });
}

function footer(slideNo, source = "Source: project README, Student Guide, and SRTA3353 Project 2 criteria") {
  return [
    shape({
      geometry: "rect",
      position: { left: 70, top: 675 },
      width: 1140,
      height: 1,
      fill: C.line,
      line: { color: C.line, width: 0 },
    }),
    txt(source, 70, 684, 780, 20, { fontSize: 10, color: C.muted }),
    txt(String(slideNo).padStart(2, "0"), 1168, 684, 42, 20, {
      fontSize: 10,
      color: C.muted,
      bold: true,
    }),
  ];
}

function header(slideNo, kickerLabel, claim, source) {
  return [bg(), ...kicker(kickerLabel), title(claim), ...footer(slideNo, source)];
}

function pill(label, x, y, width, fill, color = C.ink) {
  return [
    box(x, y, width, 34, fill, null, 17),
    txt(label, x + 14, y + 8, width - 28, 18, {
      fontSize: 12,
      bold: true,
      color,
    }),
  ];
}

function metric(value, label, context, x, y, width, fill = C.white) {
  return [
    box(x, y, width, 116, fill, C.line, 12),
    txt(value, x + 20, y + 18, width - 40, 34, {
      fontSize: 30,
      bold: true,
      color: C.green,
    }),
    txt(label, x + 20, y + 58, width - 40, 24, {
      fontSize: 15,
      bold: true,
      color: C.ink,
    }),
    txt(context, x + 20, y + 84, width - 40, 22, {
      fontSize: 12,
      color: C.muted,
    }),
  ];
}

function node(label, detail, x, y, width, height, fill = C.white, accent = C.green) {
  return [
    box(x, y, width, height, fill, C.line, 10),
    shape({
      geometry: "rect",
      position: { left: x, y },
      width: 7,
      height,
      fill: accent,
      line: { color: accent, width: 0 },
      borderRadius: 4,
    }),
    txt(label, x + 18, y + 14, width - 28, 24, {
      fontSize: 16,
      bold: true,
      color: C.ink,
    }),
    txt(detail, x + 18, y + 42, width - 28, height - 52, {
      fontSize: 12.5,
      color: C.muted,
    }),
  ];
}

function arrow(x, y, width, color = C.teal) {
  return [
    shape({
      geometry: "rect",
      position: { left: x, y },
      width,
      height: 2,
      fill: color,
      line: { color, width: 0 },
    }),
    txt(">", x + width - 6, y - 11, 18, 24, {
      fontSize: 20,
      bold: true,
      color,
    }),
  ];
}

function smallTable(x, y, colWidths, rowHeight, rows, opts = {}) {
  const els = [];
  let cy = y;
  for (let r = 0; r < rows.length; r += 1) {
    let cx = x;
    const isHeader = r === 0 && opts.header !== false;
    for (let c = 0; c < colWidths.length; c += 1) {
      const fill = isHeader ? C.dark : r % 2 === 0 ? C.white : "#FBFAF6";
      const color = isHeader ? C.white : C.ink;
      els.push(box(cx, cy, colWidths[c], rowHeight, fill, C.line, 0));
      els.push(
        txt(String(rows[r][c] ?? ""), cx + 10, cy + 9, colWidths[c] - 20, rowHeight - 14, {
          fontSize: opts.fontSize ?? 12.5,
          bold: isHeader,
          color,
        }),
      );
      cx += colWidths[c];
    }
    cy += rowHeight;
  }
  return els;
}

function thresholdBar(x, y, width) {
  return [
    txt("Soil moisture status thresholds", x, y - 36, width, 24, {
      fontSize: 16,
      bold: true,
    }),
    box(x, y, width * 0.3, 40, C.red, null, 6),
    box(x + width * 0.3, y, width * 0.4, 40, C.green2, null, 0),
    box(x + width * 0.7, y, width * 0.3, 40, C.teal, null, 6),
    txt("DRY < 30%", x + 12, y + 11, width * 0.3 - 24, 18, {
      fontSize: 12,
      bold: true,
      color: C.white,
    }),
    txt("OPTIMAL 30-70%", x + width * 0.3 + 18, y + 11, width * 0.4 - 36, 18, {
      fontSize: 12,
      bold: true,
      color: C.ink,
    }),
    txt("WET > 70%", x + width * 0.7 + 16, y + 11, width * 0.3 - 32, 18, {
      fontSize: 12,
      bold: true,
      color: C.white,
    }),
    txt("0%", x, y + 50, 50, 18, { fontSize: 11, color: C.muted }),
    txt("30%", x + width * 0.3 - 16, y + 50, 50, 18, { fontSize: 11, color: C.muted }),
    txt("70%", x + width * 0.7 - 16, y + 50, 50, 18, { fontSize: 11, color: C.muted }),
    txt("100%", x + width - 34, y + 50, 50, 18, { fontSize: 11, color: C.muted }),
  ];
}

function chartBars(x, y, width, height, items) {
  const max = Math.max(...items.map((d) => d.value));
  const gap = 18;
  const barW = (width - gap * (items.length - 1)) / items.length;
  const els = [
    shape({
      geometry: "rect",
      position: { left: x, top: y + height },
      width,
      height: 1,
      fill: C.line,
      line: { color: C.line, width: 0 },
    }),
  ];
  items.forEach((d, i) => {
    const h = (d.value / max) * (height - 26);
    const bx = x + i * (barW + gap);
    const by = y + height - h;
    els.push(box(bx, by, barW, h, d.color, null, 7));
    els.push(txt(d.label, bx - 4, y + height + 12, barW + 8, 34, { fontSize: 10.5, color: C.muted }));
    els.push(txt(d.valueLabel, bx, by - 26, barW, 20, { fontSize: 12, bold: true, color: C.ink }));
  });
  return els;
}

const slides = {
  1() {
    return [
      bg(C.dark),
      shape({
        geometry: "rect",
        position: { left: 0, top: 0 },
        width: 1280,
        height: 720,
        fill: C.dark,
        line: { color: C.dark, width: 0 },
      }),
      shape({
        geometry: "rect",
        position: { left: 0, top: 0 },
        width: 24,
        height: 720,
        fill: C.amber,
        line: { color: C.amber, width: 0 },
      }),
      ...kicker("SRTA3353 Machine Learning for IoT", 72, 54, C.green2),
      txt("Machine Learning-Based Smart Irrigation System", 72, 128, 900, 74, {
        fontFamily: titleFont,
        fontSize: 44,
        bold: true,
        color: C.white,
      }),
      txt("Predicting soil dryness before plant stress occurs", 72, 220, 820, 34, {
        fontSize: 22,
        color: "#DCE9DD",
      }),
      txt("Raspberry Pi 400 + DHT11 + soil sensor/MCP3008 + relay pump + OLED + Streamlit + Telegram/Favoriot", 72, 278, 970, 32, {
        fontSize: 16,
        color: "#BCD3C4",
      }),
      ...metric("3", "input sensor values", "soil moisture, temperature, humidity", 72, 402, 246, "#17372B"),
      ...metric("10 min", "prediction target", "demo interval can be reduced to 10 seconds", 346, 402, 246, "#17372B"),
      ...metric("Hybrid", "decision logic", "threshold baseline plus Decision Tree ML", 620, 402, 246, "#17372B"),
      ...metric("Live", "monitoring layer", "OLED, Streamlit, Telegram, optional Favoriot", 894, 402, 246, "#17372B"),
      txt("Prepared for Project 2: Hardware-Based IoT System Implementation", 72, 648, 700, 20, {
        fontSize: 12,
        color: "#A7C7B3",
      }),
      txt("01", 1168, 648, 42, 20, { fontSize: 10, color: "#A7C7B3", bold: true }),
    ];
  },

  2() {
    return [
      ...header(2, "problem fit", "The system shifts irrigation from reactive watering to predictive warning."),
      txt("Traditional small-plant watering reacts only after soil is already dry. In hot or low-humidity conditions, that delay can stress the plant before the pump starts.", 70, 178, 510, 84, {
        fontSize: 19,
        color: C.muted,
      }),
      ...node("Baseline system", "Soil is dry now -> pump ON. Simple and reliable, but late.", 92, 318, 290, 122, "#FFF8F0", C.amber),
      ...arrow(393, 378, 104, C.amber),
      ...node("Project system", "Soil is still optimal, but trend and environment show Dry Soon.", 508, 318, 340, 122, "#F5FBF6", C.green),
      ...arrow(860, 378, 104, C.green),
      ...node("Outcome", "Warn early, log evidence, and optionally control pump before stress.", 976, 318, 210, 122, "#F4F7FB", C.teal),
      box(70, 508, 526, 84, C.white, C.line, 12),
      txt("Target users", 92, 528, 170, 22, { fontSize: 14, bold: true, color: C.green }),
      txt("Small plant owners, student labs, and greenhouse-style demos that need low-cost monitoring.", 92, 554, 450, 26, { fontSize: 13, color: C.muted }),
      box(650, 508, 526, 84, C.white, C.line, 12),
      txt("Application domain", 672, 528, 190, 22, { fontSize: 14, bold: true, color: C.teal }),
      txt("Smart agriculture: soil moisture, temperature, humidity, irrigation automation, crop monitoring.", 672, 554, 458, 26, { fontSize: 13, color: C.muted }),
    ];
  },

  3() {
    const rows = [
      ["Assignment requirement", "Implementation evidence"],
      ["Raspberry Pi / hardware platform", "Raspberry Pi 400 runs full_monitor.py"],
      ["At least three input sensors/values", "DHT11 temperature, DHT11 humidity, soil moisture via MCP3008"],
      ["Output / actuator", "Relay controls DC water pump; OLED shows local status"],
      ["Real-time / near real-time processing", "READ_INTERVAL_SECONDS=600 normally; 10 seconds for demo"],
      ["Two data handling steps", "Calibration to percent, thresholding, feature extraction, missing-data handling"],
      ["Decision mechanism", "Hybrid: baseline threshold plus DecisionTreeClassifier prediction"],
      ["Monitoring layer", "Streamlit dashboard plus OLED display"],
      ["Automatic alert/control", "Pump control, Streamlit alert banners, Telegram notifications"],
      ["IoT visualization", "Streamlit as main dashboard; Favoriot REST payload kept for cloud visualization"],
    ];
    return [
      ...header(3, "criteria coverage", "The prototype maps directly to the technical requirements."),
      ...smallTable(70, 174, [350, 760], 42, rows, { fontSize: 12 }),
      txt("For the final submission, include screenshots of Streamlit and Favoriot if the Favoriot device is configured.", 80, 608, 990, 24, {
        fontSize: 13,
        bold: true,
        color: C.green,
      }),
    ];
  },

  4() {
    return [
      ...header(4, "hardware proof", "The hardware path covers sensing, conversion, display, and actuation."),
      ...node("DHT11", "Temperature and humidity\nDefault pin: board.D4", 72, 202, 200, 118, "#F9FBF5", C.green),
      ...node("Soil sensor AO", "Analog moisture signal", 72, 386, 200, 98, "#FFF8F0", C.amber),
      ...node("MCP3008 ADC", "SPI analog-to-digital\nSoil channel: CH0", 340, 354, 220, 130, "#F5F8FB", C.teal),
      ...node("Raspberry Pi 400", "Reads sensors, preprocesses, predicts, logs CSV, controls relay", 650, 286, 260, 168, "#F5FBF6", C.green),
      ...node("OLED SSD1306", "I2C display shows temp, humidity, soil, ML, pump", 986, 202, 220, 118, C.white, C.blue),
      ...node("Relay + pump", "GPIO18 active LOW\nLOW = pump ON", 986, 386, 220, 118, "#FFF8F0", C.red),
      ...arrow(282, 260, 48, C.green),
      ...arrow(282, 435, 48, C.amber),
      ...arrow(570, 418, 68, C.teal),
      ...arrow(920, 260, 56, C.blue),
      ...arrow(920, 435, 56, C.red),
      txt("Important wiring checks: enable I2C for OLED, enable SPI for MCP3008, verify DHT pin, verify relay active-LOW behavior.", 96, 560, 1060, 36, {
        fontSize: 15,
        bold: true,
        color: C.muted,
      }),
    ];
  },

  5() {
    const steps = [
      ["Sensors", "DHT11 + soil AO"],
      ["full_monitor.py", "read, preprocess, predict"],
      ["Decision", "threshold + ML"],
      ["Outputs", "pump, OLED, alerts"],
      ["Data layer", "CSV + dashboard + cloud"],
    ];
    const els = [...header(5, "software flow", "One Python loop connects hardware, ML, logging, and dashboards.")];
    steps.forEach((s, i) => {
      const x = 72 + i * 230;
      els.push(...node(s[0], s[1], x, 242, 180, 110, i === 1 ? "#F5FBF6" : C.white, i === 2 ? C.amber : C.green));
      if (i < steps.length - 1) els.push(...arrow(x + 188, 296, 38, C.teal));
    });
    els.push(...node("Telegram", "risk alerts with cooldown", 216, 444, 220, 96, "#FFF8F0", C.amber));
    els.push(...node("Streamlit", "latest metrics, charts, debug status", 530, 444, 260, 96, "#F5F8FB", C.teal));
    els.push(...node("Favoriot", "optional REST cloud payload", 890, 444, 220, 96, C.white, C.blue));
    els.push(txt("Streamlit reads plant_data.csv. It does not directly read sensors or control the pump.", 286, 586, 710, 24, {
      fontSize: 15,
      bold: true,
      color: C.green,
    }));
    return els;
  },

  6() {
    const rows = [
      ["Raw / issue", "Processing method", "Output used by system"],
      ["Soil analog reading", "Calibrate and convert to 0-100 percent", "soil_value"],
      ["Soil percentage", "Threshold classification", "DRY / OPTIMAL / WET"],
      ["Current + previous soil", "Feature extraction", "moisture_change_rate"],
      ["ON/OFF pump text", "Encode for model feature", "pump_status_code"],
      ["Incomplete training row", "Drop before training", "clean training dataset"],
      ["Missing DHT11 data", "Do not average; return Unknown", "DHT Missing alert"],
    ];
    return [
      ...header(6, "data processing", "Preprocessing turns raw sensor values into reliable ML features."),
      ...thresholdBar(70, 206, 520),
      ...smallTable(650, 178, [190, 270, 230], 48, rows, { fontSize: 11.5 }),
      box(70, 344, 520, 186, C.white, C.line, 12),
      txt("Why missing DHT11 is not filled with an average", 96, 366, 462, 24, {
        fontSize: 16,
        bold: true,
        color: C.green,
      }),
      txt("In real hardware, missing temperature or humidity may indicate wiring or sensor failure. Filling with an average can hide the fault and create fake weather conditions, so the safer output is ml_prediction = Unknown.", 96, 402, 450, 72, {
        fontSize: 14,
        color: C.muted,
      }),
      txt("This covers the assignment requirement for at least two data handling or preprocessing steps.", 96, 490, 452, 24, {
        fontSize: 13,
        bold: true,
        color: C.amber,
      }),
    ];
  },

  7() {
    const rows = [
      ["Item", "Baseline logic", "ML intelligent logic"],
      ["Main input", "Current soil only", "Soil, temp, humidity, previous soil, trend, pump"],
      ["Decision", "soil < 30% -> pump ON", "Predict Dry Soon / Not Dry Soon"],
      ["Behavior", "Reactive", "Predictive"],
      ["Example", "45% soil means pump OFF", "45% + hot/dry/falling trend can mean Dry Soon"],
    ];
    return [
      ...header(7, "intelligence", "The ML layer predicts future dryness instead of replacing the safe baseline."),
      ...smallTable(70, 178, [190, 330, 510], 58, rows, { fontSize: 12 }),
      box(70, 540, 330, 74, "#F5FBF6", C.line, 12),
      txt("Default: recommend mode", 94, 560, 260, 22, { fontSize: 15, bold: true, color: C.green }),
      txt("ML warns early, but threshold keeps direct pump control safer for demos.", 94, 586, 270, 20, { fontSize: 12.5, color: C.muted }),
      box(448, 540, 330, 74, "#FFF8F0", C.line, 12),
      txt("Optional: control mode", 472, 560, 260, 22, { fontSize: 15, bold: true, color: C.amber }),
      txt("If soil is OPTIMAL and ML predicts Dry Soon, pump can turn ON early.", 472, 586, 270, 20, { fontSize: 12.5, color: C.muted }),
      box(826, 540, 330, 74, "#F5F8FB", C.line, 12),
      txt("Model", 850, 560, 260, 22, { fontSize: 15, bold: true, color: C.teal }),
      txt("DecisionTreeClassifier saved as models/dryness_model.joblib.", 850, 586, 270, 20, { fontSize: 12.5, color: C.muted }),
    ];
  },

  8() {
    return [
      ...header(8, "model data", "Kaggle starts the model; real Raspberry Pi data improves it later."),
      ...node("1. Starter training", "Use data/training_smart_agriculture.csv from Kaggle.\nMOI -> soil_value; temp/humidity retained.", 88, 214, 250, 140, "#F5F8FB", C.blue),
      ...arrow(348, 282, 74, C.blue),
      ...node("2. Saved model", "Train Decision Tree and save models/dryness_model.joblib.", 436, 214, 240, 140, "#F5FBF6", C.green),
      ...arrow(688, 282, 74, C.green),
      ...node("3. Real-time prediction", "full_monitor.py loads model and predicts every sensor cycle.", 774, 214, 240, 140, C.white, C.teal),
      ...arrow(1028, 282, 60, C.teal),
      ...node("4. Later retraining", "Collect more plant_data.csv rows; retrain using the full real CSV.", 1096, 214, 110, 140, "#FFF8F0", C.amber),
      box(94, 430, 498, 108, C.white, C.line, 12),
      txt("Current behavior", 118, 452, 210, 22, { fontSize: 16, bold: true, color: C.green }),
      txt("The model loads or trains at startup. It does not automatically retrain every 10 minutes.", 118, 482, 420, 34, { fontSize: 13.5, color: C.muted }),
      box(688, 430, 498, 108, C.white, C.line, 12),
      txt("Retraining explanation for lecturer", 712, 452, 310, 22, { fontSize: 16, bold: true, color: C.teal }),
      txt("If 20 days of real data exists in plant_data.csv, retraining uses the whole 20-day file unless we manually filter it.", 712, 482, 414, 34, { fontSize: 13.5, color: C.muted }),
    ];
  },

  9() {
    const chartItems = [
      { label: "soil", value: 45, valueLabel: "45%", color: C.green },
      { label: "temp", value: 32, valueLabel: "32 C", color: C.amber },
      { label: "humidity", value: 55, valueLabel: "55%", color: C.teal },
      { label: "trend", value: 8, valueLabel: "rate", color: C.blue },
    ];
    return [
      ...header(9, "dashboard", "Streamlit is the main live dashboard; Favoriot remains the IoT cloud path."),
      box(72, 178, 698, 420, C.white, C.line, 12),
      txt("Streamlit dashboard mock", 98, 204, 300, 24, { fontSize: 16, bold: true, color: C.green }),
      ...metric("45%", "soil moisture", "latest CSV reading", 98, 246, 150, "#F5FBF6"),
      ...metric("32 C", "temperature", "DHT11", 270, 246, 150, "#FFF8F0"),
      ...metric("55%", "humidity", "DHT11", 442, 246, 150, "#F5F8FB"),
      ...metric("OFF", "pump", "safe state", 614, 246, 130, "#FBFAF6"),
      ...chartBars(118, 436, 586, 96, chartItems),
      txt("Charts are separated by unit: soil %, temperature C, humidity %, and moisture change rate.", 98, 554, 586, 24, {
        fontSize: 12.5,
        color: C.muted,
      }),
      ...node("Telegram", "Sends risk alerts to personal or group chat with cooldown.", 826, 204, 300, 96, "#FFF8F0", C.amber),
      ...node("Favoriot", "REST API payload includes temp, humidity, soil, pump, ML, notification status.", 826, 326, 300, 116, "#F5F8FB", C.blue),
      ...node("OLED", "Shows SMART PLANT, DHT status, soil value, ML prediction, and pump status.", 826, 470, 300, 96, "#F5FBF6", C.green),
    ];
  },

  10() {
    const rows = [
      ["Condition", "Recommend mode output", "Control mode output"],
      ["DRY soil", "Pump ON", "Pump ON"],
      ["WET soil", "Pump OFF + wet alert", "Pump OFF + wet alert"],
      ["OPTIMAL + Dry Soon", "Pump OFF + early warning", "Pump ON early"],
      ["DHT missing", "ML Unknown + DHT alert", "ML Unknown + DHT alert"],
    ];
    return [
      ...header(10, "automation", "Pump control stays safe while alerts explain every risk state."),
      ...smallTable(70, 190, [260, 390, 390], 64, rows, { fontSize: 13 }),
      box(100, 520, 480, 86, "#FFF8F0", C.line, 12),
      txt("Telegram cooldown", 126, 542, 240, 22, { fontSize: 16, bold: true, color: C.amber }),
      txt("Same warning type sends once every 30 minutes normally, or every 60 seconds in demo mode.", 126, 570, 390, 22, { fontSize: 13, color: C.muted }),
      box(700, 520, 380, 86, "#F5FBF6", C.line, 12),
      txt("Reason codes", 726, 542, 240, 22, { fontSize: 16, bold: true, color: C.green }),
      txt("PUMP_ON_DRY, PUMP_ON_ML_DRY_SOON, TELEGRAM_SENT, CSV_WRITE_OK, MODEL_LOADED.", 726, 570, 300, 22, { fontSize: 12.5, color: C.muted }),
    ];
  },

  11() {
    const rows = [
      ["Demo scenario", "Action to show", "Expected evidence"],
      ["Normal / optimal soil", "Sensor in medium-moist soil", "Pump OFF, dashboard updates"],
      ["Dry soil", "Expose sensor to dry condition", "Pump ON, DRY alert"],
      ["Dry Soon", "Use warm/low humidity sample or model output", "Early warning, pump OFF in recommend mode"],
      ["Wet / overwatering", "Place sensor in very wet soil", "Pump OFF, WET alert"],
      ["Hardware fault", "Disconnect DHT11 briefly", "ML Unknown + DHT Missing alert"],
    ];
    return [
      ...header(11, "demo plan", "A strong demo proves normal operation, abnormal states, and recovery."),
      ...smallTable(70, 174, [220, 390, 430], 56, rows, { fontSize: 12.5 }),
      box(96, 540, 480, 72, C.white, C.line, 12),
      txt("Lecturer demo interval", 122, 560, 190, 22, { fontSize: 15, bold: true, color: C.green }),
      txt("READ_INTERVAL_SECONDS=10, NOTIFICATION_COOLDOWN_SECONDS=60, STREAMLIT_REFRESH_SECONDS=10.", 122, 586, 390, 18, { fontSize: 11.5, color: C.muted }),
      box(704, 540, 380, 72, C.white, C.line, 12),
      txt("Normal collection", 730, 560, 190, 22, { fontSize: 15, bold: true, color: C.teal }),
      txt("READ_INTERVAL_SECONDS=600, NOTIFICATION_COOLDOWN_SECONDS=1800.", 730, 586, 300, 18, { fontSize: 11.5, color: C.muted }),
    ];
  },

  12() {
    const rows = [
      ["Marking area", "Evidence in project"],
      ["Problem relevance (5)", "Predictive smart agriculture watering before plant stress"],
      ["Hardware integration (10)", "Pi 400, DHT11, soil sensor, MCP3008, OLED, relay, pump"],
      ["Data communication (5)", "Streamlit, CSV logging, Telegram, Favoriot REST support"],
      ["Decision logic (5)", "Threshold baseline plus Decision Tree ML prediction"],
      ["Presentation/documentation (10)", "README, Student Guide, tests, demo scenarios, contribution evidence"],
    ];
    return [
      ...header(12, "submission evidence", "The final story should show working hardware plus clear individual contribution."),
      ...smallTable(70, 176, [260, 760], 58, rows, { fontSize: 12.5 }),
      box(86, 548, 474, 76, "#F5FBF6", C.line, 12),
      txt("Student 4 evidence", 110, 568, 240, 22, { fontSize: 15, bold: true, color: C.green }),
      txt("Preprocessing, missing data handling, feature extraction, ML decision, baseline comparison.", 110, 594, 390, 18, { fontSize: 12.5, color: C.muted }),
      box(680, 548, 474, 76, "#F5F8FB", C.line, 12),
      txt("Student 5 evidence", 704, 568, 240, 22, { fontSize: 15, bold: true, color: C.teal }),
      txt("Streamlit dashboard, charts, Telegram alerts, cloud/Favoriot payload, monitoring/debug tab.", 704, 594, 390, 18, { fontSize: 12.5, color: C.muted }),
    ];
  },
};

export async function buildSlide(presentation, slideNo) {
  const slide = presentation.slides.add();
  slide.compose(layers({ width: W, height: H }, slides[slideNo]()));
  return slide;
}
