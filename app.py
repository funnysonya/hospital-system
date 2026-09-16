import sqlite3
import json
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)
DB_NAME = "hospital.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # 탭/시트 구조 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            columns TEXT NOT NULL
        )
    ''')
    # 동적 레코드 저장 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sheet_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sheet_id INTEGER,
            data TEXT NOT NULL,
            FOREIGN KEY(sheet_id) REFERENCES sheets(id)
        )
    ''')
    
    # 기본 1번 탭(원격진료 리스트) 자동 생성
    cursor.execute("SELECT COUNT(*) FROM sheets")
    if cursor.fetchone()[0] == 0:
        default_cols = [
            {"name": "아이디", "type": "text"},
            {"name": "환자명", "type": "text"},
            {"name": "국가", "type": "dropdown", "options": ["한국", "미국", "중국", "일본", "기타"]},
            {"name": "성별", "type": "dropdown", "options": ["남", "여"]},
            {"name": "내원경로", "type": "dropdown", "options": ["영어홈페이지", "인터넷", "지인소개", "기타"]},
            {"name": "화상진료/2차소견", "type": "dropdown", "options": ["화상진료", "2차소견"]},
            {"name": "최초연락", "type": "text"},
            {"name": "자료취합", "type": "text"},
            {"name": "진료의뢰", "type": "text"},
            {"name": "진료결과", "type": "text"},
            {"name": "결과발송", "type": "text"},
            {"name": "주치의", "type": "dropdown", "options": ["김의사", "이의사", "박의사"]},
            {"name": "예상치료", "type": "text"},
            {"name": "비용안내(만원)", "type": "text"},
            {"name": "입원여부", "type": "dropdown", "options": ["Y", "N"]},
            {"name": "신환/재진", "type": "dropdown", "options": ["신환", "재진"]},
            {"name": "담당자", "type": "dropdown", "options": ["담당자A", "담당자B"]},
            {"name": "비고", "type": "text"}
        ]
        cursor.execute("INSERT INTO sheets (name, columns) VALUES (?, ?)", ("원격진료 리스트", json.dumps(default_cols, ensure_ascii=False)))
    conn.commit()
    conn.close()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>원내 업무 기록 시스템 (온프레미스)</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/tabulator-tables@5.5.0/dist/css/tabulator.min.css">
    <script src="https://cdn.jsdelivr.net/npm/tabulator-tables@5.5.0/dist/js/tabulator.min.js"></script>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f8f9fa; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .tabs { margin-bottom: 15px; display: flex; gap: 5px; border-bottom: 2px solid #dee2e6; padding-bottom: 5px; }
        .tab-btn { padding: 8px 16px; border: 1px solid #ccc; background: #e9ecef; cursor: pointer; border-radius: 4px 4px 0 0; font-weight: bold; }
        .tab-btn.active { background: #0d6efd; color: white; border-color: #0d6efd; }
        .controls { margin-bottom: 15px; display: flex; gap: 10px; }
        button { padding: 6px 12px; border: none; background: #0d6efd; color: white; border-radius: 4px; cursor: pointer; }
        button:hover { background: #0b5ed7; }
        button.secondary { background: #6c757d; }
        #example-table { background: white; border: 1px solid #ccc; }
        .modal { display: none; position: fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); justify-content:center; align-items:center; }
        .modal-content { background:white; padding:20px; border-radius:8px; width:400px; }
        .form-group { margin-bottom: 10px; }
        .form-group label { display:block; font-size:12px; font-weight:bold; margin-bottom:4px; }
        .form-group input { width:100%; padding:6px; box-sizing:border-box; }
    </style>
</head>
<body>
    <div class="header">
        <h2>🏥 원내 업무 기록 시스템</h2>
        <button class="secondary" onclick="openSheetModal()">+ 새 시트(탭) 추가</button>
    </div>

    <div class="tabs" id="tab-container"></div>

    <div class="controls">
        <button onclick="addRow()">+ 행 추가</button>
        <button class="secondary" onclick="openColumnModal()">⚙️ 현재 시트 컬럼 설정</button>
    </div>

    <div id="example-table"></div>

    <!-- 새 시트 추가 모달 -->
    <div class="modal" id="sheetModal">
        <div class="modal-content">
            <h3>새 시트(탭) 추가</h3>
            <div class="form-group">
                <label>시트 이름</label>
                <input type="text" id="newSheetName" placeholder="예: 수술일지">
            </div>
            <button onclick="createSheet()">생성</button>
            <button class="secondary" onclick="closeModal('sheetModal')">취소</button>
        </div>
    </div>

    <!-- 컬럼 설정 모달 -->
    <div class="modal" id="columnModal">
        <div class="modal-content">
            <h3>컬럼 추가</h3>
            <div class="form-group">
                <label>컬럼명</label>
                <input type="text" id="newColName">
            </div>
            <div class="form-group">
                <label>타입 (text 또는 dropdown)</label>
                <input type="text" id="newColType" value="text" placeholder="text 또는 dropdown">
            </div>
            <div class="form-group">
                <label>드롭다운 옵션 (쉼표로 구분)</label>
                <input type="text" id="newColOptions" placeholder="옵션1,옵션2,옵션3">
            </div>
            <button onclick="addColumn()">컬럼 추가</button>
            <button class="secondary" onclick="closeModal('columnModal')">취소</button>
        </div>
    </div>

    <script>
        let currentSheetId = null;
        let table = null;
        let sheetsData = [];

        async function loadSheets() {
            const res = await fetch('/api/sheets');
            sheetsData = await res.json();
            const container = document.getElementById('tab-container');
            container.innerHTML = '';
            
            sheetsData.forEach((s, idx) => {
                const btn = document.createElement('button');
                btn.className = `tab-btn ${currentSheetId === s.id || (!currentSheetId && idx === 0) ? 'active' : ''}`;
                btn.innerText = s.name;
                btn.onclick = () => selectSheet(s.id);
                container.appendChild(btn);
            });

            if (!currentSheetId && sheetsData.length > 0) {
                currentSheetId = sheetsData[0].id;
            }
            if (currentSheetId) loadTableData(currentSheetId);
        }

        async function selectSheet(id) {
            currentSheetId = id;
            loadSheets();
        }

        async function loadTableData(sheetId) {
            const sheet = sheetsData.find(s => s.id === sheetId);
            if (!sheet) return;

            const cols = JSON.parse(sheet.columns);
            const tabulatorCols = cols.map(c => {
                let colDef = { title: c.name, field: c.name, editor: "input" };
                if (c.type === "dropdown") {
                    colDef.editor = "list";
                    colDef.editorParams = { values: c.options || [] };
                }
                return colDef;
            });

            const res = await fetch(`/api/data/${sheetId}`);
            const rowData = await res.json();

            if (table) table.destroy();

            table = new Tabulator("#example-table", {
                data: rowData,
                layout: "fitColumns",
                reactiveData: true,
                columns: tabulatorCols,
                cellEdited: function(cell) {
                    saveAllData();
                }
            });
        }

        async function addRow() {
            if (!table) return;
            await table.addRow({});
            saveAllData();
        }

        async function saveAllData() {
            if (!currentSheetId || !table) return;
            const data = table.getData();
            await fetch(`/api/data/${currentSheetId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        }

        function openSheetModal() { document.getElementById('sheetModal').style.display = 'flex'; }
        function openColumnModal() { document.getElementById('columnModal').style.display = 'flex'; }
        function closeModal(id) { document.getElementById(id).style.display = 'none'; }

        async function createSheet() {
            const name = document.getElementById('newSheetName').value;
            if (!name) return;
            await fetch('/api/sheets', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, columns: [{ name: "아이디", type: "text" }] })
            });
            closeModal('sheetModal');
            loadSheets();
        }

        async function addColumn() {
            const name = document.getElementById('newColName').value;
            const type = document.getElementById('newColType').value;
            const optionsStr = document.getElementById('newColOptions').value;
            if (!name) return;

            const sheet = sheetsData.find(s => s.id === currentSheetId);
            const cols = JSON.parse(sheet.columns);
            const newCol = { name, type };
            if (type === 'dropdown') newCol.options = optionsStr.split(',').map(s => s.trim());
            cols.push(newCol);

            await fetch(`/api/sheets/${currentSheetId}/columns`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(cols)
            });
            closeModal('columnModal');
            loadSheets();
        }

        loadSheets();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/sheets', methods=['GET', 'POST'])
def handle_sheets():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if request.method == 'POST':
        data = request.json
        cursor.execute("INSERT INTO sheets (name, columns) VALUES (?, ?)", (data['name'], json.dumps(data['columns'], ensure_ascii=False)))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    else:
        cursor.execute("SELECT id, name, columns FROM sheets")
        rows = cursor.fetchall()
        conn.close()
        return jsonify([{"id": r[0], "name": r[1], "columns": r[2]} for r in rows])

@app.route('/api/sheets/<int:sheet_id>/columns', methods=['PUT'])
def update_columns(sheet_id):
    cols = request.json
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE sheets SET columns = ? WHERE id = ?", (json.dumps(cols, ensure_ascii=False), sheet_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/data/<int:sheet_id>', methods=['GET', 'POST'])
def handle_data(sheet_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if request.method == 'POST':
        rows = request.json
        cursor.execute("DELETE FROM sheet_data WHERE sheet_id = ?", (sheet_id,))
        for r in rows:
            cursor.execute("INSERT INTO sheet_data (sheet_id, data) VALUES (?, ?)", (sheet_id, json.dumps(r, ensure_ascii=False)))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    else:
        cursor.execute("SELECT data FROM sheet_data WHERE sheet_id = ?", (sheet_id,))
        rows = cursor.fetchall()
        conn.close()
        return jsonify([json.loads(r[0]) for r in rows])

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8000)
