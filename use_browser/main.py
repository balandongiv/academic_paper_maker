import os
from research_filter.agent_helper import combine_role_instruction
import pandas as pd
from PyPDF2 import PdfReader  # Make sure PyPDF2 is installed
from flask import Flask, render_template_string, request, redirect, url_for, send_file, session
from research_filter.config import AGENT_NAME_MAPPING
from research_filter.agent_helper import load_yaml
from research_filter.config import (
    YAML_PATH,
    placeholders
)

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Needed for session usage
pdf_folder=r'C:\Users\balan\OneDrive - ums.edu.my\research_related\0 eeg_trend_till24\eeg_review'
# fname = r'..\use_browser\shortdbs.xlsx'
fname=r'C:\Users\balan\IdeaProjects\academic_paper_maker\research_filter\database\eeg_review.xlsx'
df = pd.read_excel(fname)

# Create a new column combining the folder and file name
df['pdf_path'] = df['pdf_name'].apply(lambda x: f"{pdf_folder}\\{x}")

df = df[(df['ai_output'] == 'relevance') & (df['pdf_name'].notna()) & (df['pdf_name'] != '')]

current_index = 0
excel_file = "data.xlsx"
df.to_excel(excel_file, index=False)
default_shown_columns = ["year", "title", "bibtex"]
currently_editing_column = None

# Pagination for the row list
ROWS_PER_PAGE = 10

main_template = """
<!DOCTYPE html>
<html>
<head>
    <title>PDF Dashboard</title>
    <style>
        body {
            font-family: Arial, sans-serif;
        }
        .container {
            display: flex;
            flex-direction: row;
            height: 95vh;
        }

        /* Three-column layout */
        .column1, .column2, .column3 {
            border-right: 1px solid #ccc;
            padding: 20px;
            overflow-y: auto;
        }

        .column1 {
            width: 10%;
        }

        .column2 {
            width: 30%;
        }

        .column3 {
            width: 60%;
        }

        .navigation-buttons, .form-section {
            margin-bottom: 20px;
        }
        label {
            display: inline-block;
            width: 100px;
        }
        .pdf-viewer {
            width: 100%;
            height: 90%;
        }
        .row-data {
            margin-bottom: 20px;
        }
        .exit-button {
            margin-top: 20px;
            background-color: #d9534f;
            color: white;
            padding: 10px;
            border: none;
            cursor: pointer;
        }
        .exit-button:hover {
            background-color: #c9302c;
        }
        .hidden {
            display: none;
        }
        textarea {
            width: 100%;
        }
        .nav-container {
            display: flex;
            justify-content: space-between;
        }
        .top-nav {
            background: #f0f0f0;
            padding: 10px;
            margin-bottom: 20px;
        }
        .top-nav a {
            margin-right: 15px;
            text-decoration: none;
            color: blue;
        }

        /* Collapsible panel styles */
        .collapsible-button {
            background-color: #eee;
            color: #444;
            cursor: pointer;
            padding: 10px;
            width: 100%;
            border: none;
            text-align: left;
            font-size: 14px;
            margin-bottom: 10px;
        }

        .collapsible-button:hover {
            background-color: #ccc;
        }

        .collapsible-content {
            padding: 0 10px;
            display: none;
            overflow: auto;
            background-color: #f9f9f9;
            max-height: 300px;
            border: 1px solid #ccc;
        }

        .collapsible-content a {
            display: block;
            padding: 5px 0;
            color: blue;
            text-decoration: none;
        }

        .collapsible-content a:hover {
            text-decoration: underline;
        }

        .row-list-pagination {
            margin-top: 10px;
        }

        /* Show/hide column1 */
        .hide-column1 .column1 {
            display: none;
        }
        .hide-column1 .column2 {
            width: 60%; /* Adjust if needed */
        }
        .hide-column1 .column3 {
            width: 40%; /* Adjust if needed */
        }

    </style>
    <script>
        function toggleNewColumnInput() {
            var columnSelect = document.getElementById('column_to_update');
            var newColumnInput = document.getElementById('new_column_name_container');
            if (columnSelect && newColumnInput) {
                if (columnSelect.value === '__new_column__') {
                    newColumnInput.classList.remove('hidden');
                } else {
                    newColumnInput.classList.add('hidden');
                }
            }
        }

        function toggleAppendClear() {
            var modeSelect = document.getElementById('update_mode');
            var appendNote = document.getElementById('append_note');
            if (modeSelect && appendNote) {
                if (modeSelect.value === 'append') {
                    appendNote.textContent = "Appending will create a new line separated by newline on top of old record.";
                } else if (modeSelect.value === 'clear') {
                    appendNote.textContent = "Clearing will overwrite the old record.";
                } else {
                    appendNote.textContent = "";
                }
            }
        }

        // Save the scroll position to localStorage
        function saveScrollPosition() {
            localStorage.setItem("scrollTop", window.scrollY);
        }

        // Restore the scroll position after page load
        document.addEventListener("DOMContentLoaded", () => {
            const scrollTop = localStorage.getItem("scrollTop");
            if (scrollTop !== null) {
                window.scrollTo(0, parseInt(scrollTop, 10));
                localStorage.removeItem("scrollTop");
            }

            // Collapsible
            var content = document.getElementById("collapsibleContent");
            // We'll just let user toggle by a button
        });

        function editColumn(columnName) {
            if (columnName) {
                const url = `{{ url_for('edit_column') }}?column_name=${encodeURIComponent(columnName)}`;
                fetch(url)
                    .then(response => {
                        if (response.ok) {
                            window.location.reload();
                        } else {
                            console.error("Failed to update column.");
                        }
                    })
                    .catch(error => console.error("Error:", error));
            }
        }

        function copyToClipboard() {
            var text = document.getElementById('combined_string');
            if (text) {
                text.select();
                text.setSelectionRange(0, 99999);
                document.execCommand("copy");
            }
        }

        function toggleColumn1() {
            document.body.classList.toggle('hide-column1');
        }
    </script>

</head>
<body>
    <div class="top-nav">
        <a href="{{ url_for('index') }}">Home</a>
        <a href="{{ url_for('agentic_operation') }}">Agentic Operation</a>
        <button onclick="toggleColumn1()">Show/Hide Row List Column</button>
    </div>
    {{ content|safe }}
</body>
</html>
"""

