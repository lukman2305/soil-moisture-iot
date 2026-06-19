import { createRequire } from "node:module";
import fs from "node:fs/promises";
import path from "node:path";

const require = createRequire("C:/Users/Jimmy/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/.pnpm/pptxgenjs@4.0.1/node_modules/pptxgenjs/package.json");
const PptxGenJS = require("pptxgenjs");

const pptx = new PptxGenJS();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "SRTA3353 IoT Group";
pptx.subject = "Machine Learning-Based Smart Irrigation System";
pptx.title = "ML-Based Smart Irrigation System";
pptx.company = "SRTA3353 Machine Learning for IoT";
pptx.lang = "en-US";
pptx.theme = {
  headFontFace: "Georgia",
  bodyFontFace: "Arial",
  lang: "en-US",
};

const C = {
  paper: "F7F5EE",
  paper2: "EFEAE0",
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
};

const W = 13.333;
const H = 7.5;

function addBg(slide, color = C.paper) {
  slide.background = { color };
}

function addText(slide, value, x, y, w, h, opts = {}) {
  slide.addText(value, {
    x, y, w, h,
    fontFace: opts.fontFace || "Arial",
    fontSize: opts.fontSize || 12,
    color: opts.color || C.ink,
    bold: opts.bold || false,
    italic: opts.italic || false,
    valign: opts.valign || "top",
    fit: "shrink",
    margin: opts.margin ?? 0.04,
    breakLine: false,
  });
}

function addBox(slide, x, y, w, h, fill = C.white, line = C.line, radius = true) {
  slide.addShape(radius ? pptx.ShapeType.roundRect : pptx.ShapeType.rect, {
    x, y, w, h,
    rectRadius: radius ? 0.08 : 0,
    fill: { color: fill },
    line: { color: line || fill, width: line ? 0.7 : 0 },
  });
}

function addRule(slide, x, y, w, color = C.green, width = 1.2) {
  slide.addShape(pptx.ShapeType.line, {
    x, y, w, h: 0,
    line: { color, width },
  });
}

function addArrow(slide, x, y, w, color = C.teal) {
  slide.addShape(pptx.ShapeType.line, {
    x, y, w, h: 0,
    line: { color, width: 1.2, endArrowType: "triangle" },
  });
}

function addFooter(slide, n, source = "Source: project README, Student Guide, and SRTA3353 Project 2 criteria") {
  addRule(slide, 0.55, 7.03, 11.85, C.line, 0.5);
  addText(slide, source, 0.55, 7.12, 8.4, 0.18, { fontSize: 6.8, color: C.muted });
  addText(slide, String(n).padStart(2, "0"), 12.1, 7.12, 0.5, 0.18, { fontSize: 6.8, color: C.muted, bold: true });
}

function addHeader(slide, n, kicker, title, source) {
  addBg(slide);
  addRule(slide, 0.55, 0.58, 0.35, C.green, 2);
  addText(slide, kicker.toUpperCase(), 1.02, 0.46, 4.2, 0.25, { fontSize: 7.6, color: C.green, bold: true });
  addText(slide, title, 0.55, 0.83, 10.6, 0.72, { fontFace: "Georgia", fontSize: 22, bold: true, color: C.ink });
  addFooter(slide, n, source);
}

function addMetric(slide, value, label, context, x, y, w, fill = C.white) {
  const darkMetric = fill === "17372B";
  addBox(slide, x, y, w, 1.05, fill, C.line);
  addText(slide, value, x + 0.16, y + 0.15, w - 0.32, 0.28, { fontSize: 18, bold: true, color: darkMetric ? C.green2 : C.green });
  addText(slide, label, x + 0.16, y + 0.5, w - 0.32, 0.2, { fontSize: 9.5, bold: true, color: darkMetric ? C.white : C.ink });
  addText(slide, context, x + 0.16, y + 0.75, w - 0.32, 0.22, { fontSize: 7.8, color: darkMetric ? "BCD3C4" : C.muted });
}

