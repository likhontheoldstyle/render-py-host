from flask import Flask, request, jsonify, render_template_string
import subprocess
import tempfile
import os
import sys
import traceback

app = Flask(__name__)

MAX_CODE_LENGTH = 10000
TIMEOUT_SECONDS = 10

HTML = '''<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PyRunner — Python Code Executor</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg:       #0f1117;
    --surface:  #1a1d27;
    --border:   #2a2d3e;
    --accent:   #7c6af7;
    --accent2:  #5eead4;
    --text:     #e2e4ef;
    --muted:    #6b7280;
    --err:      #f87171;
    --ok:       #4ade80;
    --warn:     #fbbf24;
  }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Inter', sans-serif;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }

  /* ── Header ── */
  header {
    padding: 16px 24px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 12px;
    background: var(--surface);
  }
  .logo {
    display: flex;
    align-items: center;
    gap: 10px;
    text-decoration: none;
  }
  .logo-icon {
    width: 34px; height: 34px;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
  }
  .logo-text { font-size: 18px; font-weight: 600; color: var(--text); }
  .logo-text span { color: var(--accent); }
  .badge {
    margin-left: auto;
    background: rgba(124,106,247,0.15);
    color: var(--accent);
    border: 1px solid rgba(124,106,247,0.3);
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
  }

  /* ── Layout ── */
  .container {
    flex: 1;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0;
    height: calc(100vh - 65px);
  }

  .panel {
    display: flex;
    flex-direction: column;
    border-right: 1px solid var(--border);
    overflow: hidden;
  }
  .panel:last-child { border-right: none; }

  .panel-header {
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: var(--surface);
    flex-shrink: 0;
  }
  .panel-title {
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--muted);
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--accent); }
  .dot.green { background: var(--ok); }

  /* ── Tabs ── */
  .tabs {
    display: flex;
    gap: 4px;
    padding: 10px 16px;
    border-bottom: 1px solid var(--border);
    background: var(--bg);
    flex-shrink: 0;
  }
  .tab {
    padding: 6px 14px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    color: var(--muted);
    border: 1px solid transparent;
    transition: all 0.15s;
    background: none;
  }
  .tab:hover { color: var(--text); background: var(--surface); }
  .tab.active {
    background: rgba(124,106,247,0.15);
    color: var(--accent);
    border-color: rgba(124,106,247,0.3);
  }

  /* ── Editor ── */
  .tab-content { flex: 1; display: none; flex-direction: column; overflow: hidden; }
  .tab-content.active { display: flex; }

  textarea#code {
    flex: 1;
    background: var(--bg);
    color: #c9d1d9;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13.5px;
    line-height: 1.7;
    padding: 16px 20px;
    border: none;
    outline: none;
    resize: none;
    tab-size: 4;
  }
  textarea#code::placeholder { color: #3d4455; }

  /* ── File upload ── */
  .upload-zone {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 16px;
    padding: 32px;
    cursor: pointer;
  }
  .upload-icon {
    width: 64px; height: 64px;
    border-radius: 16px;
    background: rgba(124,106,247,0.1);
    border: 2px dashed rgba(124,106,247,0.4);
    display: flex; align-items: center; justify-content: center;
    font-size: 28px;
    transition: all 0.2s;
  }
  .upload-zone:hover .upload-icon {
    background: rgba(124,106,247,0.2);
    border-color: var(--accent);
  }
  .upload-label { font-size: 15px; color: var(--text); font-weight: 500; }
  .upload-sub { font-size: 12px; color: var(--muted); }
  #file-input { display: none; }
  .file-chosen {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 13px;
    color: var(--text);
    font-family: 'JetBrains Mono', monospace;
    display: none;
    align-items: center;
    gap: 8px;
    width: 100%;
    max-width: 320px;
  }
  .file-chosen.show { display: flex; }

  /* ── Actions ── */
  .actions {
    padding: 12px 16px;
    border-top: 1px solid var(--border);
    background: var(--surface);
    display: flex;
    gap: 8px;
    align-items: center;
    flex-shrink: 0;
  }
  .btn-run {
    background: linear-gradient(135deg, var(--accent), #6355e0);
    color: #fff;
    border: none;
    padding: 9px 22px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 7px;
    transition: opacity 0.15s, transform 0.1s;
    font-family: 'Inter', sans-serif;
  }
  .btn-run:hover { opacity: 0.9; transform: translateY(-1px); }
  .btn-run:active { transform: translateY(0); }
  .btn-run:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
  .btn-clear {
    background: none;
    border: 1px solid var(--border);
    color: var(--muted);
    padding: 9px 16px;
    border-radius: 8px;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.15s;
    font-family: 'Inter', sans-serif;
  }
  .btn-clear:hover { border-color: var(--err); color: var(--err); }
  .spinner {
    width: 14px; height: 14px;
    border: 2px solid rgba(255,255,255,0.3);
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
    display: none;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── Output ── */
  .output-panel {
    flex: 1;
    overflow-y: auto;
    padding: 16px 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    line-height: 1.7;
    background: var(--bg);
  }
  .output-panel::-webkit-scrollbar { width: 6px; }
  .output-panel::-webkit-scrollbar-track { background: transparent; }
  .output-panel::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

  .output-idle {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    gap: 12px;
    color: var(--muted);
  }
  .output-idle .idle-icon { font-size: 36px; opacity: 0.3; }
  .output-idle p { font-size: 13px; font-family: 'Inter', sans-serif; }

  .output-block { display: none; }
  .output-block.show { display: block; }

  .status-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 14px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border);
    font-family: 'Inter', sans-serif;
    font-size: 12px;
  }
  .status-pill {
    padding: 3px 10px;
    border-radius: 20px;
    font-weight: 600;
    font-size: 11px;
  }
  .status-pill.ok { background: rgba(74,222,128,0.15); color: var(--ok); }
  .status-pill.err { background: rgba(248,113,113,0.15); color: var(--err); }
  .status-pill.warn { background: rgba(251,191,36,0.15); color: var(--warn); }

  .time-info { color: var(--muted); margin-left: auto; }

  .stdout-block { color: #c9d1d9; white-space: pre-wrap; word-break: break-all; }
  .stderr-block { color: var(--err); white-space: pre-wrap; word-break: break-all; margin-top: 12px; }
  .err-label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--err);
    margin-bottom: 6px;
    font-family: 'Inter', sans-serif;
  }
  .empty-msg { color: var(--muted); font-style: italic; font-size: 12px; }

  /* ── Responsive ── */
  @media (max-width: 768px) {
    .container { grid-template-columns: 1fr; grid-template-rows: 50vh 50vh; }
    .panel { border-right: none; border-bottom: 1px solid var(--border); }
  }
</style>
</head>
<body>

<header>
  <a class="logo" href="#">
    <div class="logo-icon">🐍</div>
    <span class="logo-text">Py<span>Runner</span></span>
  </a>
  <div class="badge">Python 3 · Live</div>
</header>

<div class="container">

  <!-- LEFT: Editor / Upload -->
  <div class="panel">
    <div class="panel-header">
      <span class="panel-title"><span class="dot"></span> Input</span>
    </div>

    <div class="tabs">
      <button class="tab active" onclick="switchTab('editor')">✏️ Code Editor</button>
      <button class="tab" onclick="switchTab('upload')">📁 File Upload</button>
    </div>

    <!-- Editor Tab -->
    <div class="tab-content active" id="tab-editor">
      <textarea id="code" spellcheck="false" placeholder="# এখানে Python code লিখুন...
print('Hello from PyRunner!')

for i in range(5):
    print(f'Line {i+1}')"></textarea>
    </div>

    <!-- Upload Tab -->
    <div class="tab-content" id="tab-upload">
      <div class="upload-zone" onclick="document.getElementById('file-input').click()">
        <div class="upload-icon">📂</div>
        <div class="upload-label">.py ফাইল আপলোড করুন</div>
        <div class="upload-sub">ক্লিক করুন অথবা এখানে ফাইল ড্রপ করুন</div>
        <div class="file-chosen" id="file-chosen">
          <span>📄</span>
          <span id="file-name-text"></span>
        </div>
        <input type="file" id="file-input" accept=".py">
      </div>
    </div>

    <div class="actions">
      <button class="btn-run" id="run-btn" onclick="runCode()">
        <div class="spinner" id="spinner"></div>
        <span id="run-label">▶ Run</span>
      </button>
      <button class="btn-clear" onclick="clearAll()">Clear</button>
    </div>
  </div>

  <!-- RIGHT: Output -->
  <div class="panel">
    <div class="panel-header">
      <span class="panel-title"><span class="dot green"></span> Output</span>
      <button class="btn-clear" onclick="clearOutput()" style="padding:4px 10px;font-size:12px;">Clear</button>
    </div>

    <div class="output-panel" id="output-panel">
      <div class="output-idle" id="idle-msg">
        <div class="idle-icon">⚡</div>
        <p>Code লিখে Run করুন — output এখানে দেখাবে</p>
      </div>

      <div class="output-block" id="output-block">
        <div class="status-bar">
          <span class="status-pill" id="status-pill">OK</span>
          <span id="status-text" style="color:var(--muted)"></span>
          <span class="time-info" id="time-info"></span>
        </div>
        <div class="stdout-block" id="stdout"></div>
        <div class="stderr-block" id="stderr-wrap" style="display:none">
          <div class="err-label">⚠ Error / Stderr</div>
          <div id="stderr"></div>
        </div>
      </div>
    </div>
  </div>

</div>

<script>
let activeTab = 'editor';
let uploadedCode = '';

function switchTab(tab) {
  activeTab = tab;
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById('tab-' + tab).classList.add('active');
}

// File upload handling
const fileInput = document.getElementById('file-input');
fileInput.addEventListener('change', (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (ev) => {
    uploadedCode = ev.target.result;
    document.getElementById('file-name-text').textContent = file.name;
    document.getElementById('file-chosen').classList.add('show');
  };
  reader.readAsText(file);
});

// Drag & drop
const uploadZone = document.querySelector('.upload-zone');
uploadZone.addEventListener('dragover', (e) => { e.preventDefault(); uploadZone.style.background='rgba(124,106,247,0.1)'; });
uploadZone.addEventListener('dragleave', () => { uploadZone.style.background=''; });
uploadZone.addEventListener('drop', (e) => {
  e.preventDefault();
  uploadZone.style.background = '';
  const file = e.dataTransfer.files[0];
  if (file && file.name.endsWith('.py')) {
    const reader = new FileReader();
    reader.onload = (ev) => {
      uploadedCode = ev.target.result;
      document.getElementById('file-name-text').textContent = file.name;
      document.getElementById('file-chosen').classList.add('show');
    };
    reader.readAsText(file);
  }
});

async function runCode() {
  const code = activeTab === 'editor'
    ? document.getElementById('code').value.trim()
    : uploadedCode;

  if (!code) {
    showOutput('error', 'কোনো code নেই!', '', '');
    return;
  }

  // UI: loading state
  const btn = document.getElementById('run-btn');
  btn.disabled = true;
  document.getElementById('spinner').style.display = 'block';
  document.getElementById('run-label').textContent = 'Running...';

  const start = performance.now();

  try {
    const res = await fetch('/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code })
    });
    const data = await res.json();
    const elapsed = ((performance.now() - start) / 1000).toFixed(2);

    if (data.error && !data.stdout && !data.stderr) {
      showOutput('error', data.error, '', elapsed);
    } else {
      const status = data.returncode === 0 ? 'ok' : 'error';
      showOutput(status, status === 'ok' ? 'Executed successfully' : 'Exited with error', data, elapsed);
    }
  } catch (e) {
    showOutput('error', 'Server error: ' + e.message, '', '');
  } finally {
    btn.disabled = false;
    document.getElementById('spinner').style.display = 'none';
    document.getElementById('run-label').textContent = '▶ Run';
  }
}

function showOutput(status, msg, data, elapsed) {
  document.getElementById('idle-msg').style.display = 'none';
  const block = document.getElementById('output-block');
  block.classList.add('show');

  const pill = document.getElementById('status-pill');
  pill.textContent = status === 'ok' ? 'SUCCESS' : 'ERROR';
  pill.className = 'status-pill ' + (status === 'ok' ? 'ok' : 'err');
  document.getElementById('status-text').textContent = msg;
  document.getElementById('time-info').textContent = elapsed ? `⏱ ${elapsed}s` : '';

  const stdoutEl = document.getElementById('stdout');
  const stderrEl = document.getElementById('stderr');
  const stderrWrap = document.getElementById('stderr-wrap');

  if (data && (data.stdout !== undefined)) {
    stdoutEl.textContent = data.stdout || '';
    if (!data.stdout) stdoutEl.innerHTML = '<span class="empty-msg">(no output)</span>';
    if (data.stderr) {
      stderrEl.textContent = data.stderr;
      stderrWrap.style.display = 'block';
    } else {
      stderrWrap.style.display = 'none';
    }
  } else {
    stdoutEl.textContent = typeof data === 'string' ? data : msg;
    stderrWrap.style.display = 'none';
  }
}

function clearOutput() {
  document.getElementById('idle-msg').style.display = 'flex';
  document.getElementById('output-block').classList.remove('show');
}

function clearAll() {
  document.getElementById('code').value = '';
  uploadedCode = '';
  document.getElementById('file-chosen').classList.remove('show');
  clearOutput();
}

// Ctrl+Enter to run
document.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') runCode();
});

// Tab key in editor
document.getElementById('code').addEventListener('keydown', (e) => {
  if (e.key === 'Tab') {
    e.preventDefault();
    const s = e.target.selectionStart;
    const val = e.target.value;
    e.target.value = val.substring(0, s) + '    ' + val.substring(e.target.selectionEnd);
    e.target.selectionStart = e.target.selectionEnd = s + 4;
  }
});
</script>
</body>
</html>'''

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/run', methods=['POST'])
def run_code():
    data = request.get_json()
    if not data or 'code' not in data:
        return jsonify({'error': 'No code provided'}), 400

    code = data['code']
    if len(code) > MAX_CODE_LENGTH:
        return jsonify({'error': f'Code too long (max {MAX_CODE_LENGTH} chars)'}), 400

    # Write to temp file and run
    try:
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False, encoding='utf-8'
        ) as f:
            f.write(code)
            tmp_path = f.name

        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
        )
        return jsonify({
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        })

    except subprocess.TimeoutExpired:
        return jsonify({
            'stdout': '',
            'stderr': f'Timeout: code {TIMEOUT_SECONDS}s-এর বেশি সময় নিয়েছে।',
            'returncode': -1
        })
    except Exception as e:
        return jsonify({'error': str(e), 'trace': traceback.format_exc()})
    finally:
        try:
            os.unlink(tmp_path)
        except:
            pass

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
