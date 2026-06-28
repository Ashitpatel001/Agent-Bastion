from flask import Flask, request, render_template_string, send_file, abort
import time
import os

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Attack Simulation</title>
    <style>
        body { font-family: sans-serif; padding: 20px; }
    </style>
</head>
<body>
    <h1>Security Testbench</h1>
    <p>Directory Listing:</p>
    <ul>
        {% for file in files %}
        <li><a href="/test/{{ file }}">{{ file }}</a></li>
        {% endfor %}
    </ul>
</body>
</html>
"""

@app.route('/')
def home():
    files = [f for f in os.listdir('.') if f.endswith('.html')]
    return render_template_string(HTML_TEMPLATE, files=files)

@app.route('/test/<path:filename>')
def serve_file(filename):
    if not filename.endswith('.html') or '..' in filename or filename.startswith('/'):
        abort(400)
    
    if os.path.exists(filename):
        return send_file(filename)
    else:
        abort(404)

@app.route('/steal_creds', methods=['POST'])
def steal_creds():
    return "CREDENTIALS STOLEN: " + str(request.form)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