function addNode(slide, label, detail, x, y, w, h, fill = C.white, accent = C.green) {
  addBox(slide, x, y, w, h, fill, C.line);
  slide.addShape(pptx.ShapeType.rect, { x, y, w: 0.07, h, fill: { color: accent }, line: { color: accent, width: 0 } });
  addText(slide, label, x + 0.16, y + 0.14, w - 0.28, 0.22, { fontSize: 9.5, bold: true, color: C.ink });
  addText(slide, detail, x + 0.16, y + 0.43, w - 0.28, h - 0.5, { fontSize: 7.5, color: C.muted });
}

function addTable(slide, x, y, colW, rowH, rows, opts = {}) {
  rows.forEach((row, r) => {
    let cx = x;
    const isHead = r === 0 && opts.header !== false;
    row.forEach((cell, c) => {
      const fill = isHead ? C.dark : r % 2 === 0 ? C.white : "FBFAF6";
      addBox(slide, cx, y + r * rowH, colW[c], rowH, fill, C.line, false);
      addText(slide, String(cell), cx + 0.08, y + r * rowH + 0.08, colW[c] - 0.16, rowH - 0.14, {
        fontSize: opts.fontSize || 7.5,
        bold: isHead,
        color: isHead ? C.white : C.ink,
      });
      cx += colW[c];
    });
  });
}

function thresholdBar(slide, x, y, w) {
  addText(slide, "Soil moisture status thresholds", x, y - 0.36, w, 0.22, { fontSize: 10, bold: true });
  slide.addShape(pptx.ShapeType.rect, { x, y, w: w * 0.3, h: 0.38, fill: { color: C.red }, line: { color: C.red, width: 0 } });
  slide.addShape(pptx.ShapeType.rect, { x: x + w * 0.3, y, w: w * 0.4, h: 0.38, fill: { color: C.green2 }, line: { color: C.green2, width: 0 } });
  slide.addShape(pptx.ShapeType.rect, { x: x + w * 0.7, y, w: w * 0.3, h: 0.38, fill: { color: C.teal }, line: { color: C.teal, width: 0 } });
  addText(slide, "DRY < 30%", x + 0.08, y + 0.1, w * 0.28, 0.16, { fontSize: 7.2, bold: true, color: C.white });
  addText(slide, "OPTIMAL 30-70%", x + w * 0.3 + 0.12, y + 0.1, w * 0.38, 0.16, { fontSize: 7.2, bold: true, color: C.ink });
  addText(slide, "WET > 70%", x + w * 0.7 + 0.12, y + 0.1, w * 0.28, 0.16, { fontSize: 7.2, bold: true, color: C.white });
  addText(slide, "0%", x, y + 0.5, 0.3, 0.14, { fontSize: 6.5, color: C.muted });
  addText(slide, "30%", x + w * 0.3 - 0.1, y + 0.5, 0.35, 0.14, { fontSize: 6.5, color: C.muted });
  addText(slide, "70%", x + w * 0.7 - 0.1, y + 0.5, 0.35, 0.14, { fontSize: 6.5, color: C.muted });
  addText(slide, "100%", x + w - 0.32, y + 0.5, 0.38, 0.14, { fontSize: 6.5, color: C.muted });
}

function addBars(slide, x, y, w, h, items) {
  addRule(slide, x, y + h, w, C.line, 0.5);
  const max = Math.max(...items.map((d) => d.value));
  const gap = 0.16;
  const bw = (w - gap * (items.length - 1)) / items.length;
  items.forEach((d, i) => {
    const bh = (d.value / max) * (h - 0.25);
    const bx = x + i * (bw + gap);
    const by = y + h - bh;
    addBox(slide, bx, by, bw, bh, d.color, d.color, true);
    addText(slide, d.valueLabel, bx, by - 0.27, bw, 0.18, { fontSize: 7, bold: true, color: C.ink });
    addText(slide, d.label, bx - 0.02, y + h + 0.08, bw + 0.04, 0.25, { fontSize: 6.5, color: C.muted });
  });
}