index_template = """
<div class="container">
    <div class="column1">
        <button class="collapsible-button" onclick="var c=document.getElementById('collapsibleContent');c.style.display=(c.style.display==='block'?'none':'block')">Show/Hide Row List</button>
        <div class="collapsible-content" id="collapsibleContent" style="display:none;">
            {% for i in rows_to_display %}
                <a href="{{ url_for('go_to_row') }}?index={{ i }}&current_tab=index">{{ i }} - {{ df.iloc[i]['title'] if 'title' in df.columns else 'No Title' }}</a>
            {% endfor %}
            <div class="row-list-pagination">
                {% if row_list_page > 0 %}
                    <form action="{{ url_for('change_row_list_page') }}" method="post" style="display:inline;">
                        <input type="hidden" name="current_tab" value="index">
                        <input type="hidden" name="page_action" value="prev">
                        <button type="submit">Previous 10</button>
                    </form>
                {% endif %}
                {% if row_list_page < max_page %}
                    <form action="{{ url_for('change_row_list_page') }}" method="post" style="display:inline;">
                        <input type="hidden" name="current_tab" value="index">
                        <input type="hidden" name="page_action" value="next">
                        <button type="submit">Next 10</button>
                    </form>
                {% endif %}
            </div>
        </div>
    </div>
    <div class="column2">
        <h1>PDF Dashboard</h1>

        <div class="navigation-buttons">
            <form action="{{ url_for('prev_row') }}" method="post" style="display:inline;">
                <input type="hidden" name="current_tab" value="index">
                <button type="submit">Previous</button>
            </form>
            <form action="{{ url_for('next_row') }}" method="post" style="display:inline;">
                <input type="hidden" name="current_tab" value="index">
                <button type="submit">Next</button>
            </form>
        </div>

        <div class="form-section">
            <h3>Set Default Shown Columns</h3>
            <form action="{{ url_for('set_default_columns') }}" method="post">
                <label for="default_columns">Columns (comma-separated):</label>
                <input type="text" id="default_columns" name="default_columns" value="{{ default_columns_str }}">
                <button type="submit">Set</button>
            </form>
        </div>

        <div class="row-data">
            <h3>Current Row Data (Default Columns)</h3>
            {% for col in default_columns %}
                {% if col in row_data %}
                    <p><strong>{{ col }}:</strong> {{ row_data[col] }}</p>
                {% else %}
                    <p><strong>{{ col }}:</strong> N/A</p>
                {% endif %}
            {% endfor %}
        </div>

        <div class="form-section">
            <h3>Search Column</h3>
            <form action="{{ url_for('search_column') }}" method="post">
                <label for="column_name">Column Name:</label>
                <input type="text" id="column_name" name="column_name" required>
                <button type="submit">Search</button>
            </form>
            {% if search_column_result is defined %}
                <h4>Search Result</h4>
                {% if search_column_result is none %}
                    <p>Column not found.</p>
                {% else %}
                    <p><strong>{{ search_column_name }}:</strong> {{ search_column_result }}</p>
                {% endif %}
            {% endif %}
        </div>

        <div class="form-section">
            <h3>Update DataFrame</h3>
            <form action="{{ url_for('update_value') }}" method="post">
                <label for="column_to_update">Column:</label>
                <select id="column_to_update" name="column_to_update" onchange="toggleNewColumnInput()">
                    {% for col in default_columns %}
                        <option value="{{ col }}">{{ col }}</option>
                    {% endfor %}
                    <option value="__new_column__">Create New Column</option>
                </select><br><br>
                <div id="new_column_name_container" class="hidden">
                    <label for="new_column_name">New Column Name:</label>
                    <input type="text" id="new_column_name" name="new_column_name"><br><br>
                </div>
                <label for="new_value">New Value:</label>
                <input type="text" id="new_value" name="new_value" required><br><br>

                <label for="update_mode">Mode:</label>
                <select id="update_mode" name="update_mode" onchange="toggleAppendClear()">
                    <option value="append">Append</option>
                    <option value="clear">Clear</option>
                </select>
                <p id="append_note"></p>
                <button type="submit">Update</button>
            </form>
        </div>

        <div class="form-section">
            <h3>Edit Column Value (Current Row Only)</h3>
            <label for="edit_column_select">Select Column:</label>
            <select id="edit_column_select" name="column_name" onchange="editColumn(this.value)">
                {% for col in default_columns %}
                    <option value="{{ col }}">{{ col }}</option>
                {% endfor %}
            </select>
        </div>

        {% if edit_column_name is defined %}
        <div class="form-section">
            <h3>Editing Column: {{ edit_column_name }} (Row: {{ current_index }})</h3>
            <form action="{{ url_for('save_edited_column') }}" method="post">
                <input type="hidden" name="column_name" value="{{ edit_column_name }}">
                <textarea id="edit_column_textarea" name="edit_column_value" rows="5">{{ edit_column_value }}</textarea><br><br>
                <button type="submit">Save Column Changes</button>
            </form>
        </div>
        {% endif %}

        <div class="form-section">
            <h3>Export to Excel</h3>
            <form action="{{ url_for('export_to_excel') }}" method="post">
                <button type="submit">Export Now</button>
            </form>
        </div>

        <div class="navigation-buttons">
            <form action="{{ url_for('prev_row') }}" method="post" style="display:inline;">
                <input type="hidden" name="current_tab" value="index">
                <button type="submit">Previous</button>
            </form>
            <form action="{{ url_for('next_row') }}" method="post" style="display:inline;">
                <input type="hidden" name="current_tab" value="index">
                <button type="submit">Next</button>
            </form>
        </div>

        <form action="{{ url_for('exit_server') }}" method="post">
            <button type="submit" class="exit-button">Exit</button>
        </form>
    </div>
    <div class="column3">
        <h2>PDF Viewer</h2>
        {% if pdf_path %}
            <iframe class="pdf-viewer" src="{{ url_for('serve_pdf', pdf_path=pdf_path) }}"></iframe>
        {% else %}
            <p>No PDF available</p>
        {% endif %}
    </div>
</div>
"""

