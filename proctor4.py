import datetime
import sqlite3
from fastapi import FastAPI, Form, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sys
import os

# Use resend for email sending
# pip install resend
import resend

from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from starlette.responses import Response

app = FastAPI(
    title="Python Code Exam App",
    description="Register candidate, show multiple questions with expected output panel, code editor, run code output, send result to HR",
    version="0.3"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = "simple_exam_app_exam_candidate.db"

HR_EMAIL = "roopa.satish@timelineinvestments.in"

RESEND_API_KEY = "re_7RW6QVrT_FS96FnnKhHhVEdmQkNhqGHVd"

# Timer duration in seconds (2 hours)
EXAM_DURATION_SECONDS = 2 * 60 * 60

# ---- ADMIN PANEL SECTION ----
# Why you are getting 401 Unauthorized on /admin endpoint:
#
# The /admin endpoint is protected by HTTP Basic Auth using FastAPI's HTTPBasic dependency.
# If your request does not include the correct Authorization header with username and password,
# or if you are using the wrong credentials, FastAPI will return 401 Unauthorized.

# --- Admin Panel login and dashboard (fixed credential logic) ---
# Rewritten: More robust, modular, and slightly more secure admin panel authentication
from fastapi import Form, Request

ADMIN_USERS = {
    "tliadmin": "timeline2026",
    "hradmin": "2026"
}

def check_admin_credentials(username: str, password: str) -> bool:
    """
    Validate admin credentials. Username is case-insensitive, password is case-sensitive.
    Leading/trailing spaces are trimmed (except in password).
    """
    uname = username.strip()
    print(ADMIN_USERS.items())
    print(uname,password)
    # Print all values from ADMIN_USERS dict
    print("tliadmin:", ADMIN_USERS["tliadmin"])
    print("hradmin:", ADMIN_USERS["hradmin"])
    
    if uname.lower() == ADMIN_USERS["tliadmin"] and password == ADMIN_USERS["hradmin"]:
            print("valid data")
            return True
    else:
            print("not valid")
            return False

def render_admin_login_form(error_msg: str = "") -> HTMLResponse:
    style = """
    <style>
        body { font-family:Segoe UI,Arial,sans-serif; background:#f4f8fc; }
        h2 { color: #1c51a4;}
        .form-container {background: #ffffff; padding: 32px 26px; max-width: 350px; margin: 120px auto 0 auto; 
            border-radius: 12px; box-shadow: 0 2px 12px #b2b2ba;}
        input[type=text],input[type=password] {padding: 7px 9px; font-size:1em; width:100%; border:1px solid #bbbbce; border-radius:5px;}
        label {font-weight:500; display:block; margin-top:17px;}
        .btn {margin-top:21px; background:#1c51a4; color:#fff; font-weight:bold; border:none; border-radius:6px; padding:10px 21px; cursor:pointer;}
        .err { background: #fee0e0; color: #b12020; border: 1px solid #e59595; 
               padding: 14px; border-radius: 9px; margin-top: 19px; text-align:center; }
    </style>
    """
    errdiv = f'<div class="err"><b>{error_msg}</b></div>' if error_msg else ""
    html = style + f"""
    <div class="form-container">
        <form method="post">
            <h2>Admin Login</h2>
            <label for="username">Username</label>
            <input type="text" id="username" name="username" autocomplete="username" required>
            <label for="password">Password</label>
            <input type="password" id="password" name="password" autocomplete="current-password" required>
            <button type="submit" class="btn">Login</button>
        </form>
        {errdiv}
    </div>
    """
    return HTMLResponse(html)

@app.get("/admin", response_class=HTMLResponse)
def admin_panel_get():
    # Always show login form (no session management); FastAPI stateless by default
    return render_admin_login_form()

from fastapi import Form, Request
from fastapi.responses import HTMLResponse

@app.post("/admin", response_class=HTMLResponse)
async def admin_panel_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    delete_user_id: str = Form(None),
):

    # =======================
    # 🎨 MODERN DARK UI STYLE
    # =======================
    style = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    *{box-sizing:border-box;}

    body{
        margin:0;
        font-family:'Inter',sans-serif;
        background:linear-gradient(135deg,#0f172a,#0b1120);
        color:#e2e8f0;
    }

    .main-admin-container{
        max-width:1700px;
        margin:6px auto;
        padding:4px;
    }

    h2{
        text-align:center;
        font-size:34px;
        font-weight:700;
        margin-bottom:50px;
        background:linear-gradient(90deg,#38bdf8,#6366f1,#8b5cf6);
        -webkit-background-clip:text;
        -webkit-text-fill-color:transparent;
    }

    .table-container{
        overflow-x:auto;
        border-radius:18px;
        background:rgba(17,24,39,.75);
        backdrop-filter:blur(18px);
        box-shadow:0 30px 80px rgba(0,0,0,.65);
        border:1px solid rgba(255,255,255,.05);
    }

    .admin-table{
        width:100%;
        border-collapse:collapse;
        min-width:1200px;
    }

    .admin-table thead{
        background:rgba(30,41,59,.9);
    }

    .admin-table th{
        padding:18px 16px;
        font-size:12px;
        text-transform:uppercase;
        letter-spacing:1px;
        font-weight:600;
        color:#94a3b8;
        text-align:left;
    }

    .admin-table td{
        padding:18px 16px;
        font-size:14px;
        border-bottom:1px solid rgba(255,255,255,.04);
        vertical-align:top;
    }

    .admin-table tbody tr:hover{
        background:rgba(99,102,241,.08);
        transition:.25s ease;
    }

    .status-badge{
        padding:6px 12px;
        border-radius:30px;
        font-size:12px;
        font-weight:600;
        display:inline-block;
    }

    .completed-badge{
        background:rgba(34,197,94,.15);
        color:#22c55e;
    }

    .not-completed-badge{
        background:rgba(239,68,68,.15);
        color:#ef4444;
    }

    .btn,.view-btn{
        padding:8px 16px;
        border-radius:10px;
        border:none;
        cursor:pointer;
        font-size:13px;
        font-weight:600;
        transition:.25s ease;
    }

    .view-btn{
        background:linear-gradient(90deg,#2563eb,#4f46e5);
        color:white;
    }

    .view-btn:hover{
        transform:translateY(-3px);
        box-shadow:0 12px 24px rgba(79,70,229,.4);
    }

    .del-btn{
        background:linear-gradient(90deg,#dc2626,#b91c1c);
        color:white;
    }

    .del-btn:hover{
        transform:translateY(-3px);
        box-shadow:0 12px 24px rgba(220,38,38,.4);
    }

    .file-link{
        font-size:13px;
        color:#38bdf8;
        text-decoration:none;
    }

    .file-link:hover{
        text-decoration:underline;
    }

    .inner-attempt-table{
        width:100%;
        margin-top:10px;
        background:rgba(15,23,42,.6);
        border-radius:12px;
        overflow:hidden;
    }

    .inner-attempt-table th,
    .inner-attempt-table td{
        padding:10px;
        font-size:13px;
    }

    .view-modal{
        display:none;
        position:fixed;
        inset:0;
        background:rgba(0,0,0,.8);
        backdrop-filter:blur(8px);
        z-index:999;
        align-items:center;
        justify-content:center;
    }

    .view-modal.active{
        display:flex;
    }

    .modal-content{
        width:75%;
        max-height:85vh;
        overflow:auto;
        background:#0f172a;
        padding:35px;
        border-radius:20px;
        box-shadow:0 40px 80px rgba(0,0,0,.8);
        position:relative;
    }

    .modal-content pre{
        background:#020617;
        padding:20px;
        border-radius:12px;
        font-size:13px;
        overflow:auto;
    }

    .close-modal{
        position:absolute;
        right:20px;
        top:15px;
        font-size:24px;
        background:none;
        border:none;
        color:#ef4444;
        cursor:pointer;
    }
    </style>

    <script>
    function showModal(content,title){
        document.getElementById('modalTitle').innerText=title;
        document.getElementById('modalBody').textContent=content;
        document.getElementById('viewModal').classList.add('active');
    }
    function closeModal(){
        document.getElementById('viewModal').classList.remove('active');
    }
    document.addEventListener('keydown',function(e){
        if(e.key==='Escape') closeModal();
    });
    </script>
    """

    # =====================
    # 🔐 AUTH CHECK
    # =====================
    if not (username and password):
        return render_admin_login_form("Please enter both username and password.")

    if not check_admin_credentials(username, password):
        return render_admin_login_form("Not admin! Incorrect username or password")

    # =====================
    # 🗑 DELETE LOGIC
    # =====================
    if delete_user_id:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM candidate1 WHERE user_id=?", (delete_user_id,))
        cur.execute("DELETE FROM attempt WHERE user_id=?", (delete_user_id,))
        cur.execute("DELETE FROM exam_completion WHERE user_id=?", (delete_user_id,))
        cur.execute("DELETE FROM exam_timer WHERE user_id=?", (delete_user_id,))
        conn.commit()
        conn.close()

    # =====================
    # 📊 FETCH DATA
    # =====================
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM candidate1")
    candidates = {c["user_id"]: dict(c) for c in cur.fetchall()}

    cur.execute("""
        SELECT attempt.*, candidate1.name
        FROM attempt
        JOIN candidate1 ON candidate1.user_id = attempt.user_id
        ORDER BY attempt.user_id, attempt.question_idx
    """)
    all_attempts = cur.fetchall()

    attempts_by_user = {}
    for row in all_attempts:
        attempts_by_user.setdefault(row["user_id"], []).append(dict(row))

    cur.execute("SELECT * FROM exam_completion")
    completions = {c["user_id"]: dict(c) for c in cur.fetchall()}

    conn.close()

    import html as html_escape
    rows_html = ""

    for user_id, c in candidates.items():

        name = html_escape.escape(c.get("name") or "")
        email = html_escape.escape(c.get("email") or "")
        phone = html_escape.escape(c.get("phone") or "")
        position = html_escape.escape(c.get("position_applied") or "")
        reg_time = html_escape.escape(c.get("reg_time") or "")

        # Completion
        if user_id in completions:
            completed_html = "<span class='status-badge completed-badge'>Completed</span>"
        else:
            completed_html = "<span class='status-badge not-completed-badge'>Not Completed</span>"

        # Attempts
        import urllib.parse

        attempts = attempts_by_user.get(user_id, [])
        attempts_html = "<span>No submissions</span>"

        if attempts:

            # 🔥 Download All Button (per user)
            download_all_button = f"""
            <div style="margin-bottom:10px;">
                <a href="/admin/download/full?user_id={urllib.parse.quote(str(user_id))}"
                class="view-btn"
                style="text-decoration:none;display:inline-block;">
                ⬇ Download Full Report
                </a>
            </div>
            """

            attempts_html = download_all_button + "<table class='inner-attempt-table'><tr><th>Q</th><th>Actions</th></tr>"

            for att in attempts:
                q = att["question_idx"]
                code = att.get("code") or ""
                output = att.get("output") or ""

                attempts_html += f"""
                <tr>
                    <td>{q}</td>
                    <td>
                        <button class='view-btn'
                            onclick="this.nextElementSibling.style.display = (this.nextElementSibling.style.display === 'block') ? 'none' : 'block';">
                            Code
                        </button>
                        <div style='margin-top:4px;max-width:250px;font-family:monospace;font-size:0.88em;white-space:pre-wrap;background:#f7f7f7;border-radius:6px;padding:6px;color:#444;border:1px solid #e0e0e0; display:none;'>
                            <strong>Preview:</strong><br>
                            {html_escape.escape(str(code))[:160]}{'...' if code and len(str(code))>160 else ''}
                        </div>

                        <button class='view-btn'
                            onclick="this.nextElementSibling.style.display = (this.nextElementSibling.style.display === 'block') ? 'none' : 'block';">
                            Output
                        </button>
                        <div style='margin-top:4px;max-width:250px;font-family:monospace;font-size:0.88em;white-space:pre-wrap;background:#f7f7f7;border-radius:6px;padding:6px;color:#444;border:1px solid #e0e0e0; display:none;'>
                            <strong>Preview:</strong><br>
                            {html_escape.escape(str(output))[:160]}{'...' if output and len(str(output))>160 else ''}
                        </div>
                    </td>
                </tr>
                """

            attempts_html += "</table>"

        rows_html += f"""
        <tr>
            <td><strong>{user_id}</strong></td>
            <td>{name}</td>
            <td>{email}</td>
            <td>{phone}</td>
            <td>{position}</td>
            <td>{reg_time}</td>
            <td>{completed_html}</td>
            <td>{attempts_html}</td>
            <td>
                <form method="post">
                    <input type="hidden" name="username" value="{username}">
                    <input type="hidden" name="password" value="{password}">
                    <input type="hidden" name="delete_user_id" value="{user_id}">
                    <button type="submit" class="btn del-btn"
                    onclick="return confirm('Delete {name}?')">
                    Delete
                    </button>
                </form>
            </td>
        </tr>
        """

    html = f"""{style}
    <div class="main-admin-container">
        <h2 style="text-align:left; font-size:1.05em; font-weight:600; margin-left:0; margin-bottom:10px;">Admin Panel • Candidate Overview</h2>
        <div class="table-container">
            <table class="admin-table">
                <thead>
                    <tr>
                        <th>UserID</th>
                        <th>Name</th>
                        <th>Email</th>
                        <th>Phone</th>
                        <th>Position</th>
                        <th>Reg Time</th>
                        <th>Status</th>
                        <th>Attempts</th>
                        <th>Delete</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
    </div>

    <div id="viewModal" class="view-modal">
        <div class="modal-content">
            <button class="close-modal" onclick="closeModal()">×</button>
            <h3 id="modalTitle"></h3>
            <pre id="modalBody"></pre>
        </div>
    </div>
    """

    return HTMLResponse(html)


from fastapi.responses import StreamingResponse
import io

@app.get("/admin/download/full")
def download_full_report(user_id: str):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM candidate1 WHERE user_id=?", (user_id,))
    candidate = cur.fetchone()

    cur.execute("""
        SELECT * FROM attempt
        WHERE user_id=?
        ORDER BY question_idx
    """, (user_id,))

    attempts = [dict(row) for row in cur.fetchall()]   # ✅ FIX HERE

    conn.close()

    if not candidate:
        return HTMLResponse("User not found")

    content = []
    content.append("CANDIDATE FULL REPORT")
    content.append("="*60)
    content.append(f"User ID: {candidate['user_id']}")
    content.append(f"Name: {candidate['name']}")
    content.append(f"Email: {candidate['email']}")
    content.append("="*60)
    content.append("\n")

    for att in attempts:
        content.append(f"Question {att['question_idx']}")
        content.append("-"*40)
        content.append("CODE:")
        content.append(att.get("code") or "")
        content.append("\nOUTPUT:")
        content.append(att.get("output") or "")
        content.append("\n" + "="*60 + "\n")

    final_text = "\n".join(content)

    file_stream = io.BytesIO(final_text.encode("utf-8"))

    return StreamingResponse(
        file_stream,
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename=report_{user_id}.txt"
        },
    )
# Download endpoints for code/output
@app.get("/admin/download/code")
def admin_dl_code(user_id: int, qidx: int):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT code FROM attempt WHERE user_id=? AND question_idx=?", (user_id, qidx))
        row = cur.fetchone()
        conn.close()
        code_str = row["code"] if row else ""
    except Exception as e:
        code_str = f"Error: {e}"
    def iter_text():
        yield code_str or ""
    filename = f"code_user{user_id}_q{qidx}.txt"
    return StreamingResponse(iter_text(), media_type="text/plain", headers={
        "Content-Disposition": f"attachment; filename={filename}"
    })

@app.get("/admin/download/output")
def admin_dl_output(user_id: int, qidx: int):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT output FROM attempt WHERE user_id=? AND question_idx=?", (user_id, qidx))
        row = cur.fetchone()
        conn.close()
        output_str = row["output"] if row else ""
    except Exception as e:
        output_str = f"Error: {e}"
    def iter_text():
        yield output_str or ""
    filename = f"output_user{user_id}_q{qidx}.txt"
    return StreamingResponse(iter_text(), media_type="text/plain", headers={
        "Content-Disposition": f"attachment; filename={filename}"
    })

# ---- END ADMIN PANEL SECTION ----

def get_db():
    c = sqlite3.connect(DB_NAME)
    c.row_factory = sqlite3.Row
    return c

def ensure_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS candidate1 (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        phone TEXT,
        position_applied TEXT,
        dhan_client_id TEXT,
        dhan_access_token TEXT,
        reg_time TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS attempt (
        attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        question_idx INTEGER,
        code TEXT,
        output TEXT,
        created TEXT
    )""")
    # Add table to record exam completion
    cur.execute("""
    CREATE TABLE IF NOT EXISTS exam_completion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        completed_at TEXT
    )""")
    # Add table to store exam start for timers
    cur.execute("""
    CREATE TABLE IF NOT EXISTS exam_timer (
        user_id INTEGER PRIMARY KEY,
        start_time TEXT,
        UNIQUE(user_id)
    )
    """)
    conn.commit()
    conn.close()
ensure_db()

def get_exam_questions():
    return [
        # ... no change, keep as is ...
        {
            "question": (
                "TLI - Question 1: Trading Risk Summary as a Professional Python Function\n\n"
                "Objective:\n"
                "Write a reusable Python function that connects to the Dhan API ('dhanhq' library) with provided credentials, retrieves the account balance and open positions, and returns a summary of position risks as data (not just prints).\n\n"
                "Requirements:\n"
                "1. Define a function named `get_trading_risk_summary(client_id, access_token, from_date, to_date)`.\n"
                "2. Inside the function:\n"
                "   - Import the DhanHQ API client: `from dhanhq import dhanhq`\n"
                "   - Connect to Dhan: `dhan = dhanhq(client_id, access_token)`\n"
                "   - Fetch available balance using `dhan.get_fund_limits()` and extract the available balance field.\n"
                "   - Retrieve open positions with `dhan.get_positions()`.\n"
                "   - For each position, gather:\n"
                "     * Symbol (`position['tradingSymbol']`)\n"
                "     * Quantity (`position['netQty']`)\n"
                "     * Buy Average Price (`position['buyAvg']`)\n"
                "     * Security ID (`position['securityId']`)\n"
                "     * Last Traded Price (LTP):\n"
                "         - Use `dhan.intraday_minute_data(security_id, \"NSE_EQ\", \"EQUITY\", from_date, to_date)` and take the most recent closing price as LTP.\n"
                "     * Unrealized PnL: `(LTP - Buy Avg) * Quantity`\n"
                "     * Percentage Change: `((LTP - Buy Avg) / Buy Avg) * 100`\n"
                "   - Compose a summary dict per position with all relevant details.\n"
                "   - Calculate and include:\n"
                "     * The total/cumulative Unrealized PnL across all positions\n"
                "     * The available account balance\n"
                "3. The function should **return** a dictionary (or list of dicts) containing all position summaries and overall totals.\n\n"
                "Notes:\n"
                "- Do not print inside the function; return all data as structured output.\n"
                
            ),
            "expected_output":
"""Sample Return Value:
{
  "positions": [
    {
      "symbol": "INFY-EQ",
      "quantity": 100,
      "buy_avg": 1550.00,
      "ltp": 1570.00,
      "unrealized_pnl": 2000.0,
      "%_change": 1.29
    },
    {
      "symbol": "RELIANCE-EQ",
      "quantity": 30,
      "buy_avg": 2500.00,
      "ltp": 2490.00,
      "unrealized_pnl": -300.0,
      "%_change": -0.40
    }
  ],
  "available_balance": 100000.00,
  "total_unrealized_pnl": 1700.0
}
"""
        },
        {
            "question": (
                "TLI - Question 2: Professional Task: Compute EMA Signal for IDEA using Dhan API\n\n"
                "Write a function `generate_ema_signal(client_id: str, access_token: str, security_id: str = \"14366\")` that does the following:\n\n"
                "1. **Authenticate and Initialize Dhan API Client**\n"
                "   - Import and instantiate the DhanHQ client using the given credentials.\n"
                "     ```python\n"
                "     from dhanhq import dhanhq\n"
                "     dhan = dhanhq(client_id, access_token)\n"
                "     ```\n\n"
                "2. **Determine Date Range**\n"
                "   - Calculate the date range covering the last 3 trading days, formatted as `YYYY-MM-DD` strings for `from_date` and `to_date`.\n\n"
                "3. **Fetch Historical 5-minute OHLCV Data**\n"
                "   - Call the DhanHQ method to retrieve intraday 5-minute candle data for the given security and date range:\n"
                "     ```python\n"
                "     candles = dhan.intraday_minute_data(security_id, \"NSE_EQ\", \"EQUITY\", from_date, to_date)\n"
                "     ```\n"
                "   - Store the resulting data in a pandas DataFrame for further processing.\n\n"
                "4. **Calculate EMA Indicators**\n"
                "   - Extract the 'close' price series from the DataFrame.\n"
                "   - Calculate:\n"
                "     - 20-period Exponential Moving Average (EMA20)\n"
                "     - 50-period Exponential Moving Average (EMA50)\n"
                "   - These can be appended to the DataFrame as new columns:\n"
                "     ```python\n"
                "     df['EMA20'] = df['close'].ewm(span=20, adjust=False).mean()\n"
                "     df['EMA50'] = df['close'].ewm(span=50, adjust=False).mean()\n"
                "     ```\n\n"
                "5. **Output and Signal Generation**\n"
                "   - Print the resulting DataFrame (including at least the columns: open, high, low, close, volume, timestamp, EMA20, EMA50).\n"
                "   - Print the latest (most recent) close price, EMA20, and EMA50 values clearly.\n"
                "   - Add a column 'signal' to the DataFrame, where:\n"
                "     - signal = 'Bullish' if EMA20 > EMA50\n"
                "     - signal = 'Bearish' if EMA20 < EMA50\n"
                "   - Print the DataFrame including the 'signal' column.\n\n"
                "6. **Return Value**\n"
                "   - The function may return the DataFrame or a summary dict if needed, but printing is required as described.\n\n"
                "Please write a single self-contained function (with docstring) to accomplish this task, with well-commented and professional Python code. Do not print extraneous output."
            ),
            "expected_output": """A DataFrame should be printed similar to:

            # First five and last five rows (compact tabular format):
            # idx | open   high   low    volume     timestamp      EMA20      EMA50      signal
            # ------------------------------------------------------------------------------
            # 0   | 11.20 11.22  11.11  ...        1.771818e+09   11.150000  11.150000  Bearish
            # 1   | 11.16 11.19  11.10  ...        1.771818e+09   11.165750  11.165300  Bullish
            # 2   | 11.19 11.21  11.16  ...        1.771818e+09   11.178326  11.177332  Bullish
            # 3   | 11.18 11.20  11.17  ...        1.771818e+09   11.181696  11.180692  Bullish
            # 4   | 11.18 11.18  11.16  ...        1.771819e+09   11.176448  11.176216  Bullish
            # ...
            # 1120| 10.73 10.75  10.72  ...        1.772013e+09   10.734637  10.740533  Bearish
            # 1121| 10.73 10.74  10.72  ...        1.772013e+09   10.735148  10.740512  Bearish
            # 1122| 10.73 10.74  10.73  ...        1.772013e+09   10.734658  10.740100  Bearish
            # 1123| 10.74 10.75  10.73  ...        1.772013e+09   10.736119  10.740488  Bearish
            # 1124| 10.75 10.76  10.73  ...        1.772014e+09   10.737441  10.740861  Bearish
            #
            # (Only the first 5 and last 5 rows shown for brevity.)

(Format: each row contains open, high, low, volume, timestamp, EMA20, and EMA50. Number of rows and values will depend on actual data returned.)


(Values will vary depending on price series in the code.)
"""
        },
        {
            "question": (
                "Q3: Trade Dataset → Database → Realized PnL Calculation\n\n"
                "Objective:\n"
                "You are given a predefined set of trade records. Your task is to:\n"
                "1. Create a function that receives the dataset as input (use the below lines or pass as argument).\n"
                "2. Store the trades into a SQLite database table.\n"
                "3. Calculate the realized profit and loss (PnL) for each symbol as well as the total PnL.\n"
                "4. Print the results in the specified format.\n"
                "No external APIs allowed; use only Python stdlib and sqlite3.\n\n"
                "Dataset (as CSV lines):\n"
                "symbol,side,price,qty\n"
                "SBIN,BUY,500,10\n"
                "SBIN,SELL,520,10\n"
                "INFY,BUY,1500,5\n"
                "INFY,SELL,1480,5\n\n"
                "Instructions:\n"
                "- Write a complete, self-contained Python function (with docstring) called `calc_pnl_from_trades()` that does the following:\n"
                "   • Creates (in-memory or file) sqlite3 database and the required table structure.\n"
                "   • Inserts the dataset records into the table.\n"
                "   • Calculates realized PnL per symbol (difference between total sell and buy for each symbol; match buy/sell quantities as per rows given).\n"
                "   • Computes total PnL.\n"
                "   • Prints each symbol's PnL as `SBIN : +200` (see expected output) and the total as `TOTAL PnL : +100` (also include sign explicitly).\n"
                "   • Do NOT print extraneous information or explanations.\n\n"
                "Bonus: After the results, print the value of factorial(5) on a new line (for test purposes).\n"
                "Example expected output is provided below.\n"
                "Structure your answer as a single function with clear comments."
            ),
            "expected_output": """SBIN : +200
INFY : -100
TOTAL PnL : +100
120
"""
        },
        {
            "question": (
                "Q4: Risk-Based Market Order Placement Function Implementation\n\n"
                "Write a Python function risk_managed_market_order that:\n\n"
                "1. Accepts the following parameters: clientid, access_token.\n"
                "2. Initializes the dhan API client using: from dhanhq import dhanhq and dhan = dhanhq(clientid, access_token)\n"
                "3. Gets today's date in YYYY-MM-DD format.\n"
                "4. Prepares the data dictionary:\n"
                "   data = {\n"
                "       'security_id': '14366',\n"
                "       'exchange_segment': dhan.NSE_EQ,\n"
                "       'instrument_type': 'EQUITY',\n"
                "       'from_date': today,\n"
                "       'to_date': today\n"
                "   }\n"
                "5. Calls dhan.intraday_minute_data(data) to fetch intraday data and determine the last traded price (LTP).\n"
                "6. Attempts to place a BUY market order for quantity=1 with retry logic (total 2 attempts if the first fails):\n"
                "   dhan.place_order(\n"
                "       security_id='14366',\n"
                "       exchange_segment=dhan.NSE_EQ,\n"
                "       transaction_type=dhan.BUY,\n"
                "       quantity=1,\n"
                "       order_type=dhan.MARKET,\n"
                "       product_type=dhan.INTRA,\n"
                "       price=0\n"
                "   )\n"
                "   If order fails (exception or status not success), retry once more.\n"
                "7. Prints out the following exactly (populating with actual variable values):\n"
                "   Order Placed:\n"
                "   Symbol: <symbol>\n"
                "   LTP: <last_traded_price>\n"
                "   Quantity: 1\n"
                "   Order Status: <order_status>\n"
                "\n"
                "If real API access is not possible, provide a self-contained mock implementation for the dhan object with placeholder responses and comments showing where real calls would be used.\n"
                "\n"
                "Write only the function as described above, no extra text."
            ),
            "expected_output":
                "Order Placed:\n"
                "Symbol: <symbol>\n"
                "LTP: <last_traded_price>\n"
                "Quantity: 1\n"
                "Order Status: <order_status>\n"
        }
    ]

class RegisterModel1(BaseModel):
    name: str
    email: str
    phone: str
    position_applied: str
    dhan_client_id: str
    dhan_access_token: str

class AttemptModel(BaseModel):
    user_id: int
    code: str
    question_idx: int

def send_hr_email(user_id):
    """
    Compose a .txt report (UTF-8 safe, for Unicode characters like ₹)
    and email it to HR as an attachment using Resend.
    For unanswered questions, includes 'Not Attempted'.
    Candidate details are also included in a professional table format in the email body.
    """
    import tempfile
    import base64
    import os

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM candidate1 WHERE user_id=?", (user_id,))
    candidate = cur.fetchone()
    if not candidate:
        return
    cur.execute(
        "SELECT question_idx, code, output FROM attempt WHERE user_id=? ORDER BY question_idx", (user_id,)
    )
    attempts = cur.fetchall()
    questions = get_exam_questions()

    attempt_map = {a["question_idx"]: a for a in attempts}

    # Build TXT report for attachment
    txt_lines = []
    txt_lines.append("=== Candidate Exam Submission Report ===\n")
    txt_lines.append(f"Name: {candidate['name']}")
    txt_lines.append(f"Email: {candidate['email']}")
    txt_lines.append(f"Phone: {candidate['phone']}")
    txt_lines.append(f"Position Applied: {candidate['position_applied']}")
    txt_lines.append(f"Dhan Client ID: {candidate['dhan_client_id']}")
    txt_lines.append(f"Dhan Access Token: {candidate['dhan_access_token']}")
    txt_lines.append(f"Submitted at: {candidate['reg_time']}\n")
    for idx in range(len(questions)):
        txt_lines.append(f"\n--- Question {idx+1} ---")
        txt_lines.append(f"Question: {questions[idx]['question']}")
        txt_lines.append(f"Expected Output:\n{questions[idx]['expected_output']}")
        if idx in attempt_map:
            attempt = attempt_map[idx]
            txt_lines.append("Candidate Code:\n" + (attempt["code"] or ""))
            txt_lines.append("Output:\n" + (attempt["output"] or ""))
        else:
            txt_lines.append("Candidate Code:\n[NOT ATTEMPTED]")
            txt_lines.append("Output:\n[NOT ATTEMPTED]")
        txt_lines.append("-" * 36)
    txt_content = "\n".join(txt_lines)

    # Save to a temporary file using UTF-8 encoding
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".txt", encoding="utf-8") as tf:
        tf.write(txt_content)
        tf.flush()
        temp_txt_path = tf.name

    # Compose nice HTML table for candidate details
    candidate_table = f"""
        <table border="1" cellpadding="6" style="border-collapse: collapse; font-family: Arial; font-size: 15px; min-width: 360px;">
            <tr style="background-color:#f1f5f9;">
                <th align="left">Field</th>
                <th align="left">Value</th>
            </tr>
            <tr><td>Name</td><td>{candidate['name']}</td></tr>
            <tr><td>Email</td><td>{candidate['email']}</td></tr>
            <tr><td>Phone</td><td>{candidate['phone']}</td></tr>
            <tr><td>Position Applied</td><td>{candidate['position_applied']}</td></tr>
            <tr><td>Dhan Client ID</td><td>{candidate['dhan_client_id']}</td></tr>
            <tr><td>Dhan Access Token</td><td>{candidate['dhan_access_token']}</td></tr>
            <tr><td>Submitted at</td><td>{candidate['reg_time']}</td></tr>
        </table>
        <br>
    """

    # Build HTML report for the answer section (optional, can expand if needed)
    question_lines = []
    for idx in range(len(questions)):
        question_html = f"""
        <div style="margin-bottom:20px;">
            #<b>Question {idx+1}:</b> <span>{questions[idx]['question']}</span><br>
            <i>Expected Output:</i>
            <pre style="margin:4px 0 6px 0; background:#f9f9fe;padding:6px 10px;border-radius:4px;font-size:14px;">{questions[idx]['expected_output']}</pre>
        """
        if idx in attempt_map:
            attempt = attempt_map[idx]
            code_disp = (attempt["code"] or "").replace('<', '&lt;').replace('>', '&gt;')
            output_disp = (attempt["output"] or "").replace('<', '&lt;').replace('>', '&gt;')
            question_html += f"""
            <b>Candidate Code:</b>
            <pre style="margin:4px 0 6px 0;background:#f6faef;padding:6px 10px;border-radius:4px;font-size:14px;">{code_disp}</pre>
            <b>Output:</b>
            <pre style="margin:4px 0 6px 0;background:#eef8fa;padding:6px 10px;border-radius:4px;font-size:14px;">{output_disp}</pre>
            """
        else:
            question_html += f"""
            <b>Candidate Code:</b>
            <pre style="margin:4px 0 6px 0;background:#f6faef;padding:6px 10px;border-radius:4px;font-size:14px;">[NOT ATTEMPTED]</pre>
            <b>Output:</b>
            <pre style="margin:4px 0 6px 0;background:#eef8fa;padding:6px 10px;border-radius:4px;font-size:14px;">[NOT ATTEMPTED]</pre>
            """
        question_html += "<hr style='border:0;border-top:1px solid #e6ecf4;margin:6px 0 0 0;'>"
        question_lines.append(question_html)
    questions_html = "\n".join(question_lines)

    try:
        resend.api_key = "re_mPbaRVm3_LULoodCqDGJAm8PLCizccdE8"#"re_hW5ToeJj_KzXHNfzwsgFVZMZ4f5EYy8NR"
        with open(temp_txt_path, "rb") as f:
            file_bytes = f.read()
        file_bytes_b64 = base64.b64encode(file_bytes).decode("utf-8")
        file_payload = {
            "content": file_bytes_b64,
            "filename": f"{candidate['name'].replace(' ', '_')}_exam_report.txt",
            "type": "text/plain"
        }

        # Compose the HTML body
        html_body = f"""
            <div style="font-family: Arial,sans-serif; font-size:16px; line-height:1.62; color:#222;">
                <p>Dear HR Team,</p>
                <p>
                Please find below the detailed candidate information and attached the answer report.
                </p>
                <p>
                <b>Candidate Details:</b>
                <br>
                {candidate_table}
                </p>
                
                Regards,<br>
                Python Exam System
                </p>
            </div>
        """

        text_body = (
            f"Dear HR Team,\n\n"
            f"Please find attached the detailed submission report for candidate: {candidate['name']}.\n"
            "Refer to the attachment for full details of their answers.\n\n"
            f"Candidate Details:\n"
            f"Name: {candidate['name']}\n"
            f"Email: {candidate['email']}\n"
            f"Phone: {candidate['phone']}\n"
            f"Position Applied: {candidate['position_applied']}\n"
            f"Dhan Client ID: {candidate['dhan_client_id']}\n"
            f"Dhan Access Token: {candidate['dhan_access_token']}\n"
            f"Submitted at: {candidate['reg_time']}\n\n"
            "Regards,\nExam System"
        )

        resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": ["tliaravind@gmail.com"],#["roopamugappa@gmail.com"],
            "subject": f"Python Exam Submission: {candidate['name']}",
            "text": text_body,
            "html": html_body,
            "attachments": [file_payload]
        })
    except Exception as e:
        print(f"Error sending email via resend: {e}")
    finally:
        try:
            os.remove(temp_txt_path)
        except Exception:
            pass

