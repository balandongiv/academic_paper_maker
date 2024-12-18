import os
import json
import pandas as pd
from flask import Flask, render_template_string, request, redirect, url_for, send_file

app = Flask(__name__)

fname = r'..\use_browser\shortdbs.xlsx'
df = pd.read_excel(fname)

current_index = 0
excel_file = "data.xlsx"
df.to_excel(excel_file, index=False)
default_shown_columns = ["year", "title", "bibtex"]
currently_editing_column = None

template = """
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
        .left-panel {
            width: 40%;
            padding: 20px;
            border-right: 1px solid #ccc;
            overflow-y: auto;
        }
        .right-panel {
            width: 60%;
            padding: 20px;
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
    </style>
    <script>
        function toggleNewColumnInput() {
            var columnSelect = document.getElementById('column_to_update');
            var newColumnInput = document.getElementById('new_column_name_container');
            if (columnSelect.value === '__new_column__') {
                newColumnInput.classList.remove('hidden');
            } else {
                newColumnInput.classList.add('hidden');
            }
        }

        function toggleAppendClear() {
            var modeSelect = document.getElementById('update_mode');
            var appendNote = document.getElementById('append_note');
            if (modeSelect.value === 'append') {
                appendNote.textContent = "Appending will create a new line separated by newline on top of old record.";
            } else if (modeSelect.value === 'clear') {
                appendNote.textContent = "Clearing will overwrite the old record.";
            } else {
                appendNote.textContent = "";
            }
        }
    </script>
    
    <script>
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
    });
    </script>

</head>
<body>
    <div class="container">
        <div class="left-panel">
            <h1>PDF Dashboard</h1>

            <div class="navigation-buttons">
                <form action="{{ url_for('prev_row') }}" method="post" style="display:inline;">
                    <button type="submit">Previous</button>
                </form>
                <form action="{{ url_for('next_row') }}" method="post" style="display:inline;">
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
            
            <script>
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
            </script>


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
                    <button type="submit">Previous</button>
                </form>
                <form action="{{ url_for('next_row') }}" method="post" style="display:inline;">
                    <button type="submit">Next</button>
                </form>
            </div>

            <form action="{{ url_for('exit_server') }}" method="post">
                <button type="submit" class="exit-button">Exit</button>
            </form>
        </div>
        <div class="right-panel">
            <h2>PDF Viewer</h2>
            {% if pdf_path %}
                <iframe class="pdf-viewer" src="{{ url_for('serve_pdf', pdf_path=pdf_path) }}"></iframe>
            {% else %}
                <p>No PDF available</p>
            {% endif %}
        </div>
    </div>
</body>
</html>
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

@app.route("/", methods=["GET"])
def index():
    row_data = get_row_data(current_index)

    edit_column_name = None
    edit_column_value = None
    if currently_editing_column and currently_editing_column in df.columns:
        edit_column_name = currently_editing_column
        edit_column_value = get_current_edit_column_value()

    default_column = "year"
    return render_template_string(
        template,
        row_data=row_data,
        pdf_path=row_data.get("pdf_path", None),
        df_columns=default_shown_columns,
        default_columns=default_shown_columns,
        default_columns_str=",".join(default_shown_columns),
        current_index=current_index,
        edit_column_name=edit_column_name,
        edit_column_value=edit_column_value,
        default_column=default_column
    )

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
    return redirect(url_for('index'))

@app.route("/next", methods=["POST"])
def next_row():
    global current_index
    if current_index < len(df) - 1:
        current_index += 1
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

    return render_template_string(
        template,
        row_data=row_data,
        pdf_path=row_data.get("pdf_path", None),
        df_columns=default_shown_columns,
        search_column_result=result,
        search_column_name=column_name,
        default_columns=default_shown_columns,
        default_columns_str=",".join(default_shown_columns),
        current_index=current_index,
        edit_column_name=edit_column_name,
        edit_column_value=edit_column_value
    )

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
    return "", 204  # No content response for fetch call


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

if __name__ == "__main__":
    app.run(debug=True)