agentic_template = """
<div class="container">
    <div class="column1">
        <button class="collapsible-button" onclick="var c=document.getElementById('collapsibleContent');c.style.display=(c.style.display==='block'?'none':'block')">Show/Hide Row List</button>
        <div class="collapsible-content" id="collapsibleContent" style="display:none;">
            {% for i in rows_to_display %}
                <a href="{{ url_for('go_to_row') }}?index={{ i }}&current_tab=agentic_operation&activity_selected={{ activity_selected if activity_selected else '' }}">{{ i }} - {{ df.iloc[i]['title'] if 'title' in df.columns else 'No Title' }}</a>
            {% endfor %}
            <div class="row-list-pagination">
                {% if row_list_page > 0 %}
                    <form action="{{ url_for('change_row_list_page') }}" method="post" style="display:inline;">
                        <input type="hidden" name="current_tab" value="agentic_operation">
                        {% if activity_selected %}
                        <input type="hidden" name="activity_selected" value="{{ activity_selected }}">
                        {% endif %}
                        <input type="hidden" name="page_action" value="prev">
                        <button type="submit">Previous 10</button>
                    </form>
                {% endif %}
                {% if row_list_page < max_page %}
                    <form action="{{ url_for('change_row_list_page') }}" method="post" style="display:inline;">
                        <input type="hidden" name="current_tab" value="agentic_operation">
                        {% if activity_selected %}
                        <input type="hidden" name="activity_selected" value="{{ activity_selected }}">
                        {% endif %}
                        <input type="hidden" name="page_action" value="next">
                        <button type="submit">Next 10</button>
                    </form>
                {% endif %}
            </div>
        </div>
    </div>
    <div class="column2">
        <h1>Agentic Operation</h1>

        <div class="navigation-buttons">
            <form action="{{ url_for('prev_row') }}" method="post" style="display:inline;">
                <input type="hidden" name="current_tab" value="agentic_operation">
                {% if activity_selected %}
                <input type="hidden" name="activity_selected" value="{{ activity_selected }}">
                {% endif %}
                <button type="submit">Previous</button>
            </form>
            <form action="{{ url_for('next_row') }}" method="post" style="display:inline;">
                <input type="hidden" name="current_tab" value="agentic_operation">
                {% if activity_selected %}
                <input type="hidden" name="activity_selected" value="{{ activity_selected }}">
                {% endif %}
                <button type="submit">Next</button>
            </form>
        </div>

        <form action="{{ url_for('agentic_operation') }}" method="post">
            <label for="activity_selected">Select Operation:</label>
            <select name="activity_selected" id="activity_selected" required>
                <option value="">--Select--</option>
                <option value="analyse_pdf" {% if activity_selected == "analyse_pdf" %}selected{% endif %}>Analyse PDF</option>
                <option value="abstract_filtering" {% if activity_selected == "abstract_filtering" %}selected{% endif %}>Abstract Filtering</option>
            </select>
            <button type="submit">Run</button>
        </form>

        {% if combined_string %}
        <h3>Combined String</h3>
        <textarea id="combined_string" rows="10">{{ combined_string }}</textarea><br>
        <button type="button" onclick="copyToClipboard()">Copy</button>
        {% endif %}

        {% if combined_string %}
        <h3>Final Result (Paste Here)</h3>
        <form action="{{ url_for('agentic_operation_update') }}" method="post">
            <label for="json_input">JSON Input:</label>
            <textarea name="json_input" id="json_input" rows="5"></textarea><br><br>

            <label for="column_to_update">Column:</label>
            <select id="column_to_update" name="column_to_update" onchange="toggleNewColumnInput()">
                {% for col in default_columns %}
                    <option value="{{ col }}">{{ col }}</option>
                {% endfor %}
                <option value="__new_column__">Create New Column</option>
            </select><br><br>
            <div id="new_column_name_container" class="hidden">
                <label for="new_column_name">New Column Name:</label>
                <input type="text" id="new_column_name" name="new_column_name"><br><br>
            </div>

            <label for="update_mode">Mode:</label>
            <select id="update_mode" name="update_mode" onchange="toggleAppendClear()">
                <option value="append">Append</option>
                <option value="clear">Clear</option>
            </select>
            <p id="append_note"></p>
            <button type="submit">Update Data</button>
        </form>
        {% endif %}

        <div class="form-section">
            <h3>Export to Excel</h3>
            <form action="{{ url_for('export_to_excel') }}" method="post">
                <button type="submit">Export Now</button>
            </form>
        </div>

        <div class="navigation-buttons">
            <form action="{{ url_for('prev_row') }}" method="post" style="display:inline;">
                <input type="hidden" name="current_tab" value="agentic_operation">
                {% if activity_selected %}
                <input type="hidden" name="activity_selected" value="{{ activity_selected }}">
                {% endif %}
                <button type="submit">Previous</button>
            </form>
            <form action="{{ url_for('next_row') }}" method="post" style="display:inline;">
                <input type="hidden" name="current_tab" value="agentic_operation">
                {% if activity_selected %}
                <input type="hidden" name="activity_selected" value="{{ activity_selected }}">
                {% endif %}
                <button type="submit">Next</button>
            </form>
        </div>
    </div>
    <div class="column3">
        <h2>PDF Viewer</h2>
        {% if pdf_path %}
            <iframe class="pdf-viewer" src="{{ url_for('serve_pdf', pdf_path=pdf_path) }}"></iframe>
        {% else %}
            <p>No PDF available for this operation or none selected yet.</p>
        {% endif %}
    </div>
</div>
"""

