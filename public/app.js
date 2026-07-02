let CONFIG = {
    refreshInterval: 2000,
    jsonPath: '../outputs/plant_data.json', // Path to the JSON file
    dryThreshold: 30.0
};

// State
let updateTimer = null;
let historyData = {
    timestamps: [],
    soil: [],
    temp: [],
    humidity: []
};
let latestDataPoint = null;

// ── Tab Navigation ──
document.querySelectorAll('.nav-item').forEach(button => {
    button.addEventListener('click', (e) => {
        document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        const btn = e.currentTarget;
        btn.classList.add('active');
        const tabId = 'tab-' + btn.getAttribute('data-tab');
        document.getElementById(tabId).classList.add('active');
        
        window.dispatchEvent(new Event('resize'));
    });
});

// ── Settings Handlers ──
document.getElementById('apply-settings').addEventListener('click', () => {
    CONFIG.refreshInterval = parseInt(document.getElementById('refresh-interval').value) * 1000;
    CONFIG.jsonPath = document.getElementById('csv-file-name').value;
    
    if (updateTimer) clearInterval(updateTimer);
    if (document.getElementById('auto-refresh').checked) {
        updateTimer = setInterval(fetchData, Math.max(CONFIG.refreshInterval, 1000));
    }
    fetchData();
});

document.getElementById('auto-refresh').addEventListener('change', (e) => {
    if (e.target.checked) {
        updateTimer = setInterval(fetchData, Math.max(CONFIG.refreshInterval, 1000));
        fetchData();
    } else {
        if (updateTimer) clearInterval(updateTimer);
    }
});

// ── Main Data Fetcher ──
async function fetchData() {
    try {
        const res = await fetch(`${CONFIG.jsonPath}?t=${new Date().getTime()}`);
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        
        const data = await res.json();
        
        if (!Array.isArray(data) || data.length === 0) return;
        
        if (document.getElementById('alerts-container').innerHTML.includes('Failed to load')) {
            document.getElementById('alerts-container').innerHTML = '';
            latestDataPoint = null; // Force a full UI redraw to restore proper alerts
        }
        
        processData(data);
        document.getElementById('last-update').innerText = 'Last updated: ' + new Date().toLocaleTimeString();
        
    } catch (error) {
        console.error("Fetch error:", error);
        document.getElementById('alerts-container').innerHTML = ''; 
        showAlert('error', `Failed to load ${CONFIG.jsonPath}. Make sure you started the server from the MAIN project folder!`);
    }
}

// ── Data Processing ──
function processData(dataArray) {
    // We expect dataArray to be an array of all CSV rows.
    const latest = dataArray[dataArray.length - 1];
    
    // Prevent duplicate entries if the file hasn't been updated
    if (latestDataPoint && latestDataPoint.timestamp === latest.timestamp) {
        return; 
    }
    latestDataPoint = latest;

    // Use all available data to instantly fill charts
    const recent = dataArray;
    // Pass the raw timestamp so Plotly can format it automatically based on zoom level (e.g. days)
    historyData.timestamps = recent.map(r => r.timestamp);
    historyData.soil = recent.map(r => r.soil_value);
    historyData.temp = recent.map(r => r.temperature);
    historyData.humidity = recent.map(r => r.humidity);

    updateMetrics(latest);
    updateCharts(latest);
    updateDebug(latest);
    processAlerts(latest);
}

// ── UI Updaters ──
function updateMetrics(data) {
    const _v = (val, dec=1) => (val !== null && val !== undefined) ? Number(val).toFixed(dec) : '--';
    
    // Soil
    const currentSoil = _v(data.soil_value);
    document.getElementById('current-soil').innerText = currentSoil !== '--' ? currentSoil + '%' : '--';
    const soilStatusEl = document.getElementById('current-soil-status');
    soilStatusEl.innerText = data.soil_status || 'UNKNOWN';
    soilStatusEl.className = 'status-badge ' + (data.soil_status === 'DRY' ? 'status-dry' : 'status-optimal');
    
    // Forecast 
    const f4 = data.forecast_soil_4hr;
    document.getElementById('forecast-4h').innerText = f4 ? _v(f4) + '%' : '--';
    const f4StatusEl = document.getElementById('forecast-4h-status');
    const f4Status = (f4 && Number(f4) < CONFIG.dryThreshold) ? 'DRY' : 'OPTIMAL';
    f4StatusEl.innerText = f4 ? f4Status : 'NO DATA';
    f4StatusEl.className = 'status-badge ' + (f4Status === 'DRY' ? 'status-dry' : 'status-optimal');
    
    // Environment
    document.getElementById('current-temp').innerText = _v(data.temperature) + '°C';
    document.getElementById('current-humidity').innerText = _v(data.humidity) + '%';
    
    // Pump Alerts
    document.getElementById('pump-status').innerText = data.pump_status === 'ON' ? 'ON' : 'OFF';
    document.getElementById('forecast-risk').innerText = (data.forecast_risk === 'Dry Forecast' || data.forecast_risk === 1.0) ? 'Risk Detected' : 'All Clear';
}

