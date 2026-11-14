import html
import json
import os
import time
import pymysql
import requests
from flask import Flask, jsonify, render_template_string, request
from jose import jwt

KEYCLOAK_INTERNAL_URL = os.getenv(
    "KEYCLOAK_INTERNAL_URL",
    "http://authentication-identity-server:8080",
)
ISSUER = os.getenv(
    "OIDC_ISSUER",
    f"{KEYCLOAK_INTERNAL_URL}/realms/realm_sv001",
)
AUDIENCE = os.getenv("OIDC_AUDIENCE", "myapp")

DB_HOST = os.getenv("DB_HOST", "relational-database-server")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root")
DB_NAME = os.getenv("DB_NAME", "studentdb")

_JWKS_CACHE = {}

TABLE_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{{ title }}</title>
  <script>
    if (localStorage.getItem("minicloud-theme") === "dark") {
      document.documentElement.setAttribute("data-theme", "dark");
    }
  </script>
  <style>
    :root {
      --bg: #f4f6f9;
      --surface: #ffffff;
      --ink: #0f172a;
      --muted: #64748b;
      --line: #e2e8f0;
      --row-hover: #f8fafc;
      --btn-bg: #ffffff;
      --btn-border: #cbd5e1;
      --accent: {{ accent_light }};
    }
    [data-theme="dark"] {
      --bg: #0b1120;
      --surface: #111827;
      --ink: #f1f5f9;
      --muted: #94a3b8;
      --line: #1f2937;
      --row-hover: #1e293b;
      --btn-bg: #1e293b;
      --btn-border: #334155;
      --accent: {{ accent_dark }};
    }
    body {
      font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
      background: var(--bg);
      color: var(--ink);
      margin: 0;
      padding: 36px 20px;
      transition: background 0.2s, color 0.2s;
    }
    .wrap { max-width: 960px; margin: 0 auto; }
    .top {
      display: flex; justify-content: space-between; align-items: center;
      flex-wrap: wrap; gap: 12px; margin-bottom: 22px;
    }
    h1 { margin: 0; font-size: 1.6rem; color: var(--accent); }
    .sub { color: var(--muted); font-size: 0.9rem; margin-top: 4px; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; }
    .btn {
      text-decoration: none; color: var(--ink); font-size: 0.88rem; font-weight: 600;
      padding: 8px 14px; border-radius: 8px; background: var(--btn-bg);
      border: 1px solid var(--btn-border); cursor: pointer; font-family: inherit;
    }
    .btn:hover { opacity: 0.88; }
    .card {
      background: var(--surface); border: 1px solid var(--line);
      border-radius: 14px; overflow: hidden; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
    }
    table { width: 100%; border-collapse: collapse; }
    thead { background: {{ header_bg }}; color: #fff; }
    th, td { padding: 14px 18px; text-align: left; font-size: 0.93rem; }
    tbody tr { border-bottom: 1px solid var(--line); }
    tbody tr:hover { background: var(--row-hover); }
    tbody tr:last-child { border-bottom: none; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="top">
      <div>
        <h1>{{ title }}</h1>
        <div class="sub">{{ subtitle }}</div>
      </div>
      <div class="actions">
        <button class="btn" type="button" id="theme-toggle">Giao diện Tối</button>
        <a class="btn" href="?format=json">Xem Raw JSON</a>
        <a class="btn" href="/">Trang chính</a>
      </div>
    </div>
    <div class="card">
      <table>
        <thead>
          <tr>{% for col in columns %}<th>{{ col }}</th>{% endfor %}</tr>
        </thead>
        <tbody>
          {% for row in rows %}
          <tr>{% for cell in row %}<td>{{ cell }}</td>{% endfor %}</tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
  <script>
    const btn = document.getElementById("theme-toggle");
    function syncLabel() {
      const isDark = document.documentElement.getAttribute("data-theme") === "dark";
      btn.textContent = isDark ? "Giao diện Sáng" : "Giao diện Tối";
    }
    syncLabel();
    btn.addEventListener("click", () => {
      const isDark = document.documentElement.getAttribute("data-theme") === "dark";
      if (isDark) {
        document.documentElement.removeAttribute("data-theme");
        localStorage.setItem("minicloud-theme", "light");
      } else {
        document.documentElement.setAttribute("data-theme", "dark");
        localStorage.setItem("minicloud-theme", "dark");
      }
      syncLabel();
    });
  </script>
</body>
</html>"""


def wants_html():
    if request.args.get("format") == "json":
        return False
    best = request.accept_mimetypes.best_match(["application/json", "text/html"])
    return best == "text/html" and (
        request.accept_mimetypes["text/html"] > request.accept_mimetypes["application/json"]
    )


def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5,
    )


def get_jwks(realm="realm_sv001"):
    now = time.time()
    cached = _JWKS_CACHE.get(realm)
    if not cached or now - cached["ts"] > 600:
        jwks_url = f"{KEYCLOAK_INTERNAL_URL}/realms/{realm}/protocol/openid-connect/certs"
        resp = requests.get(jwks_url, timeout=5)
        resp.raise_for_status()
        _JWKS_CACHE[realm] = {"jwks": resp.json(), "ts": now}
    return _JWKS_CACHE[realm]["jwks"]


app = Flask(__name__)


@app.get("/hello", strict_slashes=False)
def hello():
    return jsonify(message="Hello from App Server!")


@app.get("/student", strict_slashes=False)
def student():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_dir, "students.json"), encoding="utf-8") as f:
        data = json.load(f)

    if wants_html():
        rows = [[s["id"], s["name"], s["major"], s["gpa"]] for s in data]
        return render_template_string(
            TABLE_TEMPLATE,
            title="Danh sách sinh viên (JSON)",
            subtitle="Nguồn dữ liệu: students.json (Endpoint /student)",
            accent_light="#4338ca",
            accent_dark="#a5b4fc",
            header_bg="#4f46e5",
            columns=["ID", "Name", "Major", "GPA"],
            rows=rows,
        )
    return jsonify(data)


@app.get("/students-db", strict_slashes=False)
def students_db():
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, student_id, fullname, DATE_FORMAT(dob, '%Y-%m-%d') AS dob, major "
                    "FROM students ORDER BY id"
                )
                data = cur.fetchall()
        finally:
            conn.close()
    except Exception as e:
        return jsonify(error=str(e)), 500

    if wants_html():
        rows = [[s["id"], s["student_id"], s["fullname"], s["dob"], s["major"]] for s in data]
        return render_template_string(
            TABLE_TEMPLATE,
            title="Danh sách sinh viên (G09-MiniCloud)",
            subtitle=f"Nguồn dữ liệu: G09-MiniCloud ({html.escape(DB_NAME)}.students)",
            accent_light="#047857",
            accent_dark="#34d399",
            header_bg="#059669",
            columns=["#", "Student ID", "Fullname", "DOB", "Major"],
            rows=rows,
        )
    return jsonify(data)


@app.post("/students-db")
def create_student_db():
    body = request.get_json(silent=True) or {}
    student_id = body.get("student_id")
    fullname = body.get("fullname")
    dob = body.get("dob")
    major = body.get("major")
    if not student_id or not fullname:
        return jsonify(error="student_id and fullname are required"), 400
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO students (student_id, fullname, dob, major) VALUES (%s, %s, %s, %s)",
                    (student_id, fullname, dob, major),
                )
                new_id = cur.lastrowid
            conn.commit()
            return jsonify(message="Created student", id=new_id), 201
        finally:
            conn.close()
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.put("/students-db/<int:student_pk>")
def update_student_db(student_pk):
    body = request.get_json(silent=True) or {}
    fullname = body.get("fullname")
    major = body.get("major")
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE students SET fullname = COALESCE(%s, fullname), major = COALESCE(%s, major) WHERE id = %s",
                    (fullname, major, student_pk),
                )
            conn.commit()
            return jsonify(message="Updated student", id=student_pk)
        finally:
            conn.close()
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.delete("/students-db/<int:student_pk>")
def delete_student_db(student_pk):
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM students WHERE id = %s", (student_pk,))
            conn.commit()
            return jsonify(message="Deleted student", id=student_pk)
        finally:
            conn.close()
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.get("/secure")
def secure():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify(error="Missing Bearer token"), 401

    token = auth.split(" ", 1)[1]
    try:
        unverified = jwt.get_unverified_claims(token)
        token_iss = unverified.get("iss", ISSUER)
        if "/realms/" in token_iss:
            realm = token_iss.rstrip("/").split("/realms/")[-1]
        else:
            realm = ISSUER.rstrip("/").split("/realms/")[-1]

        payload = jwt.decode(
            token,
            get_jwks(realm),
            algorithms=["RS256"],
            options={"verify_aud": False, "verify_iss": False},
        )

        aud_claim = payload.get("aud", [])
        if isinstance(aud_claim, str):
            aud_claim = [aud_claim]
        azp_claim = payload.get("azp", "")
        allowed = {AUDIENCE, "flask-app", "account", "admin-cli"}
        if not (allowed.intersection(aud_claim) or azp_claim in allowed):
            return jsonify(error="Invalid token audience"), 401

        return jsonify(
            message="Secure resource OK",
            preferred_username=payload.get("preferred_username"),
            realm=realm,
            client_id=azp_claim or AUDIENCE,
        )
    except Exception as e:
        return jsonify(error=str(e)), 401


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