def get_row_data(index):
    if 0 <= index < len(df):
        return df.iloc[index].to_dict()
    else:
        return {}

def safe_exit():
    os._exit(0)

def save_to_excel():
    df.to_excel(excel_file, index=False)

def get_current_edit_column_value():
    global currently_editing_column, current_index
    if currently_editing_column and currently_editing_column in df.columns:
        val = df.at[current_index, currently_editing_column]
        if pd.isna(val):
            val = ""
        return val
    return None

def get_row_list_page():
    return session.get('row_list_page', 0)

def set_row_list_page(page):
    session['row_list_page'] = page

@app.route("/", methods=["GET"])
def index():
    global current_index
    row_data = get_row_data(current_index)
    edit_column_name = None
    edit_column_value = None
    if currently_editing_column and currently_editing_column in df.columns:
        edit_column_name = currently_editing_column
        edit_column_value = get_current_edit_column_value()

    default_column = "year"
    row_list_page = get_row_list_page()
    start_idx = row_list_page * ROWS_PER_PAGE
    end_idx = start_idx + ROWS_PER_PAGE
    rows_to_display = range(start_idx, min(end_idx, len(df)))
    max_page = (len(df)-1)//ROWS_PER_PAGE

    content = render_template_string(
        index_template,
        row_data=row_data,
        pdf_path=row_data.get("pdf_path", None),
        df_columns=default_shown_columns,
        default_columns=default_shown_columns,
        default_columns_str=",".join(default_shown_columns),
        current_index=current_index,
        edit_column_name=edit_column_name,
        edit_column_value=edit_column_value,
        default_column=default_column,
        df=df,
        df_length=len(df),
        rows_to_display=rows_to_display,
        row_list_page=row_list_page,
        max_page=max_page
    )
    return render_template_string(main_template, content=content)

