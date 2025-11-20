import sqlite3
import json
import time
import base64
import ast
import shlex
import re
import urllib.parse
import sys
import os
import threading
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pydantic import BaseModel

from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from cryptography.fernet import Fernet

# GUI & Server
import webview
import uvicorn

# --- 1. 路径处理逻辑 (核心) ---

def resource_path(relative_path):
    """ 获取【静态资源】路径 (只读，打包在exe内部) """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_data_path(filename):
    """ 获取【用户数据】路径 (读写，保存在exe同级目录) """
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, filename)

# --- 2. 初始化配置 ---

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=resource_path("static")), name="static")

DB_NAME = get_data_path("toolbox.db")
# 生产环境请务必固定此 Key
SECRET_KEY = b'WFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFg=' 
cipher_suite = Fernet(SECRET_KEY)

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS todos 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT, status INTEGER, created_at TEXT, updated_at TEXT, completed_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS passwords 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, account TEXT, encrypted_pwd TEXT, url TEXT, tags TEXT)''')
    # 自动迁移字段
    for sql in [
        "ALTER TABLE todos ADD COLUMN updated_at TEXT",
        "ALTER TABLE todos ADD COLUMN completed_at TEXT",
        "ALTER TABLE passwords ADD COLUMN url TEXT",
        "ALTER TABLE passwords ADD COLUMN tags TEXT"
    ]:
        try: c.execute(sql)
        except: pass
    conn.commit()
    conn.close()

init_db()

# --- 3. Models ---
class TodoItem(BaseModel):
    content: str
    status: int = 0 

class TodoUpdateItem(BaseModel):
    content: Optional[str] = None
    status: Optional[int] = None

class PwdItem(BaseModel):
    title: str
    account: str
    password: str
    url: Optional[str] = ""
    tags: Optional[str] = ""

class ToolRequest(BaseModel):
    input_data: str
    mode: Optional[str] = None
    params: Optional[Dict[str, Any]] = None

# --- 4. 路由逻辑 ---

@app.get("/")
async def read_index():
    return FileResponse(resource_path('static/index.html'))

# Todo
@app.get("/api/todos")
def get_todos():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM todos ORDER BY status ASC, id DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/todos")
def add_todo(item: TodoItem):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO todos (content, status, created_at, updated_at) VALUES (?, ?, ?, ?)", (item.content, 0, now, now))
    conn.commit()
    conn.close()
    return {"msg": "ok"}

@app.put("/api/todos/{todo_id}")
def update_todo(todo_id: int, item: TodoUpdateItem):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    fields, values = ["updated_at = ?"], [now]
    if item.content is not None:
        fields.append("content = ?"); values.append(item.content)
    if item.status is not None:
        fields.append("status = ?"); values.append(item.status)
        fields.append("completed_at = ?"); values.append(now if item.status == 1 else None)
    values.append(todo_id)
    c.execute(f"UPDATE todos SET {', '.join(fields)} WHERE id = ?", tuple(values))
    conn.commit()
    conn.close()
    return {"msg": "ok"}

@app.delete("/api/todos/{todo_id}")
def delete_todo(todo_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    conn.commit()
    conn.close()
    return {"msg": "ok"}

# Passwords
@app.get("/api/passwords")
def get_passwords():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM passwords ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    res = []
    for row in rows:
        try: dec = cipher_suite.decrypt(row['encrypted_pwd'].encode()).decode()
        except: dec = "Error"
        res.append({**dict(row), "password": dec, "encrypted_pwd": ""})
    return res

@app.post("/api/passwords")
def add_password(item: PwdItem):
    enc = cipher_suite.encrypt(item.password.encode()).decode()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO passwords (title, account, encrypted_pwd, url, tags) VALUES (?, ?, ?, ?, ?)", 
              (item.title, item.account, enc, item.url, item.tags))
    conn.commit()
    conn.close()
    return {"msg": "ok"}

@app.delete("/api/passwords/{pwd_id}")
def delete_password(pwd_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM passwords WHERE id = ?", (pwd_id,))
    conn.commit()
    conn.close()
    return {"msg": "ok"}

# Tools
@app.post("/api/tools/curl2py")
def tool_curl2py(req: ToolRequest):
    cmd = req.input_data.strip()
    if not cmd.startswith('curl'): return {"error": "Need curl command"}
    try:
        # --- 修复位置：使用字符串拼接代替 f-string 以兼容低版本 Python ---
        def ansi_quote_replacer(m):
            # 将 \' 替换为 '，将 " 替换为 \"
            inner = m.group(1).replace(r"\'", "'").replace('"', r'\"')
            return '"' + inner + '"'
            
        cmd = re.sub(r"\$'((?:\\.|[^'])*)'", ansi_quote_replacer, cmd)
        # -----------------------------------------------------------

        args = shlex.split(cmd)
        url, method, headers, cookies, data = "", "GET", {}, {}, None
        i = 1
        while i < len(args):
            arg = args[i]
            if arg.startswith('http'): url = arg
            elif arg in ['-H', '--header'] and i+1 < len(args):
                if ':' in args[i+1]: k, v = args[i+1].split(':', 1); headers[k.strip()] = v.strip()
                i+=1
            elif arg in ['-b', '--cookie'] and i+1 < len(args):
                for p in args[i+1].split(';'): 
                    if '=' in p: k,v=p.split('=',1); cookies[k.strip()]=v.strip()
                i+=1
            elif arg in ['-d', '--data', '--data-raw'] and i+1 < len(args): data=args[i+1]; method="POST"; i+=1
            elif arg in ['-X', '--request'] and i+1 < len(args): method=args[i+1].upper(); i+=1
            i+=1
        
        code = "import requests\n\n"
        code += f"url = \"{url}\"\n\n"
        if headers: code += f"headers = {json.dumps(headers, indent=4)}\n\n"
        if cookies: code += f"cookies = {json.dumps(cookies, indent=4)}\n\n"
        if data:
            try: code += f"data = {json.dumps(json.loads(data), indent=4, ensure_ascii=False)}\n\n"
            except: code += f"data = '{data}'\n\n"
        
        al = ["url=url"]
        if headers: al.append("headers=headers")
        if cookies: al.append("cookies=cookies")
        if data: al.append("data=data" if method=='POST' else "params=data")
        
        code += f"response = requests.{method.lower()}({', '.join(al)})\n"
        code += "print(response.text)"
        return {"result": code}
    except Exception as e: return {"error": str(e)}

@app.post("/api/tools/json_format")
def tool_json_format(req: ToolRequest):
    try:
        # 兼容 Python Dict 写法
        text = req.input_data.strip()
        try: obj = json.loads(text)
        except: obj = ast.literal_eval(text)
        return {"result": json.dumps(obj, indent=4, ensure_ascii=False)}
    except Exception as e: return {"error": str(e)}

@app.post("/api/tools/file_hash")
async def tool_file_hash(file: UploadFile = File(...)):
    try:
        md5, sha1, sha256 = hashlib.md5(), hashlib.sha1(), hashlib.sha256()
        chunk_size = 65536 
        while True:
            chunk = await file.read(chunk_size)
            if not chunk: break
            md5.update(chunk); sha1.update(chunk); sha256.update(chunk)
        return {"result": {"MD5": md5.hexdigest(), "SHA1": sha1.hexdigest(), "SHA256": sha256.hexdigest()}}
    except Exception as e: return {"error": str(e)}

@app.post("/api/tools/time_calc")
def tool_time_calc(req: ToolRequest):
    try:
        base = req.params.get('base_time')
        dt = datetime.strptime(base, "%Y-%m-%d %H:%M:%S") if base else datetime.now()
        res = dt + timedelta(days=req.params.get('days', 0), hours=req.params.get('hours', 0))
        return {"result": res.strftime("%Y-%m-%d %H:%M:%S")}
    except: return {"error": "Error"}

@app.post("/api/tools/timestamp")
def tool_ts(req: ToolRequest):
    try:
        if req.mode == 'to_date':
            ts = float(req.input_data) if req.input_data else time.time()
            if req.params.get('unit')=='ms': ts/=1000
            return {"result": datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]}
        else:
            dt = datetime.strptime(req.input_data, "%Y-%m-%d %H:%M:%S") if req.input_data else datetime.now()
            ts = dt.timestamp()
            if req.params.get('unit')=='ms': ts*=1000
            return {"result": str(int(ts))}
    except: return {"error": "Error"}

@app.post("/api/tools/encoding")
def tool_enc(req: ToolRequest):
    s = req.input_data
    try:
        if req.mode=='base64_enc': res = base64.b64encode(s.encode()).decode()
        elif req.mode=='base64_dec': res = base64.b64decode(s).decode()
        elif req.mode=='url_enc': res = urllib.parse.quote(s)
        elif req.mode=='url_dec': res = urllib.parse.unquote(s)
        elif req.mode=='uni_enc': res = s.encode('unicode_escape').decode()
        elif req.mode=='uni_dec': res = s.encode('utf-8').decode('unicode_escape')
        return {"result": res}
    except Exception as e: return {"error": str(e)}

# --- 5. 启动 ---
def start_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")

if __name__ == "__main__":
    t = threading.Thread(target=start_server)
    t.daemon = True
    t.start()
    webview.create_window('Geek Toolbox Pro', 'http://127.0.0.1:8000', width=1280, height=850, resizable=True, text_select=True)
    webview.start()