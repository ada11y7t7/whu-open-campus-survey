"""
Survey Backend for WHU Open Campus Policy Research
===================================================
Receives survey responses from survey.html and stores them as JSON Lines.

Usage:
    pip install flask flask-cors
    python backend.py

    Server starts on http://localhost:5000
    Endpoints:
      POST /api/submit  — receive a survey response
      GET  /api/stats   — get response count
      GET  /api/export  — download all responses as JSON

Data is stored in survey_responses.jsonl (one JSON object per line).
"""

from flask import Flask, request, jsonify, Response, send_from_directory, send_file
import json
import os
from datetime import datetime

app = Flask(__name__)

# CORS is optional (only needed when frontend is on a different origin)
try:
    from flask_cors import CORS
    CORS(app)
except ImportError:
    pass

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'survey_responses.jsonl')


@app.route('/api/submit', methods=['POST'])
def submit():
    """Receive a survey response and append to JSONL file."""
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({'success': False, 'error': 'Invalid JSON'}), 400

    # Add server metadata
    data['received_at'] = datetime.now().isoformat()
    data['ip_hash'] = hash(str(request.remote_addr)) & 0x7fffffff  # anonymized

    # Validate basic structure
    if 'answers' not in data:
        return jsonify({'success': False, 'error': 'Missing "answers" field'}), 400

    # Append to JSONL file
    try:
        with open(DATA_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
    except IOError as e:
        return jsonify({'success': False, 'error': f'File write error: {e}'}), 500

    return jsonify({'success': True, 'message': 'Response recorded. Thank you!'})


@app.route('/api/stats', methods=['GET'])
def stats():
    """Return the total number of responses received."""
    count = 0
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            count = sum(1 for _ in f)
    return jsonify({'count': count, 'file': DATA_FILE})


@app.route('/api/export', methods=['GET'])
def export():
    """Download all responses as a single JSON array."""
    if not os.path.exists(DATA_FILE):
        return jsonify([])

    responses = []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    responses.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    return Response(
        json.dumps(responses, ensure_ascii=False, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': 'attachment; filename=survey_export.json'}
    )


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'time': datetime.now().isoformat()})


HERE = os.path.dirname(os.path.abspath(__file__))


@app.route('/')
def index():
    """Serve the survey HTML page."""
    return send_from_directory(HERE, 'survey.html')


@app.route('/qr')
def qr_page():
    """Show a page with the QR code + survey URL."""
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>扫码填写问卷</title>
<style>
  body {{ font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
         background: #f0f2f5; display: flex; justify-content: center; align-items: center;
         min-height: 100vh; margin: 0; }}
  .card {{ background: #fff; border-radius: 16px; padding: 40px 30px; text-align: center;
           box-shadow: 0 2px 12px rgba(0,0,0,.06); max-width: 360px; width: 90%; }}
  .card h2 {{ font-size: 20px; color: #1a1a2e; margin: 0 0 6px; }}
  .card p  {{ font-size: 14px; color: #999; margin: 0 0 24px; }}
  .card img {{ width: 220px; height: 220px; border: 1px solid #eee; border-radius: 12px; }}
  .card .url {{ margin-top: 18px; font-size: 15px; color: #1a5276; word-break: break-all; }}
  .card .hint {{ margin-top: 10px; font-size: 12px; color: #bbb; }}
</style>
</head>
<body>
<div class="card">
  <h2>武汉大学开放入校政策调研</h2>
  <p>微信 / 浏览器扫码填写</p>
  <img src="/survey_qr.png" alt="问卷二维码">
  <div class="url">{request.host_url.rstrip('/')}</div>
  <div class="hint">扫码或点击上方链接即可填写</div>
</div>
</body>
</html>'''


@app.route('/survey_qr.png')
def serve_qr():
    """Dynamically generate QR code pointing to the current server URL."""
    import io
    try:
        import qrcode
        url = request.host_url.rstrip('/')
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color='#1a1a2e', back_color='white')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return send_file(buf, mimetype='image/png')
    except ImportError:
        # Fallback to static file if qrcode not installed
        return send_from_directory(HERE, 'survey_qr.png')


if __name__ == '__main__':
    import sys
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    print('Survey backend starting...')
    print(f'   Data file: {DATA_FILE}')
    print(f'   Server:    http://localhost:{port}')
    print(f'   Stats:     http://localhost:{port}/api/stats')
    print(f'   Export:    http://localhost:{port}/api/export')
    print()
    app.run(host='0.0.0.0', port=port, debug=debug)