@app.route("/agentic_operation", methods=["GET", "POST"])
def agentic_operation():
    global current_index, df

    row_data = get_row_data(current_index)
    pdf_path = row_data.get("pdf_path", "")

    # Check if user selected/ran an activity
    activity_selected = request.form.get("activity_selected", None)
    if not activity_selected:
        activity_selected = session.get('activity_selected', None)

    combined_string = session.get('combined_string', "")

    if request.method == "POST" and request.form.get("activity_selected"):
        # User selected a new activity and clicked run
        config = load_yaml(YAML_PATH)
        pdf_text = ""
        if pdf_path and os.path.exists(pdf_path):
            try:
                reader = PdfReader(pdf_path)
                for page in reader.pages:
                    pdf_text += page.extract_text() + "\n"
            except Exception as e:
                pdf_text = f"Error reading PDF: {e}"

        if activity_selected == "analyse_pdf":
            agent_name = AGENT_NAME_MAPPING.get(activity_selected, AGENT_NAME_MAPPING["analyse_pdf"])
            system_prompt = combine_role_instruction(config, placeholders, agent_name)
            combined_string = f"{system_prompt}\n The PDF text is as follows:\n{pdf_text}"

        elif activity_selected == "abstract_filtering":
            agent_name = AGENT_NAME_MAPPING.get(activity_selected, AGENT_NAME_MAPPING["abstract_filtering"])
            system_prompt = combine_role_instruction(config, placeholders, agent_name)
            abstract_text = row_data.get("abstract", "")
            combined_string = f"{system_prompt}\n The abstract  is as follows:\n{abstract_text}"

        # Store them in session
        session['activity_selected'] = activity_selected
        session['combined_string'] = combined_string

    row_list_page = get_row_list_page()
    start_idx = row_list_page * ROWS_PER_PAGE
    end_idx = start_idx + ROWS_PER_PAGE
    rows_to_display = range(start_idx, min(end_idx, len(df)))
    max_page = (len(df)-1)//ROWS_PER_PAGE

    content = render_template_string(
        agentic_template,
        activity_selected=activity_selected,
        pdf_path=pdf_path,
        combined_string=combined_string,
        default_columns=default_shown_columns,
        df=df,
        df_length=len(df),
        rows_to_display=rows_to_display,
        row_list_page=row_list_page,
        max_page=max_page
    )
    return render_template_string(main_template, content=content)