// 1 Cover
{
  const slide = pptx.addSlide();
  addBg(slide, C.dark);
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 0.22, h: H, fill: { color: C.amber }, line: { color: C.amber, width: 0 } });
  addRule(slide, 0.62, 0.64, 0.36, C.green2, 2);
  addText(slide, "SRTA3353 MACHINE LEARNING FOR IOT", 1.08, 0.5, 4.2, 0.24, { fontSize: 7.5, color: C.green2, bold: true });
  addText(slide, "Machine Learning-Based Smart Irrigation System", 0.62, 1.22, 9.8, 0.78, { fontFace: "Georgia", fontSize: 28, bold: true, color: C.white });
  addText(slide, "Predicting soil dryness before plant stress occurs", 0.62, 2.12, 7.5, 0.35, { fontSize: 15, color: "DCE9DD" });
  addText(slide, "Raspberry Pi 400 + DHT11 + soil sensor/MCP3008 + relay pump + OLED + Streamlit + Telegram/Favoriot", 0.62, 2.75, 10.4, 0.25, { fontSize: 10.2, color: "BCD3C4" });
  addMetric(slide, "3", "input sensor values", "soil moisture, temperature, humidity", 0.62, 4.02, 2.2, "17372B");
  addMetric(slide, "10 min", "prediction target", "demo can use 10 seconds", 3.2, 4.02, 2.2, "17372B");
  addMetric(slide, "Hybrid", "decision logic", "threshold baseline plus ML", 5.78, 4.02, 2.2, "17372B");
  addMetric(slide, "Live", "monitoring layer", "OLED, Streamlit, Telegram, Favoriot", 8.36, 4.02, 2.45, "17372B");
  addText(slide, "Prepared for Project 2: Hardware-Based IoT System Implementation", 0.62, 6.82, 6.4, 0.18, { fontSize: 7.8, color: "A7C7B3" });
  addText(slide, "01", 12.1, 6.82, 0.5, 0.18, { fontSize: 7, color: "A7C7B3", bold: true });
}

// 2 Problem
{
  const slide = pptx.addSlide();
  addHeader(slide, 2, "Problem fit", "The system shifts irrigation from reactive watering to predictive warning.");
  addText(slide, "Traditional small-plant watering reacts only after soil is already dry. In hot or low-humidity conditions, that delay can stress the plant before the pump starts.", 0.55, 1.78, 5.2, 0.62, { fontSize: 11, color: C.muted });
  addNode(slide, "Baseline system", "Soil is dry now -> pump ON. Simple and reliable, but late.", 0.75, 3.18, 2.55, 1.22, "FFF8F0", C.amber);
  addArrow(slide, 3.45, 3.77, 0.75, C.amber);
  addNode(slide, "Project system", "Soil is still optimal, but trend and environment show Dry Soon.", 4.35, 3.18, 3.2, 1.22, "F5FBF6", C.green);
  addArrow(slide, 7.7, 3.77, 0.75, C.green);
  addNode(slide, "Outcome", "Warn early, log evidence, and optionally control pump before stress.", 8.62, 3.18, 2.9, 1.22, "F4F7FB", C.teal);
  addBox(slide, 0.55, 5.16, 5.3, 0.82);
  addText(slide, "Target users", 0.78, 5.37, 1.5, 0.2, { fontSize: 9, bold: true, color: C.green });
  addText(slide, "Small plant owners, student labs, and greenhouse-style demos that need low-cost monitoring.", 0.78, 5.63, 4.5, 0.22, { fontSize: 8, color: C.muted });
  addBox(slide, 6.25, 5.16, 5.3, 0.82);
  addText(slide, "Application domain", 6.48, 5.37, 1.7, 0.2, { fontSize: 9, bold: true, color: C.teal });
  addText(slide, "Smart agriculture: soil moisture, temperature, humidity, irrigation automation, crop monitoring.", 6.48, 5.63, 4.5, 0.22, { fontSize: 8, color: C.muted });
}

