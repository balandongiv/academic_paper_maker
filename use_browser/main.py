import os
import pandas as pd
from flask import Flask, request, render_template_string, send_file, redirect, url_for, jsonify
import signal

app = Flask(__name__)

# Sample DataFrame with PDF paths
dpath = r'C:\Users\balan\IdeaProjects\academic_paper_maker\ragpdf\data\test3.pdf'  # Adjust path as needed
data = {
    'ID': [1, 2],
    'Name': ['Alice', 'Bob'],
    'pdf_path': [dpath, dpath]  # Both rows use the same PDF
}
df = pd.DataFrame(data)
current_index = 0
annotations = {}  # Store annotations per row

# HTML Template with inline CSS/JS
TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>PDF Dashboard</title>
    <style>
        body { display: flex; font-family: Arial, sans-serif; }
        .left-panel { flex: 1; padding: 20px; }
        .right-panel { flex: 2; padding: 20px; }
        .controls { margin-top: 20px; }
        textarea { width: 100%; height: 100px; }
        button { margin: 5px; }
    </style>
</head>
<body>
    <div class="left-panel">
        <h2>Data Navigation</h2>
        <p><b>ID:</b> {{ row['ID'] }}</p>
        <p><b>Name:</b> {{ row['Name'] }}</p>
        <p><b>PDF Path:</b> {{ row['pdf_path'] }}</p>

        <form method="POST" action="/save_annotation">
            <label for="annotation">Annotations:</label><br>
            <textarea name="annotation" placeholder="Enter annotations here...">{{ annotation }}</textarea><br>
            <div class="controls">
                <button type="submit" name="action" value="previous">Previous</button>
                <button type="submit" name="action" value="next">Next</button>
            </div>
        </form>
        <form method="POST" action="/shutdown">
            <button type="submit">Exit</button>
        </form>
    </div>
    <div class="right-panel">
        <h2>PDF Viewer</h2>
        <iframe src="{{ url_for('serve_pdf', path=row['pdf_path']) }}" width="100%" height="600px"></iframe>
    </div>
</body>
</html>
"""

# Home route: Displays current row data and PDF
@app.route("/", methods=["GET", "POST"])
def home():
    global current_index
    if current_index < 0: current_index = 0
    if current_index >= len(df): current_index = len(df) - 1

    row = df.iloc[current_index]
    annotation = annotations.get(current_index, "")
    return render_template_string(TEMPLATE, row=row, annotation=annotation)

# Save annotations and handle navigation
@app.route("/save_annotation", methods=["POST"])
def save_annotation():
    global current_index
    annotations[current_index] = request.form.get("annotation", "")

    action = request.form.get("action")
    if action == "next":
        current_index += 1
    elif action == "previous":
        current_index -= 1
    return redirect(url_for("home"))

# Serve PDF file
@app.route("/serve_pdf/<path:path>")
def serve_pdf(path):
    return send_file(path)

# Shutdown route
@app.route("/shutdown", methods=["POST"])
def shutdown():
    os.kill(os.getpid(), signal.SIGTERM)
    return "Server shutting down..."

# API to update DataFrame via JSON
@app.route("/update_data", methods=["POST"])
def update_data():
    global df
    json_data = request.get_json()
    df = pd.DataFrame(json_data)
    return jsonify({"status": "Data updated successfully!"})

if __name__ == "__main__":
    app.run(debug=True)