@app.get("/", response_class=HTMLResponse)
def home():
    tl_words = [
        "Time", "Line", "Investments", "Pvt", "Ltd"
    ]
    header_html = '<div style="text-align:center;font-family:sans-serif;"><span style="font-size:2.1em;font-weight:bold;">'
    for word in tl_words:
        header_html += f'<span style="color: red;">{word[0]}</span><span style="color: black;">{word[1:]}</span> '
    header_html += '</span></div>'
    sub_header_html = '<div style="text-align:center;margin-bottom:23px;"><span style="font-size:1.25em;color:#333;font-weight:500;letter-spacing:0.03em;">Candidate Selection Process</span></div>'

    return f"""
    <html style="height: 100%;">
      <head>
        <title>Register for Python Exam</title>
        <style>
          html, body {{
            height: 100%;
            margin: 0;
            padding: 0;
            min-height: 100vh;
            width: 100vw;
          }}
          body {{
            font-family: sans-serif;
            width: 100vw;
            height: 100vh;
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            background: #f9fbfd;
          }}
          .register-panel {{
            box-shadow: 0 1px 5px #e0e0e8;
            background: #fff;
            border-radius: 10px;
            padding: 36px 45px;
            min-width: 320px;
            max-width: 98vw;
            width: 420px;
            margin: 0;
          }}
          @media (max-width: 500px) {{
            .register-panel {{
              padding: 18px 2vw;
              width: 98vw;
            }}
          }}
        </style>
      </head>
      <body>
        <div class="register-panel">
          {header_html}
          {sub_header_html}
          <form action='/register' method='post'>
            <label>Name:<br>
                <input style="width:95%;font-size:1.1em;" type='text' name='name' required>
            </label><br><br>
            <label>Email:<br>
                <input style="width:95%;font-size:1.1em;" type='email' name='email' required>
            </label><br><br>
            <label>Phone Number:<br>
                <input style="width:95%;font-size:1.1em;" type='text' name='phone' pattern="[\d ]{{7,}}" required>
            </label><br><br>
            <label>Position to Apply:<br>
                <input style="width:95%;font-size:1.1em;" type='text' name='position_applied' required>
            </label><br><br>
            <label>Dhan Client ID (provided by HR):<br>
                <input style="width:95%;font-size:1.1em;" type='text' name='dhan_client_id' required>
            </label><br><br>
            <label>Dhan Access Token (provided by HR):<br>
                <input style="width:95%;font-size:1.1em;" type='text' name='dhan_access_token' required>
            </label><br><br>
            <input type='submit' value='Register' style="width:100%;font-size:1.15em;padding:12px 0;background:#1560bd;color:#fff;border:none;border-radius:5px;">
          </form>
        </div>
      </body>
    </html>
    """