// 3 Criteria coverage
{
  const slide = pptx.addSlide();
  addHeader(slide, 3, "Criteria coverage", "The prototype maps directly to the technical requirements.");
  const rows = [
    ["Assignment requirement", "Implementation evidence"],
    ["Raspberry Pi / hardware platform", "Raspberry Pi 400 runs full_monitor.py"],
    ["At least three input sensors/values", "DHT11 temperature, DHT11 humidity, soil moisture via MCP3008"],
    ["Output / actuator", "Relay controls DC water pump; OLED shows local status"],
    ["Real-time / near real-time processing", "READ_INTERVAL_SECONDS=600 normally; 10 seconds for demo"],
    ["Two data handling steps", "Calibration to percent, thresholding, feature extraction, missing-data handling"],
    ["Decision mechanism", "Hybrid: baseline threshold plus DecisionTreeClassifier prediction"],
    ["Monitoring layer", "Streamlit dashboard plus OLED display"],
    ["Automatic alert/control", "Pump control, Streamlit banners, Telegram notifications"],
    ["IoT visualization", "Streamlit as main dashboard; Favoriot REST payload kept for cloud visualization"],
  ];
  addTable(slide, 0.55, 1.74, [3.35, 7.9], 0.43, rows, { fontSize: 7.2 });
  addText(slide, "For final submission, include screenshots of Streamlit and Favoriot if the Favoriot device is configured.", 0.72, 6.18, 10.4, 0.22, { fontSize: 8, bold: true, color: C.green });
}

// 4 Hardware
{
  const slide = pptx.addSlide();
  addHeader(slide, 4, "Hardware proof", "The hardware path covers sensing, conversion, display, and actuation.");
  addNode(slide, "DHT11", "Temperature and humidity\nDefault pin: board.D4", 0.72, 2.02, 2.0, 1.18, "F9FBF5", C.green);
  addNode(slide, "Soil sensor AO", "Analog moisture signal", 0.72, 3.86, 2.0, 0.98, "FFF8F0", C.amber);
  addNode(slide, "MCP3008 ADC", "SPI analog-to-digital\nSoil channel: CH0", 3.3, 3.54, 2.2, 1.3, "F5F8FB", C.teal);
  addNode(slide, "Raspberry Pi 400", "Reads sensors, preprocesses, predicts, logs CSV, controls relay", 6.25, 2.86, 2.6, 1.68, "F5FBF6", C.green);
  addNode(slide, "OLED SSD1306", "I2C display shows temp, humidity, soil, ML, pump", 9.7, 2.02, 2.25, 1.18, C.white, C.blue);
  addNode(slide, "Relay + pump", "GPIO18 active LOW\nLOW = pump ON", 9.7, 3.86, 2.25, 1.18, "FFF8F0", C.red);
  addArrow(slide, 2.82, 2.58, 0.42, C.green);
  addArrow(slide, 2.82, 4.32, 0.42, C.amber);
  addArrow(slide, 5.6, 4.16, 0.55, C.teal);
  addArrow(slide, 8.92, 2.58, 0.55, C.blue);
  addArrow(slide, 8.92, 4.32, 0.55, C.red);
  addText(slide, "Important wiring checks: enable I2C for OLED, enable SPI for MCP3008, verify DHT pin, verify relay active-LOW behavior.", 0.9, 5.65, 10.8, 0.28, { fontSize: 9, bold: true, color: C.muted });
}

