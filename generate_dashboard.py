import pandas as pd
import json
import os

# Define file paths
FILE_PATH = "c:/Users/mm16010130/Downloads/tickets_20260108_221513.csv"
OUTPUT_FILE = "c:/Users/mm16010130/Downloads/ErrorDashboard/dashboard.html"

# Load Data
print("Loading data...")
try:
    df = pd.read_csv(FILE_PATH)
except UnicodeDecodeError:
    df = pd.read_csv(FILE_PATH, encoding='latin1')
except Exception as e:
    print(f"Error loading CSV: {e}")
    exit(1)

# Preprocessing
print("Processing data...")
# Dates
df['fail_time'] = pd.to_datetime(df['fail_time'], errors='coerce')

# Error Column Logic
if 'error_message_nor' in df.columns:
    df['Analyzed_Error'] = df['error_message_nor'].fillna(df['error_message'])
else:
    df['Analyzed_Error'] = df['error_message']

# Data Cleaning
df['Analyzed_Error'] = df['Analyzed_Error'].astype(str).str.replace(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \| ERROR \| ', '', regex=True)

# Prepare data for Client-Side JSON
# We need ALL columns for the "Full Download" requirement
# Convert timestamps to string YYYY-MM-DD for easier JS handling
df['date_str'] = df['fail_time'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else "")

# Calculate Date Range before conversion
valid_dates = df['fail_time'].dropna()
if not valid_dates.empty:
    min_date = valid_dates.min().strftime('%Y-%m-%d')
    max_date = valid_dates.max().strftime('%Y-%m-%d')
else:
    min_date = ""
    max_date = ""

# Fill NaNs for safeguard in JS
df = df.fillna("")

# Convert all datetime columns to string
for col in df.select_dtypes(include=['datetime64', 'datetimetz']).columns:
    df[col] = df[col].astype(str)

# Convert entire dataframe to dict
data_records = df.to_dict(orient='records')
json_data = json.dumps(data_records)

# Unique values for dropdowns
unique_models = sorted(df['model'].unique().astype(str).tolist()) if 'model' in df.columns else []
unique_results = sorted(df['result'].unique().astype(str).tolist()) if 'result' in df.columns else []

# --- HTML Generation ---
print("Generating HTML...")

js_models = json.dumps(unique_models)
js_results = json.dumps(unique_results)

html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dynamic Error Analysis Dashboard</title>
    <!-- Plotly.js -->
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <!-- PapaParse for CSV parsing -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/PapaParse/5.3.0/papaparse.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f4f4f9;
            color: #333;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max_width: 1400px;
            margin: 0 auto;
        }}
        h1 {{
            text-align: center;
            color: #2c3e50;
        }}
        .controls {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 20px;
            justify-content: center;
            flex-wrap: wrap;
        }}
        .control-group {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        label {{
            font-weight: bold;
        }}
        input[type="date"], select {{
            padding: 8px;
            border: 1px solid #ccc;
            border-radius: 4px;
            min-width: 150px;
        }}
        button {{
            padding: 8px 16px;
            background-color: #3498db;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 1rem;
        }}
        button:hover {{
            background-color: #2980b9;
        }}
        .file-upload-wrapper {{
             position: relative;
             overflow: hidden;
             display: inline-block;
        }}
        .file-upload-btn {{
            border: 2px solid #3498db;
            color: #3498db;
            background-color: white;
            padding: 8px 20px;
            border-radius: 8px;
            font-weight: bold;
            cursor: pointer;
        }}
        .file-upload-btn:hover {{
            background-color: #3498db;
            color: white;
        }}
        .file-upload-wrapper input[type=file] {{
            font-size: 100px;
            position: absolute;
            left: 0;
            top: 0;
            opacity: 0;
            cursor: pointer;
        }}
        .reset-btn {{
            background-color: #e74c3c;
            color: white;
            border: none;
            padding: 4px 8px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.8rem;
        }}
        .reset-btn:hover {{
            background-color: #c0392b;
        }}
        .global-reset {{
            padding: 8px 16px;
            font-size: 1rem;
            background-color: #e74c3c;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }}
        .global-reset:hover {{
            background-color: #c0392b;
        }}
        .card {{
            background: white;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            padding: 20px;
            position: relative;
        }}
        .chart-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .chart-title {{
            font-size: 1.2rem;
            font-weight: bold;
            color: #2c3e50;
        }}
        .chart-actions {{
            display: flex;
            gap: 10px;
            align-items: center;
        }}
        .action-btn {{
            padding: 4px 8px;
            font-size: 0.8rem;
            background-color: #ecf0f1;
            color: #333;
            border: 1px solid #bdc3c7;
        }}
        .action-btn:hover {{
            background-color: #bdc3c7;
        }}
        .active-filters {{
            background-color: #dff9fb;
            border: 1px solid #c7ecee;
            color: #0097e6;
            padding: 10px;
            margin-bottom: 20px;
            border-radius: 4px;
            display: none; /* Hidden by default */
        }}
        .row {{
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
        }}
        .col {{
            flex: 1;
            min-width: 400px;
        }}
        .summary-stats {{
            display: flex;
            justify-content: space-around;
            margin-bottom: 20px;
            font-size: 1.2rem;
        }}
        /* Modal for Maximize */
        .modal {{
            display: none; 
            position: fixed; 
            z-index: 1000; 
            left: 0;
            top: 0;
            width: 100%; 
            height: 100%; 
            overflow: auto; 
            background-color: rgba(0,0,0,0.8); 
        }}
        .modal-content {{
            background-color: #fefefe;
            margin: 5% auto; 
            padding: 20px;
            border: 1px solid #888;
            width: 90%; 
            height: 80%;
            border-radius: 8px;
            position: relative;
        }}
        .close {{
            color: #aaa;
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
            position: absolute;
            right: 20px;
            top: 10px;
            z-index: 1001;
        }}
        .close:hover {{
            color: black;
        }}
        #modalChart {{
            width: 100%;
            height: 100%;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Dynamic Error Analysis Dashboard</h1>

        <div class="controls">
            <div class="file-upload-wrapper">
                <button class="file-upload-btn">📂 Upload CSV File</button>
                <input type="file" id="csvFileInput" accept=".csv" onchange="handleFileUpload(event)">
            </div>

            <div class="control-group">
                <label for="startDate">Start Date:</label>
                <input type="date" id="startDate" value="{min_date}">
            </div>
            <div class="control-group">
                <label for="endDate">End Date:</label>
                <input type="date" id="endDate" value="{max_date}">
            </div>
            
            <div class="control-group">
                <label for="modelSelect">Model:</label>
                <select id="modelSelect" onchange="updateDashboard()">
                    <option value="All">All</option>
                </select>
            </div>
            
            <div class="control-group">
                <label for="resultSelect">Result:</label>
                <select id="resultSelect" onchange="updateDashboard()">
                    <option value="All">All</option>
                </select>
            </div>

            <button class="global-reset" onclick="resetAllFilters()">Clear All Selection</button>
        </div>

        <div id="activeFilters" class="active-filters">
            <strong>Active Chart Filters:</strong> <span id="filterText"></span>
        </div>

        <div class="card">
            <div class="summary-stats" id="stats"></div>
        </div>

        <!-- 1. Timeline -->
        <div class="card">
            <div class="chart-header">
                <div class="chart-title">Trend Failure</div>
                <div class="chart-actions">
                    <button class="reset-btn" id="btn-reset-date" onclick="clearFilter('date')" style="display:none;">Clear Selection</button>
                    <button class="action-btn" onclick="maximizeChart('timelineGraph', 'Trend Failure')">Maximize</button>
                    <button class="action-btn" style="background-color: #27ae60; color: white;" onclick="downloadRawData()">Download Raw Data</button>
                </div>
            </div>
            <div id="timelineGraph"></div>
        </div>

        <!-- 2. Test Items -->
        <div class="card">
            <div class="chart-header">
                <div class="chart-title">Top Test Items (Fails)</div>
                <div class="chart-actions">
                     <button class="reset-btn" id="btn-reset-testItem" onclick="clearFilter('testItem')" style="display:none;">Clear Selection</button>
                    <button class="action-btn" onclick="maximizeChart('testItemGraph', 'Top Test Items')">Maximize</button>
                    <button class="action-btn" style="background-color: #27ae60; color: white;" onclick="downloadRawData()">Download Raw Data</button>
                </div>
            </div>
            <div id="testItemGraph"></div>
        </div>

        <div class="row">
            <!-- 3. Top Errors -->
            <div class="col card">
                <div class="chart-header">
                    <div class="chart-title">Top 10 Errors</div>
                    <div class="chart-actions">
                        <button class="reset-btn" id="btn-reset-error" onclick="clearFilter('error')" style="display:none;">Clear Selection</button>
                        <button class="action-btn" onclick="maximizeChart('topErrorsGraph', 'Top 10 Errors')">Maximize</button>
                        <button class="action-btn" style="background-color: #27ae60; color: white;" onclick="downloadRawData()">Download Raw Data</button>
                    </div>
                </div>
                <div id="topErrorsGraph"></div>
            </div>
            
            <!-- 4. Result -->
            <div class="col card">
                <div class="chart-header">
                    <div class="chart-title">Result Distribution</div>
                    <div class="chart-actions">
                        <button class="reset-btn" id="btn-reset-result" onclick="clearFilter('result')" style="display:none;">Clear Selection</button>
                        <button class="action-btn" onclick="maximizeChart('resultGraph', 'Result Distribution')">Maximize</button>
                        <button class="action-btn" style="background-color: #27ae60; color: white;" onclick="downloadRawData()">Download Raw Data</button>
                    </div>
                </div>
                <div id="resultGraph"></div>
            </div>
        </div>
        
    </div>

    <!-- Modal -->
    <div id="chartModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal()">&times;</span>
            <div id="modalChart"></div>
        </div>
    </div>

    <script>
        let rawData = {json_data};
        let uniqueModels = {js_models};
        let uniqueResults = {js_results};

        // State for click-interactions
        let selectedClickFilters = {{
            date: null,
            error: null,
            testItem: null,
            result: null
        }};

        // Data currently shown (for download)
        let currentFilteredData = [];

        // --- File Upload Handler ---
        function handleFileUpload(event) {{
            const file = event.target.files[0];
            if (!file) return;

            Papa.parse(file, {{
                header: true,
                skipEmptyLines: true,
                complete: function(results) {{
                    processUploadedData(results.data);
                }},
                error: function(error) {{
                    alert("Error parsing CSV: " + error.message);
                }}
            }});
        }}

        // Initialize listeners once
        let listenersAttached = false;

        function attachListeners() {{
            if(listenersAttached) return;
            
            const ids = ['timelineGraph', 'testItemGraph', 'topErrorsGraph', 'resultGraph'];
            const filters = ['date', 'testItem', 'error', 'result'];
            
            ids.forEach((id, idx) => {{
                const el = document.getElementById(id);
                el.on('plotly_click', function(data){{
                    if(data.points.length > 0) {{
                        let val;
                        if(filters[idx] === 'date') val = data.points[0].x;
                        else if(filters[idx] === 'testItem') val = data.points[0].x;
                        else if(filters[idx] === 'error') val = data.points[0].y; // Horizontal bar
                        else if(filters[idx] === 'result') val = data.points[0].label;
                        
                        selectedClickFilters[filters[idx]] = val;
                        updateDashboard();
                    }}
                }});
            }});
            
            listenersAttached = true;
        }}

        function processUploadedData(data) {{
            // Clean and transform data (Mirroring Python logic)
            // 1. fail_time -> date_str (YYYY-MM-DD)
            // 2. error_message_nor (or error_message) -> Analyzed_Error (clean timestamp)
            
            const processed = data.map(row => {{
                // Date Processing
                let dateStr = "";
                if (row.fail_time) {{
                    const d = new Date(row.fail_time);
                    if (!isNaN(d.getTime())) {{
                        dateStr = d.toISOString().split('T')[0];
                    }}
                }}
                row.date_str = dateStr;

                // Error Processing
                let rawError = row.error_message_nor || row.error_message || "Unknown";
                // Regex to remove "YYYY-MM-DD HH:MM:SS | ERROR | "
                let cleanError = rawError.replace(/\\d{{4}}-\\d{{2}}-\\d{{2}} \\d{{2}}:\\d{{2}}:\\d{{2}} \\| ERROR \\| /, "");
                row.Analyzed_Error = cleanError;

                // Ensure test_item exists (trim whitespace if present)
                if(row.test_item) row.test_item = row.test_item.trim();

                return row;
            }});

            rawData = processed;
            
            // Re-calculate unique values
            const models = new Set();
            const results = new Set();
            
            // Update Min/Max dates
            let minD = null;
            let maxD = null;

            processed.forEach(r => {{
                if(r.model) models.add(r.model);
                if(r.result) results.add(r.result);
                if(r.date_str) {{
                    if(!minD || r.date_str < minD) minD = r.date_str;
                    if(!maxD || r.date_str > maxD) maxD = r.date_str;
                }}
            }});

            uniqueModels = Array.from(models).sort();
            uniqueResults = Array.from(results).sort();

            // Update UI Controls
            if(minD) document.getElementById('startDate').value = minD;
            if(maxD) document.getElementById('endDate').value = maxD;
            
            refreshDropdowns();
            resetAllFilters(); // Helper will call updateDashboard
            
            alert(`File loaded successfully! ${{processed.length}} records processed.`);
        }}

        function refreshDropdowns() {{
            const modelSel = document.getElementById('modelSelect');
            modelSel.innerHTML = '<option value="All">All</option>';
            uniqueModels.forEach(m => {{
                const opt = document.createElement('option');
                opt.value = m;
                opt.textContent = m;
                modelSel.appendChild(opt);
            }});

            const resultSel = document.getElementById('resultSelect');
            resultSel.innerHTML = '<option value="All">All</option>';
            uniqueResults.forEach(r => {{
                const opt = document.createElement('option');
                opt.value = r;
                opt.textContent = r;
                resultSel.appendChild(opt);
            }});
        }}


        function populateDropdowns() {{
             refreshDropdowns();
        }}

        function processData() {{
            const startDateInput = document.getElementById('startDate').value;
            const endDateInput = document.getElementById('endDate').value;
            const selectedModel = document.getElementById('modelSelect').value;
            const selectedResult = document.getElementById('resultSelect').value;
            
            const start = startDateInput ? new Date(startDateInput) : new Date('1900-01-01');
            const end = endDateInput ? new Date(endDateInput) : new Date('2100-01-01');
            end.setHours(23, 59, 59, 999);

            return rawData.filter(row => {{
                // 1. Static Filters (Top Bar)
                if (row.date_str) {{
                    const d = new Date(row.date_str);
                    if (d < start || d > end) return false;
                }}
                if (selectedModel !== 'All' && row.model !== selectedModel) return false;
                if (selectedResult !== 'All' && row.result !== selectedResult) return false;

                // 2. Click Interaction Filters
                if (selectedClickFilters.date && row.date_str !== selectedClickFilters.date) return false;
                if (selectedClickFilters.error && row.Analyzed_Error !== selectedClickFilters.error) return false;
                if (selectedClickFilters.testItem && row.test_item !== selectedClickFilters.testItem) return false;
                if (selectedClickFilters.result && row.result !== selectedClickFilters.result) return false;

                return true;
            }});
        }}

        function updateDashboard() {{
            const data = processData();
            currentFilteredData = data; // Store for download
            const totalCount = data.length;

            updateFilterDisplay();

            document.getElementById('stats').innerHTML = `<div>Total Records: <strong>${{totalCount}}</strong></div>`;

            // Always render, even if empty, to show blank state
            renderCharts(data, totalCount);
        }}

        function renderCharts(data, totalCount) {{
             // 1. Timeline
            const dateCounts = {{}};
            data.forEach(r => {{ if(r.date_str) dateCounts[r.date_str] = (dateCounts[r.date_str] || 0) + 1; }});
            const sortedDates = Object.keys(dateCounts).sort();
            
            const timelineLayout = {{
                margin: {{t: 10, l: 40}},
                xaxis: {{title: 'Date'}},
                yaxis: {{title: 'Count'}}
            }};

            Plotly.newPlot('timelineGraph', [{{
                x: sortedDates,
                y: sortedDates.map(d => dateCounts[d]),
                type: 'scatter',
                mode: 'lines+markers',
                marker: {{color: '#3498db'}},
                line: {{shape: 'spline'}}
            }}], timelineLayout);

            // Listener removed from here

            // 2. Test Items
            const itemCounts = {{}};
            data.forEach(r => {{
                const ti = r.test_item || "Unknown";
                itemCounts[ti] = (itemCounts[ti] || 0) + 1;
            }});
            const sortedItems = Object.entries(itemCounts).sort((a,b)=>b[1]-a[1]).slice(0, 15);

            Plotly.newPlot('testItemGraph', [{{
                x: sortedItems.map(i => i[0]),
                y: sortedItems.map(i => i[1]),
                type: 'bar',
                marker: {{color: '#9b59b6'}}
            }}], {{
                margin: {{t: 10, b: 100}},
                xaxis: {{tickangle: -45}}
            }});

            // Listener removed from here

            // 3. Top Errors
            const errorCounts = {{}};
            data.forEach(r => {{ errorCounts[r.Analyzed_Error] = (errorCounts[r.Analyzed_Error] || 0) + 1; }});
            const sortedErrors = Object.entries(errorCounts).sort((a,b)=>b[1]-a[1]).slice(0, 10);

            Plotly.newPlot('topErrorsGraph', [{{
                x: sortedErrors.map(e => e[1]),
                y: sortedErrors.map(e => e[0]),
                type: 'bar',
                orientation: 'h',
                text: sortedErrors.map(e => `${{e[1]}} (${{((e[1]/totalCount)*100).toFixed(1)}}%)`),
                textposition: 'auto',
                marker: {{color: '#e74c3c'}}
            }}], {{
                margin: {{t: 10, l: 400}},
                yaxis: {{autorange: 'reversed'}}
            }});

            // Listener removed from here

            // 4. Result
            const resCounts = {{}};
            data.forEach(r => {{ resCounts[r.result] = (resCounts[r.result] || 0) + 1; }});
            const resKeys = Object.keys(resCounts);

            Plotly.newPlot('resultGraph', [{{
                labels: resKeys,
                values: Object.values(resCounts),
                type: 'pie',
                textinfo: 'label+percent',
                marker: {{colors: ['#2ecc71', '#f1c40f', '#e74c3c']}}
            }}], {{
                margin: {{t: 10}}
            }});

            // Listener removed from here
            
            // Attach listeners safely
            attachListeners();
        }}

        function updateFilterDisplay() {{
            const div = document.getElementById('activeFilters');
            const txt = document.getElementById('filterText');
            let parts = [];
            
            // Manage "Clear Selection" buttons visibility
            document.getElementById('btn-reset-date').style.display = selectedClickFilters.date ? 'inline-block' : 'none';
            document.getElementById('btn-reset-error').style.display = selectedClickFilters.error ? 'inline-block' : 'none';
            document.getElementById('btn-reset-testItem').style.display = selectedClickFilters.testItem ? 'inline-block' : 'none';
            document.getElementById('btn-reset-result').style.display = selectedClickFilters.result ? 'inline-block' : 'none';

            if(selectedClickFilters.date) parts.push(`Date: ${{selectedClickFilters.date}}`);
            if(selectedClickFilters.error) parts.push(`Error: ${{selectedClickFilters.error}}`);
            if(selectedClickFilters.testItem) parts.push(`Test Item: ${{selectedClickFilters.testItem}}`);
            if(selectedClickFilters.result) parts.push(`Result: ${{selectedClickFilters.result}}`);

            if(parts.length > 0) {{
                div.style.display = 'block';
                txt.innerHTML = parts.join(' | ');
            }} else {{
                div.style.display = 'none';
            }}
        }}

        function clearFilter(type) {{
            selectedClickFilters[type] = null;
            updateDashboard();
        }}

        function resetAllFilters() {{
            selectedClickFilters = {{ date: null, error: null, testItem: null, result: null }};
            updateDashboard();
        }}

        // --- Utils ---
        function maximizeChart(id, title) {{
            document.getElementById('chartModal').style.display = "block";
            const src = document.getElementById(id);
            const layout = JSON.parse(JSON.stringify(src.layout));
            layout.title = title;
            layout.margin = {{t: 50, l: 50, r: 50, b: 100}};
            if(id === 'topErrorsGraph') layout.margin.l = 400;
            
            Plotly.newPlot('modalChart', src.data, layout);
        }}

        function closeModal() {{
            document.getElementById('chartModal').style.display = "none";
            Plotly.purge('modalChart');
        }}
        
        window.onclick = function(e) {{ if(e.target == document.getElementById('chartModal')) closeModal(); }};

        function downloadRawData() {{
            const data = currentFilteredData;
            if(!data || data.length === 0) return alert("No data to download");
            
            const headers = Object.keys(data[0]);
            const csvRows = [headers.join(",")];
            
            data.forEach(row => {{
                const values = headers.map(header => {{
                    let val = row[header] === null || row[header] === undefined ? "" : "" + row[header];
                    val = val.replace(/\\"/g, '""');
                    if (val.search(/("|,|\\n)/g) >= 0) val = `"${{val}}"`;
                    return val;
                }});
                csvRows.push(values.join(","));
            }});
            
            const blob = new Blob([csvRows.join("\\n")], {{ type: 'text/csv;charset=utf-8;' }});
            const link = document.createElement("a");
            link.href = URL.createObjectURL(blob);
            link.download = `raw_data_export.csv`;
            link.style.display = "none";
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }}

        window.addEventListener('DOMContentLoaded', () => {{
            populateDropdowns();
            updateDashboard();
        }});
    </script>
</body>
</html>
"""

# Write to file
try:
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Dashboard successfully created at: {OUTPUT_FILE}")
except Exception as e:
    print(f"Error writing HTML file: {e}")