@app.post("/register", response_class=HTMLResponse)
async def register(
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    position_applied: str = Form(...),
    dhan_client_id: str = Form(...),
    dhan_access_token: str = Form(...)
):
    conn = get_db()
    cur = conn.cursor()
    # Check if this email or phone is already in candidate1.
    cur.execute(
        "SELECT user_id, email, phone FROM candidate1 WHERE lower(email) = lower(?) OR phone = ? COLLATE NOCASE",
        (email.strip(), phone.strip())
    )
    existing = cur.fetchone()
    if existing:
        # Render Already Registered message
        conn.close()
        return HTMLResponse("""
        <html>
        <body style='font-family:sans-serif;background:#fcf6f6;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;'>
            <div style='background:#fff;box-shadow:0 1.5px 9px #eee;border-radius:14px;padding:38px 26px;width:98vw;max-width:420px;'>
                <h2 style='color:#b72600;text-align:center;'>Exam Already Taken</h2>
                <p style='color:#444;font-size:1.13em;text-align:center;'>A candidate with this email or phone number has already registered and cannot take the exam again.</p>
                <p style='text-align:center;'><a href='/' style='color:#145db2;font-weight:bold;'>Return to Home</a></p>
            </div>
        </body>
        </html>
        """, status_code=409)
    cur.execute(
        "INSERT INTO candidate1 (name, email, phone, position_applied, dhan_client_id, dhan_access_token, reg_time) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (name, email, phone, position_applied, dhan_client_id, dhan_access_token, datetime.datetime.now().isoformat())
    )
    user_id = cur.lastrowid
    conn.commit()
    conn.close()
    instructions_html = f"""
    <html>
      <head>
        <title>Exam Instructions - Python Coding Exam - Time Line Investments Pvt Ltd</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
          body {{
            font-family: sans-serif;
            background: #f2f6fc;
            margin:0;
            padding:0;
            display:flex;
            flex-direction:column;
            min-height:100vh;
          }}
          .instructions-panel {{
            background: #fff;
            margin: 50px auto 0 auto;
            box-shadow: 0 2px 8px #cbe6f7;
            border-radius: 10px;
            max-width: 600px;
            width: 95vw;
            padding: 30px 26px 20px 26px;
            box-sizing: border-box;
          }}
          .instructions-panel h2 {{
            text-align:center;
          }}
          .instructions-list {{
            margin: 14px 0 16px 0;
            font-size: 1.11em;
            color: #223366;
          }}
          .checkbox-wrap {{
            margin: 24px 0 12px 0;
            display: flex;
            align-items: center;
          }}
          .start-btn {{
            padding: 10px 38px;
            font-size: 1.11em;
            border: none;
            border-radius: 5px;
            background: #1460b1;
            color: #fff;
            font-weight: 600;
            cursor: pointer;
            margin-left: 0;
          }}
          .start-btn[disabled] {{
            opacity: 0.65;
            background: #bbbbbb;
            cursor: not-allowed;
          }}
          @media (max-width:700px) {{
            .instructions-panel {{
              margin: 13vw 0 0 0;
              padding: 11px 2vw;
              max-width: 99vw;
            }}
          }}
        </style>
      </head>
      <body>
        <div class="instructions-panel">
          <h2>Exam Instructions</h2>
          <ul class="instructions-list">
            <li>The exam consists of 4 programming questions.</li>
            <li>You have to attempt each question in sequence (direct navigation is restricted).</li>
            <li><b>Anti-cheating:</b> Switching browser tabs or copying/pasting code will result in warnings, and after 5 violations, your exam will be forcibly closed.</li>
            <li>Do <b>not</b> refresh or close your browser during the exam; your progress may be lost.</li>
            <li>Each question has its own expected output panel for reference.</li>
            <li>You may use the 'Run Code' button to check your code output before final submission.</li>
            <li><b>The exam has a time limit of 2 hours. After 2 hours, your exam will be auto-submitted and you will see a time exceeded message.</b></li>
            <li>For questions involving the Dhan API, your code must use the <code>dhanhq</code> Python library as described; do not use unofficial or external modules.</li>
            <li>The <b>Dhan API Credentials</b> should be used <b>only</b> for the purpose of testing and must <b>not</b> be used for any other purpose.</li>
            <li>Click the checkbox below to confirm you have read and understood the instructions.</li>
          </ul>
          <form method="get" action="/start_exam">
            <input type="hidden" name="user_id" value="{user_id}">
            <div class="checkbox-wrap">
              <input type="checkbox" id="agree" name="agree" value="yes" onchange="document.getElementById('startbtn').disabled=!this.checked">
              <label for="agree" style="margin-left:9px;user-select:none;cursor:pointer;">I have read and understood the instructions.</label>
            </div>
            <button id="startbtn" type="submit" class="start-btn" disabled>Start Exam</button>
          </form>
        </div>
      </body>
    </html>
    """
    return HTMLResponse(instructions_html)