// 5 Flow
{
  const slide = pptx.addSlide();
  addHeader(slide, 5, "Software flow", "One Python loop connects hardware, ML, logging, and dashboards.");
  const labels = [
    ["Sensors", "DHT11 + soil AO"],
    ["full_monitor.py", "read, preprocess, predict"],
    ["Decision", "threshold + ML"],
    ["Outputs", "pump, OLED, alerts"],
    ["Data layer", "CSV + dashboard + cloud"],
  ];
  labels.forEach((d, i) => {
    const x = 0.65 + i * 2.4;
    addNode(slide, d[0], d[1], x, 2.45, 1.8, 1.08, i === 1 ? "F5FBF6" : C.white, i === 2 ? C.amber : C.green);
    if (i < labels.length - 1) addArrow(slide, x + 1.88, 2.98, 0.32, C.teal);
  });
  addNode(slide, "Telegram", "risk alerts with cooldown", 2.0, 4.55, 2.2, 0.95, "FFF8F0", C.amber);
  addNode(slide, "Streamlit", "latest metrics, charts, debug status", 5.05, 4.55, 2.75, 0.95, "F5F8FB", C.teal);
  addNode(slide, "Favoriot", "optional REST cloud payload", 8.7, 4.55, 2.2, 0.95, C.white, C.blue);
  addText(slide, "Streamlit reads plant_data.csv. It does not directly read sensors or control the pump.", 2.75, 6.05, 7.3, 0.22, { fontSize: 9, bold: true, color: C.green });
}

// 6 Processing
{
  const slide = pptx.addSlide();
  addHeader(slide, 6, "Data processing", "Preprocessing turns raw sensor values into reliable ML features.");
  thresholdBar(slide, 0.62, 2.15, 5.25);
  const rows = [
    ["Raw / issue", "Processing method", "Output"],
    ["Soil analog reading", "Calibrate to 0-100 percent", "soil_value"],
    ["Soil percentage", "Threshold classification", "DRY / OPTIMAL / WET"],
    ["Current + previous soil", "Feature extraction", "moisture_change_rate"],
    ["Pump ON/OFF text", "Encode for ML feature", "pump_status_code"],
    ["Incomplete training row", "Drop before training", "clean dataset"],
    ["Missing DHT11 data", "Do not average; return Unknown", "DHT Missing alert"],
  ];
  addTable(slide, 6.2, 1.78, [1.9, 2.85, 2.3], 0.48, rows, { fontSize: 6.9 });
  addBox(slide, 0.62, 3.55, 5.25, 1.8);
  addText(slide, "Why missing DHT11 is not averaged", 0.86, 3.77, 4.4, 0.23, { fontSize: 10, bold: true, color: C.green });
  addText(slide, "In real hardware, missing temperature or humidity may indicate wiring or sensor failure. Filling with an average can hide the fault and create fake weather conditions, so the safer output is ml_prediction = Unknown.", 0.86, 4.14, 4.55, 0.6, { fontSize: 8, color: C.muted });
  addText(slide, "This covers the assignment requirement for at least two data handling or preprocessing steps.", 0.86, 4.98, 4.55, 0.22, { fontSize: 8, bold: true, color: C.amber });
}

// 7 Intelligence
{
  const slide = pptx.addSlide();
  addHeader(slide, 7, "Intelligence", "The ML layer predicts future dryness instead of replacing the safe baseline.");
  const rows = [
    ["Item", "Baseline logic", "ML intelligent logic"],
    ["Main input", "Current soil only", "Soil, temp, humidity, previous soil, trend, pump"],
    ["Decision", "soil < 30% -> pump ON", "Predict Dry Soon / Not Dry Soon"],
    ["Behavior", "Reactive", "Predictive"],
    ["Example", "45% soil means pump OFF", "45% + hot/dry/falling trend can mean Dry Soon"],
  ];
  addTable(slide, 0.65, 1.9, [1.8, 3.4, 5.4], 0.62, rows, { fontSize: 7.6 });
  addNode(slide, "Default: recommend mode", "ML warns early, but threshold keeps direct pump control safer for demos.", 0.8, 5.45, 3.3, 0.75, "F5FBF6", C.green);
  addNode(slide, "Optional: control mode", "OPTIMAL + ML Dry Soon can turn pump ON early.", 4.55, 5.45, 3.3, 0.75, "FFF8F0", C.amber);
  addNode(slide, "Model", "DecisionTreeClassifier saved as models/dryness_model.joblib.", 8.3, 5.45, 3.3, 0.75, "F5F8FB", C.teal);
}

