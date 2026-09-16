import sqlite3
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

def init_db():
    conn = sqlite3.connect('hospital_records.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chart_number TEXT NOT NULL,
            patient_name TEXT NOT NULL,
            category TEXT NOT NULL,
            content TEXT NOT NULL,
            status TEXT DEFAULT '대기',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>원내 업무 기록 시스템</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; margin: 20px; background-color: #f8f9fa; color: #333; }
        .container { max-width: 1000px; margin: 0 auto; background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h2 { margin-top: 0; color: #1a252f; border-bottom: 2px solid #34495e; padding-bottom: 10px; }
        .form-group { display: flex; gap: 10px; margin-bottom: 20px; }
        input, select, button { padding: 10px; border: 1px solid #ccc; border-radius: 4px; }
        input[type="text"] { flex: 1; }
        button { background-color: #2c3e50; color: white; border: none; cursor: pointer; font-weight: bold; }
        button:hover { background-color: #1a252f; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #f2f4f5; color: #2c3e50; }
        tr:nth-child(even) { background-color: #fafafa; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🏥 원내 업무 기록 시스템 (오프라인 전용)</h2>
        <form id="recordForm" class="form-group">
            <input type="text" id="chart_number" placeholder="차트번호" required style="flex: 0.5;">
            <input type="text" id="patient_name" placeholder="환자명" required style="flex: 0.5;">
            <select id="category">
                <option value="진료">진료</option>
                <option value="입원">입원</option>
                <option value="수술">수술</option>
                <option value="검사">검사</option>
            </select>
            <input type="text" id="content" placeholder="상세 업무 내용" required style="flex: 2;">
            <button type="submit">기록 저장</button>
        </form>

        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>차트번호</th>
                    <th>환자명</th>
                    <th>구분</th>
                    <th>내용</th>
                    <th>상태</th>
                    <th>일시</th>
                </tr>
            </thead>
            <tbody id="recordTable"></tbody>
        </table>
    </div>

    <script>
        async function loadRecords() {
            const res = await fetch('/api/records');
            const data = await res.json();
            const tbody = document.getElementById('recordTable');
            tbody.innerHTML = '';
            data.forEach(row => {
                tbody.innerHTML += `
                    <tr>
                        <td>${row.id}</td>
                        <td><b>${row.chart_number}</b></td>
                        <td>${row.patient_name}</td>
                        <td>${row.category}</td>
                        <td>${row.content}</td>
                        <td>${row.status}</td>
                        <td>${row.created_at}</td>
                    </tr>
                `;
            });
        }

        document.getElementById('recordForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const body = new URLSearchParams({
                chart_number: document.getElementById('chart_number').value,
                patient_name: document.getElementById('patient_name').value,
                category: document.getElementById('category').value,
                content: document.getElementById('content').value
            });
            await fetch('/api/records', { method: 'POST', body });
            document.getElementById('content').value = '';
            loadRecords();
        });

        loadRecords();
        setInterval(loadRecords, 3000);
    </script>
</body>
</html>
"""

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode('utf-8'))
        elif parsed.path == '/api/records':
            conn = sqlite3.connect('hospital_records.db')
            cursor = conn.cursor()
            cursor.execute('SELECT id, chart_number, patient_name, category, content, status, created_at FROM records ORDER BY id DESC')
            rows = cursor.fetchall()
            conn.close()
            data = [{'id': r[0], 'chart_number': r[1], 'patient_name': r[2], 'category': r[3], 'content': r[4], 'status': r[5], 'created_at': r[6]} for r in rows]
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_POST(self):
        if self.path == '/api/records':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = parse_qs(post_data)
            conn = sqlite3.connect('hospital_records.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO records (chart_number, patient_name, category, content) VALUES (?, ?, ?, ?)',
                           (params['chart_number'][0], params['patient_name'][0], params['category'][0], params['content'][0]))
            conn.commit()
            conn.close()
            self.send_response(200)
            self.end_headers()

def run():
    init_db()
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, RequestHandler)
    print("원내 서버 작동 중... http://[메인PC_IP]:8000")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