@app.get("/start_exam")
async def start_exam(user_id: int, agree: Optional[str] = None):
    if agree != "yes":
        return HTMLResponse(
            "<h3 style='font-family:sans-serif;color:red;margin:2vw;'>You must check the confirmation box before starting the exam.<br><a href='/'>Return to Home</a></h3>",
            status_code=403,
        )
    # On start, record the exam start time in exam_timer if not already set
    conn = get_db()
    cur = conn.cursor()
    now_ts = datetime.datetime.now().isoformat()
    try:
        cur.execute("INSERT OR IGNORE INTO exam_timer (user_id, start_time) VALUES (?, ?)", (user_id, now_ts))
        conn.commit()
    except Exception:
        pass
    conn.close()
    return RedirectResponse(url=f"/question?user_id={user_id}&question_idx=0", status_code=302)

def get_exam_remaining_seconds(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT start_time FROM exam_timer WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        # Fallback: if not started, allow full duration
        return EXAM_DURATION_SECONDS
    try:
        start_dt = datetime.datetime.fromisoformat(row["start_time"])
        now_dt = datetime.datetime.now()
        elapsed = (now_dt - start_dt).total_seconds()
        rem = max(0, EXAM_DURATION_SECONDS - int(elapsed))
        return rem
    except Exception:
        return EXAM_DURATION_SECONDS

def format_timer_seconds(sec):
    sec = int(sec)
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

@app.get("/question")
async def jump_question(user_id: int, question_idx: int):
    # Timer logic: check time exceeded at server side
    time_left = get_exam_remaining_seconds(user_id)
    if time_left <= 0:
        # Auto submit if time exceeded
        fill_notattempted(user_id, len(get_exam_questions()))
        send_hr_email(user_id)
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("INSERT INTO exam_completion (user_id, completed_at) VALUES (?, ?)", (user_id, datetime.datetime.now().isoformat()))
            conn.commit()
            conn.close()
        except:
            pass
        # Show time exceeded page
        return HTMLResponse(f"""
        <html><body style='font-family:sans-serif;background:#fceaea;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;'>
        <div style='background:#fff8f8;box-shadow:0 1.5px 9px #f5bdbd;border-radius:14px;padding:36px 20px;text-align:center;max-width:440px;'>
            <h2 style='color:#d52b1f;'>Time Exceeded</h2>
            <p style='font-size:1.13em;color:#480c0c;'>Your 2 hour exam time has been exceeded.<br>The exam was auto-submitted. All your answers have been sent to HR.</p>
            <a href='/' style='color:#147db2;font-weight:bold;'>Return Home</a>
        </div>
        </body></html>
        """)

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT code FROM attempt WHERE user_id=? AND question_idx=? ORDER BY created DESC LIMIT 1", (user_id, question_idx))
    row = cur.fetchone()
    cur.execute("SELECT dhan_client_id, dhan_access_token FROM candidate1 WHERE user_id=?", (user_id,))
    creds = cur.fetchone()
    conn.close()
    last_code = row["code"] if row else ""
    dhan_client_id, dhan_access_token = (creds["dhan_client_id"], creds["dhan_access_token"]) if creds else ("", "")
    # Pass time_left to render_question to display countdown timer
    return HTMLResponse(render_question(user_id, question_idx, last_code, dhan_client_id, dhan_access_token, time_left=time_left))

@app.post("/skip", response_class=HTMLResponse)
async def skip_question(
    user_id: str = Form(...),
    question_idx: str = Form(...)
):
    try:
        uid = int(user_id)
        q_idx = int(question_idx)
        if get_exam_remaining_seconds(uid) <= 0:
            # Timer up, prevent further action & auto-submit
            fill_notattempted(uid, len(get_exam_questions()))
            send_hr_email(uid)
            try:
                conn = get_db()
                cur = conn.cursor()
                cur.execute("INSERT INTO exam_completion (user_id, completed_at) VALUES (?, ?)", (uid, datetime.datetime.now().isoformat()))
                conn.commit()
                conn.close()
            except:
                pass
            # Show time exceeded page
            return HTMLResponse(f"""
            <html><body style='font-family:sans-serif;background:#fceaea;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;'>
            <div style='background:#fff8f8;box-shadow:0 1.5px 9px #f5bdbd;border-radius:14px;padding:36px 20px;text-align:center;max-width:440px;'>
                <h2 style='color:#d52b1f;'>Time Exceeded</h2>
                <p style='font-size:1.13em;color:#480c0c;'>Your 2 hour exam time has been exceeded. <br>The exam was auto-submitted. All your answers have been sent to HR.</p>
                <a href='/' style='color:#147db2;font-weight:bold;'>Return Home</a>
            </div>
            </body></html>
            """)

        # Mark the skip as an attempt with special code/output, only if not already submitted for this q_idx
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM attempt WHERE user_id=? AND question_idx=?", (uid, q_idx))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO attempt (user_id, question_idx, code, output, created) VALUES (?, ?, ?, ?, ?)",
                (uid, q_idx, "[SKIPPED]", "[SKIPPED]", datetime.datetime.now().isoformat())
            )
            conn.commit()
        conn.close()
        # Move to next question
        questions = get_exam_questions()
        if q_idx + 1 >= len(questions):
            # On skip at last question, before marking exam as submitted, fill in [NOT ATTEMPTED] for all unanswered questions
            fill_notattempted(uid, len(questions))
            send_hr_email(uid)
            try:
                conn = get_db()
                cur = conn.cursor()
                cur.execute("INSERT INTO exam_completion (user_id, completed_at) VALUES (?, ?)", (uid, datetime.datetime.now().isoformat()))
                conn.commit()
                conn.close()
            except:
                pass
            return RedirectResponse(f"/submit_exam?user_id={uid}", status_code=302)
        # Prefill credentials for next question if required
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT dhan_client_id, dhan_access_token FROM candidate1 WHERE user_id=?", (uid,))
        creds = cur.fetchone()
        conn.close()
        dhan_client_id = creds["dhan_client_id"] if creds else ""
        dhan_access_token = creds["dhan_access_token"] if creds else ""
        # Pass timer to next page
        return render_question(uid, q_idx + 1, "", dhan_client_id, dhan_access_token, time_left=get_exam_remaining_seconds(uid))
    except Exception as e:
        import traceback
        trace = traceback.format_exc()
        return HTMLResponse(f"<h3>Oops, error occurred during skipping.<br>Error: {e}</h3><pre>{trace}</pre>", status_code=500)