function processAlerts(data) {
    const container = document.getElementById('alerts-container');
    container.innerHTML = ''; 
    
    const events = [];
    if (data.soil_status === 'DRY') events.push("Soil is currently DRY!");
    if (data.forecast_risk === 'Dry Forecast' || data.forecast_risk === 1.0) events.push("Forecast predicts dry soil soon.");
    if (data.pump_status === 'ON') events.push("Pump is activated.");
    
    if (events.length === 0) {
        showAlert('success', 'System Normal: No critical risks detected.');
    } else {
        events.forEach(e => showAlert(e.includes('DRY') ? 'error' : 'warning', e));
    }
}

function showAlert(type, message) {
    const container = document.getElementById('alerts-container');
    const div = document.createElement('div');
    div.className = `alert alert-${type}`;
    
    let icon = 'ℹ️';
    if(type === 'error') icon = '🚨';
    if(type === 'warning') icon = '⚠️';
    if(type === 'success') icon = '✅';
    
    div.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    container.appendChild(div);
}

function updateDebug(data) {
    document.getElementById('debug-json').textContent = JSON.stringify(data, null, 2);
}

// ── Charting (Plotly.js) ──
function updateCharts(latestData) {
    const layoutConfig = {
        margin: { t: 40, r: 20, b: 40, l: 40 },
        hovermode: 'x unified',
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { family: 'Outfit, sans-serif' },
        xaxis: { 
            gridcolor: 'rgba(100,116,139,0.1)',
            type: 'date'
        },
        yaxis: { gridcolor: 'rgba(100,116,139,0.1)' }
    };
    
    const isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (isDark) {
        layoutConfig.font.color = '#f8fafc';
    }

    // 1. Forecast Chart
    const f4 = latestData.forecast_soil_4hr;
    const f6 = latestData.forecast_soil_6hr;
    const f8 = latestData.forecast_soil_8hr;
    
    if (f4 !== undefined && f4 !== null) {
        const traceFore = {
            x: ['Now', '+4 Hrs', '+6 Hrs', '+8 Hrs'],
            y: [latestData.soil_value, f4, f6, f8],
            type: 'scatter', mode: 'lines+markers',
            name: 'Forecast',
            line: {color: '#3b82f6', width: 3, shape: 'spline'},
            marker: {size: 10}
        };
        const traceThresh = {
            x: ['Now', '+4 Hrs', '+6 Hrs', '+8 Hrs'],
            y: [CONFIG.dryThreshold, CONFIG.dryThreshold, CONFIG.dryThreshold, CONFIG.dryThreshold],
            type: 'scatter', mode: 'lines',
            name: 'Dry Threshold',
            line: {color: '#ef4444', dash: 'dash'}
        };
        
        Plotly.react('forecast-chart', [traceFore, traceThresh], {...layoutConfig, showlegend: false, xaxis: {...layoutConfig.xaxis, type: 'category'}});
    } else {
        document.getElementById('forecast-chart').innerHTML = '<div style="padding: 20px; color: #64748b;">No ML forecast provided in JSON yet.</div>';
    }

    // 2. Historical Soil
    Plotly.react('history-soil-chart', [{
        x: historyData.timestamps, y: historyData.soil, type: 'scatter', mode: 'lines',
        fill: 'tozeroy', fillcolor: 'rgba(16, 185, 129, 0.1)',
        line: {color: '#10b981', width: 2}
    }], {...layoutConfig, title: 'Soil Moisture'});
    
    // 3. Historical Temp
    Plotly.react('history-temp-chart', [{
        x: historyData.timestamps, y: historyData.temp, type: 'scatter', mode: 'lines',
        line: {color: '#f59e0b', width: 2}
    }], {...layoutConfig, title: 'Temperature'});
    
    // 4. Historical Humidity
    Plotly.react('history-hum-chart', [{
        x: historyData.timestamps, y: historyData.humidity, type: 'scatter', mode: 'lines',
        line: {color: '#8b5cf6', width: 2}
    }], {...layoutConfig, title: 'Humidity'});
}

window.addEventListener('resize', () => {
    ['forecast-chart', 'history-soil-chart', 'history-temp-chart', 'history-hum-chart'].forEach(id => {
        const el = document.getElementById(id);
        if (el && el.innerHTML !== "" && !el.innerHTML.includes('No ML forecast')) {
            Plotly.Plots.resize(id);
        }
    });
});

// Setup input defaults
document.getElementById('csv-file-name').value = CONFIG.jsonPath;

updateTimer = setInterval(fetchData, CONFIG.refreshInterval);
fetchData();