@app.route("/change_row_list_page", methods=["POST"])
def change_row_list_page():
    page_action = request.form.get("page_action")
    current_tab = request.form.get("current_tab", "index")
    activity_selected = request.form.get("activity_selected", None)
    row_list_page = get_row_list_page()

    if page_action == "next":
        row_list_page += 1
    elif page_action == "prev" and row_list_page > 0:
        row_list_page -= 1

    set_row_list_page(row_list_page)

    if current_tab == "agentic_operation":
        if activity_selected:
            session['activity_selected'] = activity_selected
        return redirect(url_for('agentic_operation'))
    else:
        return redirect(url_for('index'))

@app.route("/set_default_columns", methods=["POST"])
def set_default_columns():
    global default_shown_columns
    cols_str = request.form.get("default_columns", "")
    cols = [c.strip() for c in cols_str.split(",") if c.strip()]
    if cols:
        default_shown_columns = cols
    return redirect(url_for('index'))

@app.route("/prev", methods=["POST"])
def prev_row():
    global current_index
    if current_index > 0:
        current_index -= 1
    current_tab = request.form.get("current_tab", "index")
    activity_selected = request.form.get("activity_selected", None)
    if current_tab == "agentic_operation":
        if activity_selected:
            session['activity_selected'] = activity_selected
        return redirect(url_for('agentic_operation'))
    else:
        return redirect(url_for('index'))

@app.route("/next", methods=["POST"])
def next_row():
    global current_index
    if current_index < len(df) - 1:
        current_index += 1
    current_tab = request.form.get("current_tab", "index")
    activity_selected = request.form.get("activity_selected", None)
    if current_tab == "agentic_operation":
        if activity_selected:
            session['activity_selected'] = activity_selected
        return redirect(url_for('agentic_operation'))
    else:
        return redirect(url_for('index'))

@app.route("/go_to_row", methods=["GET"])
def go_to_row():
    global current_index
    idx = request.args.get("index", None)
    current_tab = request.args.get("current_tab", "index")
    activity_selected = request.args.get("activity_selected", None)
    if idx is not None and idx.isdigit():
        new_index = int(idx)
        if 0 <= new_index < len(df):
            current_index = new_index
    if current_tab == "agentic_operation":
        if activity_selected:
            session['activity_selected'] = activity_selected
        return redirect(url_for('agentic_operation'))
    else:
        return redirect(url_for('index'))