def fill_notattempted(user_id, num_questions):
    # This helper will insert [NOT ATTEMPTED] for all questions not yet in attempt for the given user
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT question_idx FROM attempt WHERE user_id=?", (user_id,))
    existing = set([row["question_idx"] for row in cur.fetchall()])
    now = datetime.datetime.now().isoformat()
    for idx in range(num_questions):
        if idx not in existing:
            cur.execute(
                "INSERT INTO attempt (user_id, question_idx, code, output, created) VALUES (?, ?, ?, ?, ?)",
                (user_id, idx, "[NOT ATTEMPTED]", "[NOT ATTEMPTED]", now)
            )
    conn.commit()
    conn.close()

def render_question(user_id, question_idx, last_code="", dhan_client_id=None, dhan_access_token=None, time_left=None):
    questions = get_exam_questions()
    total = len(questions)
    if question_idx >= total:
        fill_notattempted(user_id, total)
        send_hr_email(user_id)
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO exam_completion (user_id, completed_at) VALUES (?, ?)",
                (user_id, datetime.datetime.now().isoformat())
            )
            conn.commit()
            conn.close()
        except:
            pass
        return RedirectResponse(f"/submit_exam?user_id={user_id}", status_code=302)

    # Fetch credentials if missing
    if dhan_client_id is None or dhan_access_token is None:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT dhan_client_id, dhan_access_token FROM candidate1 WHERE user_id=?", (user_id,))
        creds = cur.fetchone()
        conn.close()
        dhan_client_id = creds["dhan_client_id"] if creds else ""
        dhan_access_token = creds["dhan_access_token"] if creds else ""

    q = questions[question_idx]["question"]
    expected_output = questions[question_idx].get("expected_output", "")

    code_default = ""
    if last_code:
        preload = f"document.getElementById('code').value = {repr(last_code)};"
    else:
        if dhan_client_id or dhan_access_token:
            code_default = (
                f'# Your Dhan API credentials from registration:\n'
                f'client_id = "{dhan_client_id or ""}"\n'
                f'access_token = "{dhan_access_token or ""}"\n\n'
            )
        preload = f'document.getElementById("code").value = {repr(code_default)};'

    # Branding
    company_name_parts = [
        ("T", "ime"),
        ("L", "ine"),
        ("I", "nvestments"),
        ("P", "vt"),
        ("L", "td")
    ]
    header_html = (
        '<div style="text-align:center;font-family:Segoe UI,Arial,sans-serif;">'
        '<span style="font-size:2.15em;font-weight:700;letter-spacing:0.055em;">'
    )
    for first, rest in company_name_parts:
        header_html += (
            f'<span style="color:#ff0000;">{first}</span>'
            f'<span style="color:#23272b;">{rest}</span> '
        )
    header_html += '</span></div>'

    sub_header_html = (
        '<div style="text-align:center;margin-bottom:15px;">'
        '<span style="font-size:1.13em;color:#205e99;font-weight:600;letter-spacing:0.009em;">'
        'Candidate Assessment Portal'
        '</span></div>'
    )

    # ===== Question Navigation as Q1 Q2 Q3 ... then big title, then timer panel (order changed as per instructions) =====
    # Compose question number navigation (Q1 Q2 Q3 ...)
    qnums_html = (
        '<div class="qnav-qnums">'
    )
    for idx in range(total):
        selected = "active-qnav" if idx == question_idx else ""
        qnums_html += (
            f'<button type="button" class="qnav-qbtn {selected}" '
            f'onclick="jumpToQuestion({idx})" aria-label="Go to question {idx+1}">Q{idx+1}</button>'
        )
    qnums_html += '</div>'  # End of qnav-qnums

    # Compose timer panel
    if time_left is None:
        time_left = get_exam_remaining_seconds(user_id)
    formatted_time = format_timer_seconds(time_left)
    h, m, s = formatted_time.split(':')

    timer_panel_html = (
        f'<div class="qnav-timer-panel">'
        f'<span class="timer-icon">⏰</span>'
        f'<span id="examTimer" class="timer-value">{h}:{m}:{s}</span>'
        f'</div>'
    )

    # Centered big question heading between qnums and timer
    # We'll use a flex column + row approach for true centering between margins, or simply use a full-width flex with a center-aligned div
    qbar_timer_html = (
        '<div id="qnav-timer-horizontal" class="qnav-timer-horizontal" style="flex-direction: row; align-items: center;">'
        f'{header_html}'
        f'<div style="flex:1 1 auto;"></div>'
        # Center the heading visually by wrapping in a flex item that grows, and centering with text-align
        f'<div style="flex:2 2 0;text-align:center;display:flex;justify-content:center;">'
        f'<span style="font-size:1.39em;font-weight:700;font-family:\'Segoe UI Semibold\',Arial,sans-serif;letter-spacing:0.015em;color:#1461ab;text-shadow:0 1.2px 7px #f6fafe;margin:0 19px 0 19px;white-space:nowrap;">'
        f'{qnums_html}'
        f'</span>'
        f'</div>'
        f'<div style="flex:1 1 auto;display:flex;justify-content:flex-end;">'
        f'{timer_panel_html}'
        f'</div>'
        f'</div>'
    )

    # Anti-cheat JS (unchanged)
    anticheat_js = """
    <script>
    (function () {
        let allowAntiCheatClear = false;
        function clearViolationForClick(ids) {
            ids.forEach(function (id) {
                var el = document.getElementById(id);
                if (el) {
                    el.addEventListener('click', function (e) {
                        allowAntiCheatClear = true;
                        setTimeout(function () { allowAntiCheatClear = false; }, 1800);
                    }, true);
                }
            });
        }
        document.addEventListener('DOMContentLoaded', function () {
            clearViolationForClick(['submitForm']);
            clearViolationForClick(['skipForm']);
            clearViolationForClick(['runCodeBtn']);
        });
        function getOrCreateTabId() {
            if (!window.sessionStorage) return "default";
            var tid = window.sessionStorage.getItem("exam_tabid");
            if (!tid) {
                tid = Math.random().toString(36).substring(2) + Date.now().toString(36);
                window.sessionStorage.setItem("exam_tabid", tid);
            }
            return tid;
        }
        var tabid = getOrCreateTabId();
        function violateKey() { return "exam_violations:" + tabid; }
        function getViolationCount() {
            if (!window.sessionStorage) return 0;
            var n = window.sessionStorage.getItem(violateKey());
            return n ? parseInt(n, 10) : 0;
        }
        function setViolationCount(n) {
            if (!window.sessionStorage) return;
            window.sessionStorage.setItem(violateKey(), n.toString());
        }
        function hardCrashExam() {
            document.body.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100vh;"><div style="background:#fff;padding:44px 34px;font-family:sans-serif;border-radius:12px;box-shadow:0 2px 10px #f2caca;text-align:center;"><h2 style="color:#b00716;">Exam Terminated</h2><p style="font-size:1.18em;">Your exam was forcibly closed due to 5 anti-cheating violations (tab switch or copy-paste).</p><p style="color:#ca3f1a;font-size:1.06em;">Please contact the test supervisor.</p></div></div>';
            document.body.style.background = "#ffe6e6";
            try { document.querySelectorAll("input,button,textarea").forEach(function (e) { e.disabled = true; }); } catch (e) { }
            setTimeout(function () {
                window.close();
                setTimeout(function () {
                    window.location.replace("about:blank");
                }, 700);
            }, 1600);
            throw new Error('Exam forcibly closed due to 5 violations.');
        }
        function incrementViolation(reason) {
            var count = getViolationCount();
            var confirmText = "Warning #" + (count+1) + " of 5: " + reason + "\\nYou are not allowed to switch tabs or use copy/paste/select all.\\n\\nClick OK if action was accidental -- the violation will NOT be counted;\\nClick Cancel if you admit this was a violation -- the violation WILL be counted.";
            var ok = window.confirm(confirmText);
            if (ok) return;
            count += 1;
            setViolationCount(count);
            if (count < 5) {
                alert("Violation acknowledged. Counted #" + count + " of 5. After 5, your exam will be forcibly closed.");
            } else if (count === 5) {
                if (window.confirm("Violation acknowledged. Counted #" + count + " of 5. This was your last warning. The exam will now terminate.\\nClick OK to close this page.")) {
                    hardCrashExam();
                } else {
                    setTimeout(hardCrashExam, 200);
                }
            }
        }
        function handlePasteCutCopyContext(evtName, humanLabel) {
            document.addEventListener(evtName, function (e) {
                incrementViolation(humanLabel + " is not allowed during the exam.");
                e.preventDefault();
                return false;
            }, true);
        }
        document.addEventListener('DOMContentLoaded', function () {
            handlePasteCutCopyContext('copy', 'Copy');
            handlePasteCutCopyContext('paste', 'Paste');
            handlePasteCutCopyContext('cut', 'Cut');
            handlePasteCutCopyContext('contextmenu', 'Right-click');
            document.addEventListener('keydown', function (e) {
                if ((e.ctrlKey || e.metaKey) && [65, 67, 86, 88].includes(e.keyCode)) {
                    incrementViolation("Keyboard shortcut for Copy/Paste/Select All/Cut is disabled.");
                    e.preventDefault();
                    return false;
                }
            }, true);
            var code = document.getElementById('code');
            if (code) {
                code.addEventListener('focus', function () { });
            }
        });
        var isWindowVisible = true;
        var lastFocus = performance.now(), tabLossTimeout = null;
        window.addEventListener('blur', function () {
            setTimeout(function () {
                if (!document.hasFocus()) {
                    if (!allowAntiCheatClear) {
                        isWindowVisible = false;
                        incrementViolation("Tab/window switch detected (blur/loss of focus).");
                    }
                }
            }, 240);
        });
        window.addEventListener('focus', function () {
            isWindowVisible = true;
            lastFocus = performance.now();
        });
        document.addEventListener('visibilitychange', function () {
            if (document.hidden) {
                if (!allowAntiCheatClear) {
                    isWindowVisible = false;
                    incrementViolation("Tab/window switch detected (visibilitychange, browser tab left).");
                }
            } else {
                isWindowVisible = true;
                lastFocus = performance.now();
            }
        });
        document.addEventListener('DOMContentLoaded', function () {
            var cnt = getViolationCount();
            if (cnt > 0 && cnt < 5) {
                alert(
                    "Warning: You already have " + cnt + " violation(s) in this exam tab. On 5, your exam will close."
                );
            }
        });
        document.addEventListener('keydown', function (e) {
            if (e.keyCode === 44) {
                incrementViolation("PrintScreen is disabled.");
                e.preventDefault();
                return false;
            }
        }, true);
    })();
    </script>
    """

    webcam_html = ""
    webcam_script = f"""
    <script>
    window.onload = function() {{
        {preload}
        var examBox = document.querySelector('.exam-box');
        if (examBox) {{
            examBox.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
        }}
    }};
    </script>
    """

    is_last_question = (question_idx + 1) >= total
    submit_button_text = "Next →" if not is_last_question else "Submit Exam"

    submit_button_html = (
        f"<button id='submitBtn' type='submit' style='font-size:1.005em;"
        f"padding:8px 24px;background:linear-gradient(91deg,#225bbc 0%,#57a7ee 100%);"
        f"color:#fff;border:none;border-radius:5px;"
        f"box-shadow:0 1.5px 6px #b9dfff,0 1.5px 4px #d1d7f0;outline:none;"
        f"font-weight:600;letter-spacing:0.01em;transition:background 0.14s,box-shadow 0.14s;"
        f"min-width:92px;cursor:pointer;margin:0 0 0 0;'>"
        f"{submit_button_text}</button>"
    )
    skip_button_html = (
        f"<form id='skipForm' action='/skip' method='post' style='display:inline;margin-left:13px;margin-top:0;' onsubmit='return confirmSkip();'>"
        f"<input type='hidden' name='user_id' value='{user_id}'>"
        f"<input type='hidden' name='question_idx' value='{question_idx}'>"
        f"<button type='submit' style='font-size:0.97em;background:linear-gradient(91deg,#e9eaf3 80%,#f4f7fc 100%);"
        f"color:#23539c;border:none;padding:7px 20px;border-radius:5px;box-shadow:0 1.5px 6px #e1e9ef,0 1.5px 4px #e8ebe8;"
        f"cursor:pointer;font-weight:500;margin:0;'>Skip</button>"
        f"</form>"
    )

    return f"""
    <!DOCTYPE html>
    <html lang="en" style="height:100%;"width:100%">
    <head>
        <meta charset="UTF-8">
        <title>Python Assessment - Question {question_idx+1} of {total}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            html, body {{
                min-height: 100vh; width: 100vw; margin: 0; padding: 0; box-sizing: border-box;
            }}
            body {{
                font-family: 'Segoe UI', 'Roboto', Arial, sans-serif; width:100vw; min-height:100vh;
                background: linear-gradient(135deg, #f5fafe 0%, #eaf4ff 100%);
                display:flex; flex-direction:column; align-items:stretch; box-sizing: border-box;
            }}
            .container-root {{
                width:100%; min-height:100vh; display:flex; flex-direction:column; align-items:stretch; z-index:2;
            }}
            .qnav-timer-horizontal {{
                display: flex;
                flex-direction: row;
                align-items: center;
                justify-content: space-between;
                background: #f4f8fd;
                border-radius: 14px;
                box-shadow: 0 1.5px 8px #e7eaf4;
           
                max-width: 99%;
                width: 100%;
                padding: 5px 5px 5px 5px;
                position: relative;
                top: 0;
                z-index: 12;
                border: 1.8px solid #d6e3f5;
            }}
            .qnav-qnums {{
                display: flex; gap: 5px;
                align-items:center;
                justify-content: flex-start;
            }}
            .qnav-qbtn {{
                display: inline-block;
                background: #eaf1fc;
                color: #26539b;
                font-weight: 500;
                font-size: 1em;
                padding: 5px 11px;
                border-radius: 6px;
                border: 1.2px solid #8bbcf0;
                margin: 0 1.5px;
                cursor: pointer;
                transition: background .13s, color .13s, box-shadow .14s, border .13s;
                outline: none;
                box-shadow: 0 0.7px 3px #e2eefd;
                vertical-align: middle;
            }}
            .qnav-qbtn.active-qnav {{
                background: linear-gradient(90deg, #346be0 0%, #8fb9fb 100%);
                color: #fff;
                border-color: #356ad6;
                box-shadow: 0 1.2px 5px #c8e2fa;
                font-size: 1.05em;
                font-weight:600;
            }}
            .qnav-qbtn:hover:not(.active-qnav) {{
                background: #e0edfc;
                color: #186fd1;
                border-color: #2684e3;
            }}
            .qnav-timer-panel {{
                display: flex; align-items: center; gap: 7px;
                font-size: 1.12em; color: #835a00; font-weight: 600;
                padding: 7px 16px 7px 13px; background: #faf2db;
                border-radius: 8px; border: 1.5px solid #f1dfbe;
                box-shadow: 0 1.5px 4px #ebe3c9;
            }}
            .timer-value {{
                font-family: 'Fira Mono','Consolas',monospace;
                font-size: 1.15em; color: #cf7e00; margin-left: 0.25em; letter-spacing:0.02em;
            }}
            .timer-icon {{
                font-size: 1.12em;
            }}
            .main-exam-flex {{
                width: 100%; display: flex; flex-direction: column; justify-content: flex-start; align-items: center;
            }}
            .exam-content-outer {{
                flex:1 1 auto; display: flex; flex-direction:column; align-items:center; width:100%;
                min-height:0; box-sizing:border-box; padding-bottom: 31px;
            }}
            .exam-box {{
                background: linear-gradient(146deg,#fff,#e3f0fc 120%);
                border-radius: 18px;
                box-shadow: 0 7px 25px #bdd7ea,0 3px 7px #dfecf5;
                padding: 38px 20px 24px 20px;
                width: 100%; max-width: 99%; box-sizing: border-box;
                border: 2px solid #b9d3ee; animation: boxfloatin 0.6s cubic-bezier(.23,.39,.45,.96);
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: flex-start;
            }}
            @keyframes boxfloatin {{
                from {{ opacity:0; transform: translateY(25px) scale(0.99); }}
                to {{ opacity:1; transform: none; }}
            }}
            /* New layout for exam interaction */
            .exam-layout-split {{
                width: 100%; 
                display: flex; 
                flex-direction: row; 
                gap: 44px; 
                align-items: flex-start; 
                justify-content: center;
                margin: 0 auto;
                margin-bottom: 12px;
            }}
            .exam-layout-left {{
                display: flex; 
                flex-direction: column; 
                gap: 16px; 
                flex: 1.3 1 320px;
                min-width: 260px; 
                max-width: 500px;
            }}
            /* 70/30 split on right-hand column: */
            .exam-layout-right {{
                display: flex; 
                flex-direction: column; 
                gap: 8px;
                flex: 2 1 480px;
                min-width: 320px;
                max-width: 800px;
                height: 400px;
            }}
            .editor-terminal-vertical-split {{
                display: flex;
                flex-direction: column;
                height: 100%;
                flex: 1 1 auto;
            }}
            .editor-slice {{
                flex: 0 0 70%;
                /* This controls the 70% height */
                min-height: 0;
                display: flex;
                flex-direction: column;
            }}
            .terminal-slice {{
                flex: 0 0 30%;
                /* This controls the 30% height */
                min-height: 0;
                display: flex;
                flex-direction: column;
            }}
            .panel-box {{
                background: linear-gradient(130deg,#f9fbff 0%,#e9f1fd 78%);
                border-radius: 13px; padding: 19px 22px 19px 22px;
                flex: 1 1 220px; min-width: 160px; max-width: 100%; border: 1.4px solid #d0dbef;
                box-shadow: 0 2px 8px #e9eef7;
                max-height: 350px; display: flex; flex-direction: column;
                transition: box-shadow 0.12s, border 0.14s;
                align-items: flex-start;
            }}
            .panel-title {{
                font-size:1.16em; padding-bottom:7px; margin-bottom:10px; border-bottom:1.05px solid #d3dce8;
                font-weight: 700; color:#2862a4; letter-spacing:0.01em; flex: 0 0 auto;
                font-family: 'Segoe UI Semibold', 'Roboto', Arial, sans-serif;
            }}
            .panel-question-content, .panel-output-content {{
                font-family:inherit; font-size:1.08em; overflow-y:auto; flex:1 1 auto; min-height:0;
                max-height: 175px; padding-right: 1.5px; scrollbar-color: #bfd3f2 #f6f8fa; scrollbar-width: thin;
                width:100%;
                word-break: break-word;
            }}
            .panel-output-content {{
                font-family:monospace,'Fira Mono','Consolas',monospace;
                background:#f7faf6; font-size:1.08em; border-radius:4px; padding:7px 4px 7px 9px; margin-top:2px;
            }}
            .panel-question-content::-webkit-scrollbar, .panel-output-content::-webkit-scrollbar {{ width:7px; background: #eee; }}
            .panel-question-content::-webkit-scrollbar-thumb, .panel-output-content::-webkit-scrollbar-thumb {{ background: #c4c4d5; border-radius: 7px; }}
            
            /* ====== 70%/30%: Editor much higher than terminal ===== */
            #code {{
                width: 100%; height: 100%; min-height: 0; max-height: none;
                font-family:'Fira Mono','Consolas',monospace; font-size:1.13em;
                border-radius: 8px; border: 2px solid #92bfe9; padding:10px 10px 10px 14px;
                resize: none; box-sizing: border-box; overflow: auto;
                background: linear-gradient(124deg, #fafdff 60%, #e9f1fc 100%);
                box-shadow:0 1.2px 5px #d9e8fc;
                transition:border 0.11s, box-shadow 0.11s; display: block; outline:none; margin-bottom:8px;
                flex: 1 1 auto;
            }}
            #code:focus {{
                border:2px solid #458be7;
                box-shadow:0 2.5px 11px #b0d7fb,0 1.0px 3px #cbe3fc;
                background:linear-gradient(108deg,#f5fafd 0%, #e5f1fc 100%);
            }}
            #code::-webkit-scrollbar {{ width: 8px; background: #e5eefb; }}
            #code::-webkit-scrollbar-thumb {{ background: #d1dbea; border-radius: 6px; }}
            #result {{
                background: linear-gradient(101deg,#252c41,#5386c6 98%);
                color: #fafafa;
                padding: 9px 8px 9px 13px; border-radius: 7px; font-size: 1em;
                white-space: pre-wrap; min-height: 10px; height: 240px; max-height: 250px;
                overflow-y: auto; overflow-x: auto; margin-top: 6px; margin-bottom: 0;
                box-sizing: border-box; display: block;
                box-shadow:0 2px 7px #becaea;
                flex: 1 1 auto;
                scrollbar-color: #888 #252c41;
                scrollbar-width: auto;
                /* Give explicit max-height for scrolling when output is long */
            }}
            #result::-webkit-scrollbar {{ width: 10px; background: #252c41; }}
            #result::-webkit-scrollbar-thumb {{ background: #888; border-radius: 6px; }}
            /* ... rest of style unchanged ... */
        </style>
    </head>
    <body>
        <div class="container-root">
          
            {qbar_timer_html}
            <div class="main-exam-flex">
                <div class="exam-content-outer">
                    <div class="exam-box">
                        <div class="exam-layout-split">
                            <!-- Left side: question and expected output vertically stacked -->
                            <div class="exam-layout-left">
                                <div class="panel-box">
                                    <div class="panel-title">Question</div>
                                    <div class="panel-question-content">{q.replace('\n', '<br>')}</div>
                                </div>
                                <div class="panel-box" style="margin-top:7px;">
                                    <div class="panel-title">Expected Output</div>
                                    <div class="panel-output-content">{expected_output.replace('\n', '<br>')}</div>
                                </div>
                            </div>
                            <!-- Right side: code editor (70%) and output terminal (30%) stacked -->
                            <div class="exam-layout-right">
                                <div class="editor-terminal-vertical-split">
                                    <div class="editor-slice" style="flex:0 0 70%;">
                                        <textarea id="code" placeholder="Write your code here..."></textarea>
                                        <div class="buttons-row-new">
                                            <button id="runCodeBtn" type="button" onclick="runCode()" style="font-size:0.99em;padding:6px 18px;background:linear-gradient(91deg,#1e752e 0%,#38d28d 100%);color:#fff;font-weight:600;border-radius:5px;border:none;box-shadow:0 1.3px 5px #a2cfa9;cursor:pointer;letter-spacing:0.01em;transition:box-shadow 0.11s;outline:none;">&#9654; Run Code</button>
                                            <span id="runstatus" style="font-weight:600;font-size:1em;color:#0e8e2e;"></span>
                                            <form id="submitForm" action="/submit" method="post" onsubmit="return onSubmitForm();" style="display:inline;vertical-align:middle;margin:0;">
                                                <input type="hidden" name="user_id" value="{user_id}">
                                                <input type="hidden" name="question_idx" value="{question_idx}">
                                                <input type="hidden" name="code" id="codeinput">
                                                <input type="hidden" name="output" id="outputinput">
                                                {submit_button_html}
                                            </form>
                                            {skip_button_html}
                                        </div>
                                    </div>
                                    <div class="terminal-slice" style="flex:0 0 30%;">
                                        <div style="margin-top:6px;text-align:left;width:100%;">
                                            <b style="color:#215683;">Output:</b>
                                            <pre id="result"></pre>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="note-bar">
                            <b style="color:#ff0000;">Note:</b> Please use the <em>“Skip”</em> option if you prefer not to answer this question. Once skipped, you will not be able to revisit this question during this exam session.
                        </div>
                    </div>
                </div>
            </div>
        </div>
        {webcam_html}
        <script>
            function jumpToQuestion(idx) {{
                var codeVal = document.getElementById('code').value;
                var userId = document.querySelector('input[name="user_id"]').value;
                var goUrl = '/question?user_id=' + encodeURIComponent(userId) + '&question_idx=' + idx;
                window.location = goUrl;
            }}
            function runCode() {{
                document.getElementById('runstatus').innerText = 'Running...';
                document.getElementById('result').innerText = '';
                fetch('/run_code', {{
                    method: "POST",
                    headers: {{"Content-Type": "application/json"}},
                    body: JSON.stringify({{"code": document.getElementById('code').value}})
                }})
                .then(resp => resp.json())
                .then(function (data) {{
                    document.getElementById('result').innerText = data.output;
                    document.getElementById('runstatus').innerText = data.error ? 'Error' : 'Success';
                    document.getElementById('codeinput').value = document.getElementById('code').value;
                    document.getElementById('outputinput').value = data.output;
                }});
            }}
            function onSubmitForm() {{
                var codeVal = document.getElementById('code').value;
                var outputVal = document.getElementById('result').innerText;

                // Allow blank code on last question, for not attempted.
                if (!codeVal && {int(is_last_question)} && {int(total) > 0}) {{
                    return true;
                }}
                document.getElementById('codeinput').value = codeVal;
                document.getElementById('outputinput').value = outputVal;
                return true;
            }}
            function confirmSkip() {{
                return confirm("Are you sure you want to skip this question? You will not be able to return to it later in this exam.");
            }}

            // Timer JS
            (function timerScript() {{
                var timeLeft = {int(time_left)};
                var timerElem = document.getElementById('examTimer');
                var interval = setInterval(function () {{
                    timeLeft--;
                    if (timerElem) {{
                        var h = Math.floor(timeLeft/3600);
                        var m = Math.floor((timeLeft%3600)/60);
                        var s = timeLeft % 60;
                        var hStr = (h<10?'0':'')+h;
                        var mStr = (m<10?'0':'')+m;
                        var sStr = (s<10?'0':'')+s;
                        timerElem.innerText = hStr+":"+mStr+":"+sStr;
                    }}
                    if (timeLeft <= 0) {{
                        clearInterval(interval);
                        alert("Time Limit Exceeded. The exam will now be submitted.");
                        window.location.href = "/question?user_id={user_id}&question_idx={question_idx}";
                    }}
                }}, 1000);
            }})();
        </script>
        {anticheat_js}
        {webcam_script}
    </body>
    </html>
    """