// 8 Training data
{
  const slide = pptx.addSlide();
  addHeader(slide, 8, "Model data", "Kaggle starts the model; real Raspberry Pi data improves it later.");
  addNode(slide, "1. Starter training", "Use data/training_smart_agriculture.csv.\nMOI -> soil_value; temp/humidity retained.", 0.8, 2.25, 2.55, 1.4, "F5F8FB", C.blue);
  addArrow(slide, 3.48, 2.95, 0.72, C.blue);
  addNode(slide, "2. Saved model", "Train Decision Tree and save models/dryness_model.joblib.", 4.35, 2.25, 2.45, 1.4, "F5FBF6", C.green);
  addArrow(slide, 6.95, 2.95, 0.72, C.green);
  addNode(slide, "3. Real-time prediction", "full_monitor.py loads model and predicts every sensor cycle.", 7.85, 2.25, 2.45, 1.4, C.white, C.teal);
  addArrow(slide, 10.45, 2.95, 0.55, C.teal);
  addNode(slide, "4. Retrain later", "Use collected plant_data.csv after enough real rows.", 11.1, 2.25, 1.45, 1.4, "FFF8F0", C.amber);
  addNode(slide, "Current behavior", "The model loads or trains at startup. It does not automatically retrain every 10 minutes.", 0.9, 4.45, 5.0, 1.1, C.white, C.green);
  addNode(slide, "Retraining explanation for lecturer", "If 20 days of real data exists in plant_data.csv, retraining uses the whole 20-day file unless manually filtered.", 7.0, 4.45, 5.0, 1.1, C.white, C.teal);
}

// 9 Dashboard
{
  const slide = pptx.addSlide();
  addHeader(slide, 9, "Dashboard", "Streamlit is the main live dashboard; Favoriot remains the IoT cloud path.");
  addBox(slide, 0.7, 1.8, 7.2, 4.35);
  addText(slide, "Streamlit dashboard mock", 0.95, 2.03, 3, 0.22, { fontSize: 10, bold: true, color: C.green });
  addMetric(slide, "45%", "soil moisture", "latest CSV reading", 0.95, 2.45, 1.45, "F5FBF6");
  addMetric(slide, "32 C", "temperature", "DHT11", 2.62, 2.45, 1.45, "FFF8F0");
  addMetric(slide, "55%", "humidity", "DHT11", 4.3, 2.45, 1.45, "F5F8FB");
  addMetric(slide, "OFF", "pump", "safe state", 5.98, 2.45, 1.32, "FBFAF6");
  addBars(slide, 1.05, 4.42, 5.9, 0.95, [
    { label: "soil", value: 45, valueLabel: "45%", color: C.green },
    { label: "temp", value: 32, valueLabel: "32 C", color: C.amber },
    { label: "humidity", value: 55, valueLabel: "55%", color: C.teal },
    { label: "trend", value: 8, valueLabel: "rate", color: C.blue },
  ]);
  addText(slide, "Charts are separated by unit: soil %, temperature C, humidity %, and moisture change rate.", 0.95, 5.72, 5.9, 0.22, { fontSize: 7.5, color: C.muted });
  addNode(slide, "Telegram", "Sends risk alerts to personal or group chat with cooldown.", 8.55, 2.0, 3.2, 0.95, "FFF8F0", C.amber);
  addNode(slide, "Favoriot", "REST payload includes temp, humidity, soil, pump, ML, notification status.", 8.55, 3.25, 3.2, 1.08, "F5F8FB", C.blue);
  addNode(slide, "OLED", "Shows SMART PLANT, DHT status, soil value, ML prediction, and pump status.", 8.55, 4.68, 3.2, 0.95, "F5FBF6", C.green);
}

