import pandas as pd
import json
import os
import re

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
# User requested strict usage of 'error_message_nor'
if 'error_message_nor' in df.columns:
    # Use error_message_nor, fill with "Unknown" or empty if missing, 
    # but the user emphasis implies we should trust this column.
    # We will still fallback for now to avoid empty charts if data is poor, 
    # but logically prioritize it.
    df['Analyzed_Error'] = df['error_message_nor'].fillna("Unknown")
else:
    df['Analyzed_Error'] = df['error_message'] 


# Data Cleaning
# 1. Remove initial prefix
df['Analyzed_Error'] = df['Analyzed_Error'].astype(str).str.replace(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \| ERROR \| ', '', regex=True)

# 2. Standardize specific patterns (Dates, IPs, Session IDs)
def standardize_error(err):
    # Specialized replacement for "does not appear to be an IPv4 or IPv6 address"
    # This groups all variations of this specific error into one single bucket.
    if "does not appear to be an IPv4 or IPv6 address" in err:
         return "'Last login: DATE from XXX.XXX.XXX.XXXstart serial session -i XX -b X\\n\\n\\nip addr\\nWcsCli# start serial session -i XX -b X\\n' does not appear to be an IPv4 or IPv6 address"

    # Specialized replacement for "create account - fail"
    if err.strip().endswith("create account - fail"):
        return "UXX create account - fail"
        
    # Specialized replacement for "timed out. (connect timeout=30)'))"
    if err.strip().endswith("timed out. (connect timeout=30)'))"):
        return "HTTPConnectionPool(host='XXX.XXX.XXX.{id}', port=5985): Max retries exceeded with url: /wsman (Caused by ConnectTimeoutError(<urllib3.connection.HTTPConnection object at XxXXXXXXXXXXXXX>, 'Connection to XXX.XXX.XXX.XXX timed out. (connect timeout=30)'))"

    # Specialized replacement for "check BMC FW Version"
    if err.startswith("check BMC FW Version") and "Failed to ping" in err:
        return "check BMC FW Version, expected equal to C2195.BC.0406, actual: C2195.BC.0405 - Fail\nFailed to ping 172.XXX.XXX.XXX, DUT is not reachable."

    # Specialized replacement for "Command [show manager relay -p"
    if err.startswith("Command [show manager relay -p"):
        return "Command [show manager relay -p X] timeout."

    # Specialized replacement for "check DIMM Locator"
    if err.startswith("check DIMM Locator, expected equal to DIMM_"):
        return "check DIMM Locator, expected equal to DIMM_XN, actual: DIMM_XN - Fail\ncheck DIMM Quantity, expected equal to 12, actual: {not equality} - Fail"

    # Specialized replacement for "Invalid SFCS stage"
    if err.startswith("Invalid SFCS stage, expected:"):
        return "Invalid SFCS stage, expected: Zz, actual: Xx"

    # Specialized replacement for "check sensor Fan_"
    if err.startswith("check sensor Fan_"):
        return "check sensor Fan_Nx reading, expected equal to ok, actual: ns - Fail\nL10 BMC SDR check fail"

    # Specialized replacement for "didn't have device exist in OS"
    if err.strip().endswith("didn't have device exist in OS"):
        return "This BDF XXXX:XX:XX.X didn't have device exist in OS"

    # Specialized replacement for "check System SN"
    if err.startswith("check System SN, expected equal to"):
        return "check System SN, expected equal to PXXXXXXXXXXXXXXX, actual: PYYYYYYYYYYYYYYY - Fail"

    # Specialized replacement for "TOR switch" and "expected equal to OK, actual: NOT - Fail"
    if "expected equal to OK, actual: NOT - Fail" in err and "TOR switch" in err:
        return "check psuXpwr-511-ac-red, expected equal to OK, actual: NOT - Fail\nTOR switch M1171500-001 (DATA_SW, UXX) - Fail"

    # Specialized replacement for "Failed to process the command: ping -c"
    if err.startswith("Failed to process the command: ping -c"):
        return "Failed to process the command: ping -c X -i X -W XX 172.XX.XX.XX"

    # Specialized replacement for "check BMC FW Version" and "Command [set system bmc update -i"
    # We use a substring check for the first part to avoid issues with exact whitespace matching
    if "check BMC FW Version" in err and "Command [set system bmc update -i" in err:
        return "check BMC FW Version, expected equal to C2195.BC.0406, actual: C2195.BC.0405 - Fail\nCommand [set system bmc update -i X -f C2195.BC.0406.00.bin] timeout."

    # Specialized replacement for "Failed to 'GetUSNGenealogyBasic'"
    if err.startswith("Failed to 'GetUSNGenealogyBasic' with {'UnitSerialNumber': 'P"):
        return "Failed to 'GetUSNGenealogyBasic' with {'UnitSerialNumber': 'P{id}', 'StageCode': 'XX'}"

    # Specialized replacement for "Failed to execute RM cmd: 'set system psu update -i"
    if err.startswith("Failed to execute RM cmd: 'set system psu update -i"):
        return "Failed to execute RM cmd: 'set system psu update -i X -f File.hex -t X'"

    # Specialized replacement for "<pypsrp.powershell.PSDataStreams object at"
    if err.startswith("<pypsrp.powershell.PSDataStreams object at"):
        return "<pypsrp.powershell.PSDataStreams object at 0x7XXXXXXXXXXXX>\nrc=True, Failed to execute cmd 'cd ~\\.\\inband_tools\\MPF_latest; .\\s ;'"

    # Specialized replacement for "Get tpm ekcert from sfcs error"
    if err.startswith("Get tpm ekcert from sfcs error"):
        return "Get tpm ekcert from sfcs error, error message: ['NoneType' object has no attribute 'get']\nGet dcscmsn[M1304365002B5293XXXXXXX] ekcert failed in SFCS/MES."

    # Specialized replacement for "Unable to send RAW command"
    if "Unable to send RAW command (channel=0x0 netfn=0x34 lun=0x0 cmd=0x93 rsp=0xd5): Command not supported in present state" in err:
        return "Failed to execute RM cmd: 'set system cmd -i XX -c raw 0x34 0x93 0x01 0x04', 'Completion Code: Failure', 'Status Description: Failed to run command ['raw', '0x{id}', '0x{id}', '0x{id}', '0x{id}'] with error: Unable to send RAW command (channel=0x0 netfn=0x34 lun=0x0 cmd=0x93 rsp=0xd5): Command not supported in present state'"

    # Date: Fri Jan  9 09:24:01 2026
    err = re.sub(r'[A-Za-z]{3}\s+[A-Za-z]{3}\s+\d+\s+\d{2}:\d{2}:\d{2}\s+\d{4}', 'DATE', err)
    # IP: 172.17.6.32
    err = re.sub(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', 'XXX.XXX.XXX.XXX', err)
    # Session ID: -i 35 -> -i XX
    err = re.sub(r'-i\s+\d+', '-i XX', err)
    # Session ID: -b 1 -> -b X
    err = re.sub(r'-b\s+\d+', '-b X', err)
    return err

df['Analyzed_Error'] = df['Analyzed_Error'].apply(standardize_error)

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
        <div class="row">
            <!-- 2. Test Items (Bar) -->
            <div class="col card">
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

            <!-- 2b. Test Item Distribution (Pie) -->
            <div class="col card">
                <div class="chart-header">
                    <div class="chart-title">Test Item Distribution</div>
                    <div class="chart-actions">
                         <button class="reset-btn" id="btn-reset-testItemPie" onclick="clearFilter('testItem')" style="display:none;">Clear Selection</button>
                        <button class="action-btn" onclick="maximizeChart('testItemPie', 'Test Item Distribution')">Maximize</button>
                        <button class="action-btn" style="background-color: #27ae60; color: white;" onclick="downloadRawData()">Download Raw Data</button>
                    </div>
                </div>
                <div id="testItemPie"></div>
            </div>
        </div>

        <div class="row">
            <!-- 3. Top Errors (Bar) -->
            <div class="col card">
                <div class="chart-header">
                    <div class="chart-title">Top 10 Errors (Frequency)</div>
                    <div class="chart-actions">
                        <button class="reset-btn" id="btn-reset-error" onclick="clearFilter('error')" style="display:none;">Clear Selection</button>
                        <button class="action-btn" onclick="maximizeChart('topErrorsGraph', 'Top 10 Errors (Frequency)')">Maximize</button>
                        <button class="action-btn" style="background-color: #27ae60; color: white;" onclick="downloadRawData()">Download Raw Data</button>
                    </div>
                </div>
                <div id="topErrorsGraph"></div>
            </div>

            <!-- 3b. Top Errors (Pie detection) -->
             <div class="col card">
                <div class="chart-header">
                    <div class="chart-title">Errors Distribution</div>
                    <div class="chart-actions">
                         <button class="reset-btn" id="btn-reset-errorPie" onclick="clearFilter('error')" style="display:none;">Clear Selection</button>
                        <button class="action-btn" onclick="maximizeChart('topErrorsPie', 'Errors Distribution')">Maximize</button>
                        <button class="action-btn" style="background-color: #27ae60; color: white;" onclick="downloadRawData()">Download Raw Data</button>
                    </div>
                </div>
                <div id="topErrorsPie"></div>
            </div>
        </div>
            
        <!-- 4. Result -->
        <div class="card">
            <div class="chart-header">
                <div class="chart-title">Error Hierarchy (Model &rarr; Test Item &rarr; Error)</div>
                <div class="chart-actions">
                    <button class="reset-btn" id="btn-reset-result" onclick="clearFilter('result')" style="display:none;">Clear Selection</button>
                    <button class="action-btn" onclick="maximizeChart('resultGraph', 'Error Hierarchy')">Maximize</button>
                    <button class="action-btn" style="background-color: #27ae60; color: white;" onclick="downloadRawData()">Download Raw Data</button>
                </div>
            </div>
            <div id="resultGraph"></div>
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
        // State for click-interactions
        let selectedClickFilters = {{
            date: null,
            model: null,
            testItem: null,
            error: null,
            result: null
        }};

        // Helper separator for IDs in Sunburst
        const sep = "^^";

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

        // Initialize listeners function
        function attachListeners() {{
            const ids = ['timelineGraph', 'testItemGraph', 'testItemPie', 'topErrorsGraph', 'topErrorsPie', 'resultGraph'];
            
            ids.forEach((id) => {{
                const el = document.getElementById(id);
                el.removeAllListeners && el.removeAllListeners('plotly_click');
                
                el.on('plotly_click', function(data){{
                    if(data.points.length > 0) {{
                        const pt = data.points[0];
                        let needsUpdate = false;

                        if (id === 'timelineGraph') {{
                            selectedClickFilters.date = pt.x;
                            needsUpdate = true;
                        }} 
                        else if (id === 'testItemGraph') {{
                            selectedClickFilters.testItem = pt.x;
                            needsUpdate = true;
                        }}
                        else if (id === 'testItemPie') {{
                            selectedClickFilters.testItem = pt.label;
                            needsUpdate = true;
                        }}
                        else if (id === 'topErrorsGraph') {{
                            selectedClickFilters.error = pt.y; 
                            needsUpdate = true;
                        }}
                        else if (id === 'topErrorsPie') {{
                            selectedClickFilters.error = pt.label; 
                            needsUpdate = true;
                        }}
                        else if (id === 'resultGraph') {{
                            // Sunburst Logic (Endogram)
                            // ID format: Model^^TestItem^^Error
                            const nodeId = pt.id; 
                            
                            // If root or weird state
                            if (!nodeId) return; 

                            // Reset everything first to apply strict hierarchy from this node
                            selectedClickFilters.model = null;
                            selectedClickFilters.testItem = null;
                            selectedClickFilters.error = null;

                            // Parse
                            const parts = nodeId.split(sep);
                            if (parts[0] !== "Total") {{
                                if (parts.length >= 1) selectedClickFilters.model = parts[0];
                                if (parts.length >= 2) selectedClickFilters.testItem = parts[1];
                                if (parts.length >= 3) selectedClickFilters.error = parts[2];
                                needsUpdate = true;
                            }}
                        }}

                        if (needsUpdate) updateDashboard();
                    }}
                }});
            }});
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
                // Prioritize error_message_nor as requested
                // Prioritize Analyzed_Error if it exists in the row, otherwise error_message_nor, otherwise Unknown.
                let rawError = row.Analyzed_Error || row.error_message_nor || "Unknown";
                
                // 1. Remove Prefix "YYYY-MM-DD HH:MM:SS | ERROR | "
                let cleanError = rawError.replace(/\\d{{4}}-\\d{{2}}-\\d{{2}} \\d{{2}}:\\d{{2}}:\\d{{2}} \\| ERROR \\| /, "");
                
                // Specific standardization for IPv4/IPv6 address error
                if (cleanError.includes("does not appear to be an IPv4 or IPv6 address")) {{
                    cleanError = "'Last login: DATE from XXX.XXX.XXX.XXXstart serial session -i XX -b X\\n\\n\\nip addr\\nWcsCli# start serial session -i XX -b X\\n' does not appear to be an IPv4 or IPv6 address";
                }} 
                // Specific standardization for "create account - fail"
                else if (cleanError.trim().endsWith("create account - fail")) {{
                    cleanError = "UXX create account - fail";
                }}
                // Specific standardization for "timed out. (connect timeout=30)'))"
                else if (cleanError.trim().endsWith("timed out. (connect timeout=30)'))")) {{
                    cleanError = "HTTPConnectionPool(host='XXX.XXX.XXX.{id}', port=5985): Max retries exceeded with url: /wsman (Caused by ConnectTimeoutError(<urllib3.connection.HTTPConnection object at XxXXXXXXXXXXXXX>, 'Connection to XXX.XXX.XXX.XXX timed out. (connect timeout=30)'))";
                }}
                // Specific standardization for "check BMC FW Version"
                else if (cleanError.startsWith("check BMC FW Version") && cleanError.includes("Failed to ping")) {{
                     cleanError = "check BMC FW Version, expected equal to C2195.BC.0406, actual: C2195.BC.0405 - Fail\\nFailed to ping 172.XXX.XXX.XXX, DUT is not reachable.";
                }}
                // Specific standardization for "Command [show manager relay -p"
                else if (cleanError.startsWith("Command [show manager relay -p")) {{
                     cleanError = "Command [show manager relay -p X] timeout.";
                }}
                // Specific standardization for "check DIMM Locator"
                else if (cleanError.startsWith("check DIMM Locator, expected equal to DIMM_")) {{
                     cleanError = "check DIMM Locator, expected equal to DIMM_XN, actual: DIMM_XN - Fail\\ncheck DIMM Quantity, expected equal to 12, actual: {{not equality}} - Fail";
                }}
                // Specific standardization for "Invalid SFCS stage"
                else if (cleanError.startsWith("Invalid SFCS stage, expected:")) {{
                    cleanError = "Invalid SFCS stage, expected: Zz, actual: Xx";
                }}
                // Specific standardization for "check sensor Fan_"
                else if (cleanError.startsWith("check sensor Fan_")) {{
                    cleanError = "check sensor Fan_Nx reading, expected equal to ok, actual: ns - Fail\\nL10 BMC SDR check fail";
                }}
                // Specific standardization for "didn't have device exist in OS"
                else if (cleanError.trim().endsWith("didn't have device exist in OS")) {{
                    cleanError = "This BDF XXXX:XX:XX.X didn't have device exist in OS";
                }}
                // Specific standardization for "check System SN"
                else if (cleanError.startsWith("check System SN, expected equal to")) {{
                    cleanError = "check System SN, expected equal to PXXXXXXXXXXXXXXX, actual: PYYYYYYYYYYYYYYY - Fail";
                }}
                // Specific standardization for "TOR switch"
                else if (cleanError.includes("expected equal to OK, actual: NOT - Fail") && cleanError.includes("TOR switch")) {{
                    cleanError = "check psuXpwr-511-ac-red, expected equal to OK, actual: NOT - Fail\\nTOR switch M1171500-001 (DATA_SW, UXX) - Fail";
                }}
                // Specific standardization for "Failed to process the command: ping -c"
                else if (cleanError.startsWith("Failed to process the command: ping -c")) {{
                    cleanError = "Failed to process the command: ping -c X -i X -W XX 172.XX.XX.XX";
                }}
                 // Specialized replacement for "check BMC FW Version" and "Command [set system bmc update -i"
                else if (cleanError.includes("check BMC FW Version") && cleanError.includes("Command [set system bmc update -i")) {{
                    cleanError = "check BMC FW Version, expected equal to C2195.BC.0406, actual: C2195.BC.0405 - Fail\\nCommand [set system bmc update -i X -f C2195.BC.0406.00.bin] timeout.";
                }}
                // Specialized replacement for "Failed to 'GetUSNGenealogyBasic'"
                else if (cleanError.startsWith("Failed to 'GetUSNGenealogyBasic' with {{'UnitSerialNumber': 'P")) {{
                    cleanError = "Failed to 'GetUSNGenealogyBasic' with {{'UnitSerialNumber': 'P{{id}}', 'StageCode': 'XX'}}";
                }}
                // Specialized replacement for "Failed to execute RM cmd: 'set system psu update -i"
                else if (cleanError.startsWith("Failed to execute RM cmd: 'set system psu update -i")) {{
                     cleanError = "Failed to execute RM cmd: 'set system psu update -i X -f File.hex -t X'";
                }}
                // Specialized replacement for "<pypsrp.powershell.PSDataStreams object at"
                else if (cleanError.startsWith("<pypsrp.powershell.PSDataStreams object at")) {{
                    cleanError = "<pypsrp.powershell.PSDataStreams object at 0x7XXXXXXXXXXXX>\\nrc=True, Failed to execute cmd 'cd ~\\.\\inband_tools\\MPF_latest; .\\s ;'";
                }}
                // Specialized replacement for "Get tpm ekcert from sfcs error"
                else if (cleanError.startsWith("Get tpm ekcert from sfcs error")) {{
                    cleanError = "Get tpm ekcert from sfcs error, error message: ['NoneType' object has no attribute 'get']\\nGet dcscmsn[M1304365002B5293XXXXXXX] ekcert failed in SFCS/MES.";
                }}
                // Specialized replacement for "Unable to send RAW command"
                else if (cleanError.includes("Unable to send RAW command (channel=0x0 netfn=0x34 lun=0x0 cmd=0x93 rsp=0xd5): Command not supported in present state")) {{
                    cleanError = "Failed to execute RM cmd: 'set system cmd -i XX -c raw 0x34 0x93 0x01 0x04', 'Completion Code: Failure', 'Status Description: Failed to run command ['raw', '0x{{id}}', '0x{{id}}', '0x{{id}}', '0x{{id}}'] with error: Unable to send RAW command (channel=0x0 netfn=0x34 lun=0x0 cmd=0x93 rsp=0xd5): Command not supported in present state'";
                }}
                else {{
                    // 2. Standardize Patterns
                    // Date: Fri Jan  9 09:24:01 2026
                    cleanError = cleanError.replace(/[A-Za-z]{{3}}\\s+[A-Za-z]{{3}}\\s+\\d+\\s+\\d{{2}}:\\d{{2}}:\\d{{2}}\\s+\\d{{4}}/g, "DATE");
                    // IP: 172.17.6.32
                    cleanError = cleanError.replace(/\\d{{1,3}}\\.\\d{{1,3}}\\.\\d{{1,3}}\\.\\d{{1,3}}/g, "XXX.XXX.XXX.XXX");
                    // Session ID: -i 35 -> -i XX
                    cleanError = cleanError.replace(/-i\\s+\\d+/g, "-i XX");
                    // Session ID: -b 1 -> -b X
                    cleanError = cleanError.replace(/-b\\s+\\d+/g, "-b X");
                }}

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
                
                // Hierarchical & Chart Filters
                if (selectedClickFilters.model && row.model !== selectedClickFilters.model) return false;
                if (selectedClickFilters.testItem && row.test_item !== selectedClickFilters.testItem) return false;
                if (selectedClickFilters.error && row.Analyzed_Error !== selectedClickFilters.error) return false;
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
            // Show ALL items (removed slice), sorted by count
            const sortedItems = Object.entries(itemCounts).sort((a,b)=>b[1]-a[1]); 

            // Calculate dynamic width for scrollbar
            const containerWidth = document.getElementById('testItemGraph').parentElement.offsetWidth;
            const itemWidth = 50; // pixels per bar
            const calcWidth = sortedItems.length * itemWidth;
            const finalWidth = Math.max(containerWidth, calcWidth);

            Plotly.newPlot('testItemGraph', [{{
                x: sortedItems.map(i => i[0]),
                y: sortedItems.map(i => i[1]),
                type: 'bar',
                marker: {{color: '#9b59b6'}}
            }}], {{
                margin: {{t: 10, b: 150}},
                xaxis: {{tickangle: -45, automargin: true}},
                width: finalWidth, 
                autosize: false
            }});

             // 2b. Test Item Distribution (Pie) - New
             Plotly.newPlot('testItemPie', [{{
                labels: sortedItems.map(e => e[0]),
                values: sortedItems.map(e => e[1]),
                type: 'pie',
                textinfo: 'label+percent+value',
                marker: {{colors: ['#8e44ad', '#9b59b6', '#a569bd', '#af7ac5', '#bb8fce', '#c39bd3', '#d2b4de', '#e8daef', '#f4ecf7', '#f5eef8']}}
            }}], {{
                margin: {{t: 10, l: 10, r: 10, b: 10}},
                showlegend: false,
                height: 500
            }});

            // Listener removed from here

            // 3. Top Errors (Bar) - Keep generic top 10
            const errorCounts = {{}};
            data.forEach(r => {{ errorCounts[r.Analyzed_Error] = (errorCounts[r.Analyzed_Error] || 0) + 1; }});
            // Sort all errors
            const allSortedErrors = Object.entries(errorCounts).sort((a,b)=>b[1]-a[1]);
            // Top 10 for Bar
            const top10Errors = allSortedErrors.slice(0, 10);

            Plotly.newPlot('topErrorsGraph', [{{
                x: top10Errors.map(e => e[1]),
                y: top10Errors.map(e => e[0]),
                type: 'bar',
                orientation: 'h',
                text: top10Errors.map(e => `${{e[1]}} (${{((e[1]/totalCount)*100).toFixed(1)}}%)`),
                textposition: 'auto',
                marker: {{color: '#e74c3c'}}
            }}], {{
                margin: {{t: 10, l: 400}},
                yaxis: {{autorange: 'reversed'}}
            }});
            
            // 3b. Errors Distribution (Pie) - Show ALL
            Plotly.newPlot('topErrorsPie', [{{
                labels: allSortedErrors.map(e => e[0]),
                values: allSortedErrors.map(e => e[1]),
                type: 'pie',
                textinfo: 'label+percent+value',
                marker: {{colors: ['#e74c3c', '#c0392b', '#d35400', '#e67e22', '#f39c12', '#f1c40f', '#2ecc71', '#27ae60', '#16a085', '#1abc9c']}}
            }}], {{
                margin: {{t: 10, l: 10, r: 10, b: 10}},
                showlegend: false,
                height: 500
            }});


            // Listener removed from here

            // 4. Error Hierarchy (Sunburst)
            // Hierarchy: Total -> Model -> Test Item -> Analyzed_Error
            const tree = {{}};
            let totalErrs = 0;

            data.forEach(r => {{
                const m = r.model || "Unknown";
                const t = r.test_item || "Unknown";
                const e = r.Analyzed_Error || "Unknown";
                
                if (!tree[m]) tree[m] = {{}};
                if (!tree[m][t]) tree[m][t] = {{}};
                if (!tree[m][t][e]) tree[m][t][e] = 0;
                tree[m][t][e]++;
                totalErrs++;
            }});

            const ids = ["Total"];
            const labels = ["Total Errors"];
            const parents = [""];
            const values = [totalErrs];
            const colors = ["#ffffff"]; // Root

            // Distinct Palette
            const palette = [
                '#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#46f0f0', '#f032e6', 
                '#bcf60c', '#fabebe', '#008080', '#e6beff', '#9a6324', '#fffac8', '#800000', '#aaffc3', 
                '#808000', '#ffd8b1', '#000075', '#808080', '#000000'
            ];
            let colorIdx = 0;

            // Helper separator for IDs
            const sep = "^^";

            Object.keys(tree).forEach(m => {{
                let mCount = 0;
                
                const mColor = palette[colorIdx % palette.length];
                colorIdx++;

                Object.keys(tree[m]).forEach(t => {{
                    let tCount = 0;
                    
                    const tColor = palette[colorIdx % palette.length];
                    colorIdx++;

                    Object.keys(tree[m][t]).forEach(e => {{
                        const eCount = tree[m][t][e];
                        tCount += eCount;
                        
                        // Add Error Node (Leaf)
                        const eId = `${{m}}${{sep}}${{t}}${{sep}}${{e}}`;
                        ids.push(eId);
                        labels.push(e); 
                        parents.push(`${{m}}${{sep}}${{t}}`);
                        values.push(eCount);
                        colors.push(tColor);
                    }});
                    mCount += tCount;
                    
                    // Add Test Item Node
                    const tId = `${{m}}${{sep}}${{t}}`;
                    ids.push(tId);
                    labels.push(t);
                    parents.push(m);
                    values.push(tCount);
                    colors.push(tColor);
                }});
                
                // Add Model Node
                ids.push(m);
                labels.push(m);
                parents.push("Total");
                values.push(mCount);
                colors.push(mColor);
            }});

            Plotly.newPlot('resultGraph', [{{
                ids: ids,
                labels: labels,
                parents: parents,
                values: values,
                type: 'sunburst',
                branchvalues: 'total',
                textinfo: 'label+value+percent entry',
                marker: {{
                    line: {{width: 2}},
                    colors: colors
                }}
            }}], {{
                margin: {{t: 0, l: 0, r: 0, b: 0}},
                height: 700 
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
            document.getElementById('btn-reset-errorPie').style.display = selectedClickFilters.error ? 'inline-block' : 'none'; 
            
            document.getElementById('btn-reset-testItem').style.display = selectedClickFilters.testItem ? 'inline-block' : 'none';
            document.getElementById('btn-reset-testItemPie').style.display = selectedClickFilters.testItem ? 'inline-block' : 'none'; 

            // Result button logic simplified
            document.getElementById('btn-reset-result').style.display = (selectedClickFilters.model || selectedClickFilters.testItem || selectedClickFilters.error) ? 'inline-block' : 'none';

            if(selectedClickFilters.date) parts.push(`Date: ${{selectedClickFilters.date}}`);
            
            // Hierarchical Display
            if(selectedClickFilters.model) parts.push(`Model: ${{selectedClickFilters.model}}`);
            if(selectedClickFilters.testItem) parts.push(`Test Item: ${{selectedClickFilters.testItem}}`);
            if(selectedClickFilters.error) parts.push(`Error: ${{selectedClickFilters.error}}`);
            
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
            selectedClickFilters = {{ date: null, model: null, testItem: null, error: null, result: null }};
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