@app.get("/submit_exam", response_class=HTMLResponse)
def submit_exam(user_id: int):
    return """
    <html style="height:100%;">
    <body style='font-family:sans-serif;width:100vw;height:100vh;margin:0;padding:0;display:flex;flex-direction:column;justify-content:center;align-items:center;'>
    <div style='background:#fff;box-shadow:0 1px 5px #e0e0ee;border-radius:12px;padding:48px 28px;width:98vw;max-width:540px;'>
    <h2 style='text-align:center'>Thank you! You have submitted your exam.</h2>
    <p>All your answers have been sent to HR.</p>
    <a href='/' style="color:#145db2;font-size:1.18em;font-weight:bold;">Register Another</a>
    </div>
    </body></html>
    """

@app.post("/run_code")
async def runcode(payload: dict):
    code = payload.get("code", "")
    max_time = 3
    output = ""
    try:
        import subprocess, tempfile
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py") as f:
            f.write(code)
            f.flush()
            tempname = f.name
        try:
            out = subprocess.run(
                [sys.executable, tempname],
                capture_output=True, text=True, timeout=max_time
            )
            output = (out.stdout or "") + (("\n" + out.stderr) if out.stderr else "")
            error = False
        except subprocess.TimeoutExpired:
            output = f"Error: Code timed out (> {max_time}s)"
            error = True
        except Exception as e:
            output = f"Error: {e}"
            error = True
        finally:
            try:
                os.unlink(tempname)
            except Exception:
                pass
    except Exception as e:
        output = f"Infra Error: {e}"
        error = True
    if len(output) > 1000:
        output = output[:1000] + "\n[Output Truncated]"
    return JSONResponse(content={"output": output, "error": error})