@app.route("/search_column", methods=["POST"])
def search_column():
    global current_index
    column_name = request.form.get("column_name")
    row_data = get_row_data(current_index)
    if column_name in row_data:
        result = row_data[column_name]
    else:
        result = None

    edit_column_name = None
    edit_column_value = None
    if currently_editing_column and currently_editing_column in df.columns:
        edit_column_name = currently_editing_column
        edit_column_value = get_current_edit_column_value()

    row_list_page = get_row_list_page()
    start_idx = row_list_page * ROWS_PER_PAGE
    end_idx = start_idx + ROWS_PER_PAGE
    rows_to_display = range(start_idx, min(end_idx, len(df)))
    max_page = (len(df)-1)//ROWS_PER_PAGE

    content = render_template_string(
        index_template,
        row_data=row_data,
        pdf_path=row_data.get("pdf_path", None),
        df_columns=default_shown_columns,
        search_column_result=result,
        search_column_name=column_name,
        default_columns=default_shown_columns,
        default_columns_str=",".join(default_shown_columns),
        current_index=current_index,
        edit_column_name=edit_column_name,
        edit_column_value=edit_column_value,
        df=df,
        df_length=len(df),
        rows_to_display=rows_to_display,
        row_list_page=row_list_page,
        max_page=max_page
    )
    return render_template_string(main_template, content=content)

@app.route("/update_value", methods=["POST"])
def update_value():
    global current_index, df
    column_to_update = request.form.get("column_to_update")
    new_value = request.form.get("new_value")
    update_mode = request.form.get("update_mode", "append")

    if column_to_update == "__new_column__":
        new_col_name = request.form.get("new_column_name")
        if new_col_name and new_col_name.strip():
            column_to_update = new_col_name.strip()
            if column_to_update not in df.columns:
                df[column_to_update] = ""
        else:
            return redirect(url_for('index'))
    else:
        if column_to_update not in df.columns:
            df[column_to_update] = ""

    old_val = df.at[current_index, column_to_update]
    if pd.isna(old_val):
        old_val = ""
    if update_mode == "append":
        updated_val = (new_value + "\n" + old_val).strip()
    else:
        updated_val = new_value.strip()

    df.at[current_index, column_to_update] = updated_val
    save_to_excel()

    return redirect(url_for('index'))

@app.route("/edit_column", methods=["GET", "POST"])
def edit_column():
    global currently_editing_column
    column_name = request.args.get("column_name") or request.form.get("column_name")
    if column_name and column_name in df.columns:
        currently_editing_column = column_name
    return "", 204  # No content response

@app.route("/save_edited_column", methods=["POST"])
def save_edited_column():
    global df, current_index
    column_name = request.form.get("column_name")
    edited_text = request.form.get("edit_column_value", "")
    df.at[current_index, column_name] = edited_text.strip()
    save_to_excel()
    return redirect(url_for('index'))

@app.route("/export_to_excel", methods=["POST"])
def export_to_excel():
    save_to_excel()
    return "Data exported to Excel successfully!"

@app.route("/serve_pdf/<path:pdf_path>")
def serve_pdf(pdf_path):
    if os.path.exists(pdf_path):
        return send_file(pdf_path, mimetype='application/pdf')
    else:
        return "PDF not found", 404

@app.route("/exit", methods=["POST"])
def exit_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is not None:
        func()
    else:
        safe_exit()
    return "Server shutting down..."

@app.route("/agentic_operation_update", methods=["POST"])
def agentic_operation_update():
    global current_index, df
    json_input = request.form.get("json_input", "")
    column_to_update = request.form.get("column_to_update")
    update_mode = request.form.get("update_mode", "append")

    if column_to_update == "__new_column__":
        new_col_name = request.form.get("new_column_name")
        if new_col_name and new_col_name.strip():
            column_to_update = new_col_name.strip()
            if column_to_update not in df.columns:
                df[column_to_update] = ""
        else:
            return redirect(url_for('agentic_operation'))
    else:
        if column_to_update not in df.columns:
            df[column_to_update] = ""

    old_val = df.at[current_index, column_to_update]
    if pd.isna(old_val):
        old_val = ""
    if update_mode == "append":
        updated_val = (json_input + "\n" + old_val).strip()
    else:
        updated_val = json_input.strip()

    df.at[current_index, column_to_update] = updated_val
    save_to_excel()

    return redirect(url_for('agentic_operation'))

if __name__ == "__main__":
    app.run(debug=True)