// 10 Automation
{
  const slide = pptx.addSlide();
  addHeader(slide, 10, "Automation", "Pump control stays safe while alerts explain every risk state.");
  const rows = [
    ["Condition", "Recommend mode output", "Control mode output"],
    ["DRY soil", "Pump ON", "Pump ON"],
    ["WET soil", "Pump OFF + wet alert", "Pump OFF + wet alert"],
    ["OPTIMAL + Dry Soon", "Pump OFF + early warning", "Pump ON early"],
    ["DHT missing", "ML Unknown + DHT alert", "ML Unknown + DHT alert"],
  ];
  addTable(slide, 0.7, 1.95, [2.6, 3.85, 3.85], 0.65, rows, { fontSize: 8.2 });
  addNode(slide, "Telegram cooldown", "Same warning type sends once every 30 minutes normally, or every 60 seconds in demo mode.", 1.0, 5.28, 4.8, 0.85, "FFF8F0", C.amber);
  addNode(slide, "Reason codes", "PUMP_ON_DRY, PUMP_ON_ML_DRY_SOON, TELEGRAM_SENT, CSV_WRITE_OK, MODEL_LOADED.", 7.1, 5.28, 4.0, 0.85, "F5FBF6", C.green);
}

// 11 Testing demo
{
  const slide = pptx.addSlide();
  addHeader(slide, 11, "Demo plan", "A strong demo proves normal operation, abnormal states, and recovery.");
  const rows = [
    ["Demo scenario", "Action to show", "Expected evidence"],
    ["Normal / optimal soil", "Sensor in medium-moist soil", "Pump OFF, dashboard updates"],
    ["Dry soil", "Expose sensor to dry condition", "Pump ON, DRY alert"],
    ["Dry Soon", "Use warm/low humidity sample or model output", "Early warning, pump OFF in recommend mode"],
    ["Wet / overwatering", "Place sensor in very wet soil", "Pump OFF, WET alert"],
    ["Hardware fault", "Disconnect DHT11 briefly", "ML Unknown + DHT Missing alert"],
  ];
  addTable(slide, 0.65, 1.78, [2.25, 4.1, 4.35], 0.56, rows, { fontSize: 7.7 });
  addNode(slide, "Lecturer demo interval", "READ_INTERVAL_SECONDS=10, NOTIFICATION_COOLDOWN_SECONDS=60, STREAMLIT_REFRESH_SECONDS=10.", 1.0, 5.5, 5.0, 0.75, C.white, C.green);
  addNode(slide, "Normal collection", "READ_INTERVAL_SECONDS=600, NOTIFICATION_COOLDOWN_SECONDS=1800.", 7.2, 5.5, 4.0, 0.75, C.white, C.teal);
}

// 12 Submission evidence
{
  const slide = pptx.addSlide();
  addHeader(slide, 12, "Submission evidence", "The final story should show working hardware plus clear individual contribution.");
  const rows = [
    ["Marking area", "Evidence in project"],
    ["Problem relevance (5)", "Predictive smart agriculture watering before plant stress"],
    ["Hardware integration (10)", "Pi 400, DHT11, soil sensor, MCP3008, OLED, relay, pump"],
    ["Data communication (5)", "Streamlit, CSV logging, Telegram, Favoriot REST support"],
    ["Decision logic (5)", "Threshold baseline plus Decision Tree ML prediction"],
    ["Presentation/documentation (10)", "README, Student Guide, tests, demo scenarios, contribution evidence"],
  ];
  addTable(slide, 0.65, 1.84, [2.8, 7.8], 0.58, rows, { fontSize: 8 });
  addNode(slide, "Student 4 evidence", "Preprocessing, missing data handling, feature extraction, ML decision, baseline comparison.", 0.9, 5.55, 4.9, 0.75, "F5FBF6", C.green);
  addNode(slide, "Student 5 evidence", "Streamlit dashboard, charts, Telegram alerts, cloud/Favoriot payload, monitoring/debug tab.", 7.0, 5.55, 4.9, 0.75, "F5F8FB", C.teal);
}

const out = "\\\\wsl.localhost\\Ubuntu\\home\\jimmy_linux\\anaconda_projects\\iot\\project\\soil-moisture-iot\\outputs\\manual-20260615-smart-irrigation\\presentations\\smart-irrigation-slides\\output\\ML-Based_Smart_Irrigation_System.pptx";
await fs.mkdir(path.dirname(out), { recursive: true });
await pptx.writeFile({ fileName: out });
console.log(out);