@app.post("/submit", response_class=HTMLResponse)
async def submit(
    user_id: str = Form(...),
    question_idx: str = Form(...),
    code: str = Form(...),
    output: str = Form(...)
):
    try:
        uid = int(user_id)
        if get_exam_remaining_seconds(uid) <= 0:
            fill_notattempted(uid, len(get_exam_questions()))
            send_hr_email(uid)
            try:
                conn = get_db()
                cur = conn.cursor()
                cur.execute("INSERT INTO exam_completion (user_id, completed_at) VALUES (?, ?)", (uid, datetime.datetime.now().isoformat()))
                conn.commit()
                conn.close()
            except:
                pass
            # Show time exceeded page
            return HTMLResponse(f"""
            <html><body style='font-family:sans-serif;background:#fceaea;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;'>
            <div style='background:#fff8f8;box-shadow:0 1.5px 9px #f5bdbd;border-radius:14px;padding:36px 20px;text-align:center;max-width:440px;'>
                <h2 style='color:#d52b1f;'>Time Exceeded</h2>
                <p style='font-size:1.13em;color:#480c0c;'>Your 2 hour exam time has been exceeded.<br>The exam was auto-submitted. All your answers have been sent to HR.</p>
                <a href='/' style='color:#147db2;font-weight:bold;'>Return Home</a>
            </div>
            </body></html>
            """)

        # If code is submitted AND output is blank, treat as not run/not answered
        # Insert special '[NOT ATTEMPTED]' mark for this attempt
        conn = get_db()
        cur = conn.cursor()
        q_idx = int(question_idx)
        store_code = code
        store_output = output
        if (not output.strip()) and code.strip():  # Code present, no output, treat as not attempted/run
            store_code = "[NOT RUN OR BLANK OUTPUT]"
            store_output = "[NOT RUN OR BLANK OUTPUT]"
        elif (not code.strip()) and (not output.strip()):
            store_code = "[NOT ATTEMPTED]"
            store_output = "[NOT ATTEMPTED]"

        cur.execute(
            "INSERT INTO attempt (user_id, question_idx, code, output, created) VALUES (?, ?, ?, ?, ?)",
            (uid, q_idx, store_code, store_output, datetime.datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        questions = get_exam_questions()
        if q_idx + 1 >= len(questions):
            fill_notattempted(uid, len(questions))
            send_hr_email(uid)
            try:
                conn = get_db()
                cur = conn.cursor()
                cur.execute("INSERT INTO exam_completion (user_id, completed_at) VALUES (?, ?)", (uid, datetime.datetime.now().isoformat()))
                conn.commit()
                conn.close()
            except:
                pass
            return RedirectResponse(f"/submit_exam?user_id={uid}", status_code=302)
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT dhan_client_id, dhan_access_token FROM candidate1 WHERE user_id=?", (uid,))
        creds = cur.fetchone()
        conn.close()
        dhan_client_id = creds["dhan_client_id"] if creds else ""
        dhan_access_token = creds["dhan_access_token"] if creds else ""
        return render_question(uid, q_idx + 1, "", dhan_client_id, dhan_access_token, time_left=get_exam_remaining_seconds(uid))
    except Exception as e:
        import traceback
        trace = traceback.format_exc()
        return HTMLResponse(f"<h3>Oops, error occurred during submission.<br>Error: {e}</h3><pre>{trace}</pre>", status_code=500)

