import html
from datetime import date
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

TABLE_TEMPLATE = r"""<!DOCTYPE html>
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
    .table-scroll { overflow-x: auto; }
    .editor { padding: 20px; margin-bottom: 20px; }
    .fields { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin: 16px 0; }
    label { display: grid; gap: 6px; }
    input { box-sizing: border-box; width: 100%; padding: 10px; border: 1px solid var(--btn-border); border-radius: 6px; background: var(--btn-bg); color: var(--ink); font: inherit; }
    .danger { color: #dc2626; }
    #crud-status { min-height: 24px; margin: 12px 0; }
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
    {% if editable %}
    <form id="student-form" class="card editor">
      <h2 id="editor-title">Thêm sinh viên</h2>
      <p class="sub">Mã sinh viên được cấp tự động khi thêm mới.</p>
      <div class="fields">
        <label>Họ và tên<input name="fullname" maxlength="100" required /></label>
        <label>Ngày sinh<input name="dob" type="date" /></label>
        <label>Ngành học<input name="major" maxlength="50" /></label>
      </div>
      <div class="actions">
        <button class="btn" type="submit" id="save-student">Thêm sinh viên</button>
        <button class="btn" type="button" id="cancel-edit" hidden>Hủy sửa</button>
      </div>
    </form>
    <div id="crud-status" role="status" aria-live="polite"></div>
    {% endif %}
    <div class="card table-scroll">
      <table>
        <thead>
          <tr>{% for col in columns %}<th>{{ col }}</th>{% endfor %}{% if editable %}<th>Thao tác</th>{% endif %}</tr>
        </thead>
        <tbody>
          {% for row in rows %}
          <tr>{% for cell in row %}<td>{{ cell if cell is not none else "" }}</td>{% endfor %}
            {% if editable %}
            <td><div class="actions">
              <button class="btn" type="button" data-edit="{{ row[0] }}">Sửa</button>
              <button class="btn danger" type="button" data-delete="{{ row[0] }}">Xóa</button>
            </div></td>
            {% endif %}
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
  <script>
    {% if editable %}
    const students = {{ students | tojson }};
    const form = document.getElementById("student-form");
    const status = document.getElementById("crud-status");
    const saveButton = document.getElementById("save-student");
    const cancelButton = document.getElementById("cancel-edit");
    let editingId = null;
    let busy = false;
    // Keep requests on the current entry point: Gateway, Web proxy, or direct Flask.
    const apiUrl = window.location.pathname.replace(/\/$/, "");
    const flash = sessionStorage.getItem("minicloud-student-message");
    if (flash) {
      status.textContent = flash;
      sessionStorage.removeItem("minicloud-student-message");
    }
    function resetEditor() {
      editingId = null;
      form.reset();
      document.getElementById("editor-title").textContent = "Thêm sinh viên";
      saveButton.textContent = "Thêm sinh viên";
      cancelButton.hidden = true;
    }
    async function mutate(url, method, data, message) {
      if (busy) return;
      busy = true;
      document.querySelectorAll("#student-form button, [data-edit], [data-delete]")
        .forEach(button => button.disabled = true);
      status.textContent = "Đang lưu thay đổi…";
      try {
        const options = { method, headers: { Accept: "application/json" } };
        if (data) {
          options.headers["Content-Type"] = "application/json";
          options.body = JSON.stringify(data);
        }
        const response = await fetch(url, options);
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || "Thao tác thất bại.");
        sessionStorage.setItem("minicloud-student-message", message);
        window.location.reload();
      } catch (error) {
        status.textContent = error.message;
        busy = false;
        document.querySelectorAll("#student-form button, [data-edit], [data-delete]")
          .forEach(button => button.disabled = false);
      }
    }
    form.addEventListener("submit", event => {
      event.preventDefault();
      const data = Object.fromEntries(new FormData(form));
      for (const key of Object.keys(data)) data[key] = data[key].trim();
      data.dob = data.dob || null;
      mutate(editingId === null ? apiUrl : apiUrl + "/" + editingId,
        editingId === null ? "POST" : "PUT", data,
        editingId === null ? "Đã thêm sinh viên." : "Đã cập nhật sinh viên.");
    });
    cancelButton.addEventListener("click", resetEditor);
    document.querySelectorAll("[data-edit]").forEach(button => {
      button.addEventListener("click", () => {
        const student = students.find(item => item.id === Number(button.dataset.edit));
        editingId = student.id;
        for (const field of ["fullname", "dob", "major"]) {
          form.elements.namedItem(field).value = student[field] || "";
        }
        document.getElementById("editor-title").textContent = "Sửa sinh viên";
        saveButton.textContent = "Lưu thay đổi";
        cancelButton.hidden = false;
        form.scrollIntoView({ behavior: "smooth", block: "start" });
        form.elements.namedItem("fullname").focus();
      });
    });
    document.querySelectorAll("[data-delete]").forEach(button => {
      button.addEventListener("click", () => {
        const student = students.find(item => item.id === Number(button.dataset.delete));
        if (window.confirm("Xóa sinh viên " + student.fullname + "?")) {
          mutate(apiUrl + "/" + student.id, "DELETE", null, "Đã xóa sinh viên.");
        }
      });
    });
    {% endif %}
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
            editable=True,
            students=data,
        )
    return jsonify(data)


def validate_student_fields(body, partial=False):
    if not isinstance(body, dict):
        return None, "Dữ liệu phải là một đối tượng JSON."
    fields = {}
    for key, limit in (("student_id", 10), ("fullname", 100), ("major", 50)):
        if key not in body:
            if not partial and key == "fullname":
                return None, "Vui lòng nhập họ tên."
            continue
        value = body[key]
        # Existing API callers can omit or pass null for optional updates.
        if partial and value is None:
            continue
        if value is None and key == "major":
            fields[key] = None
            continue
        if not isinstance(value, str):
            return None, "Các trường văn bản phải là chuỗi."
        value = value.strip()
        if key != "major" and not value:
            return None, "Mã sinh viên và họ tên không được để trống."
        if len(value) > limit:
            return None, f"{key} tối đa {limit} ký tự."
        fields[key] = value
    if "dob" in body:
        dob = body["dob"]
        if dob in (None, ""):
            fields["dob"] = None
        else:
            try:
                if not isinstance(dob, str) or date.fromisoformat(dob).isoformat() != dob:
                    return None, "Ngày sinh phải có định dạng YYYY-MM-DD."
            except ValueError:
                return None, "Ngày sinh không hợp lệ."
            fields["dob"] = dob
    return fields, None


@app.post("/students-db", strict_slashes=False)
def create_student_db():
    fields, error = validate_student_fields(request.get_json(silent=True))
    if error:
        return jsonify(error=error), 400
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            student_id = fields.get("student_id")
            if student_id is None:
                # Create lazily so existing databases work without resetting their volumes.
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS student_id_sequence "
                    "(id TINYINT PRIMARY KEY, value BIGINT UNSIGNED NOT NULL)"
                )
                cur.execute("INSERT IGNORE INTO student_id_sequence (id, value) VALUES (1, 0)")
                cur.execute(
                    "SELECT COALESCE(MAX(CAST(SUBSTRING(student_id, 3) AS UNSIGNED)), 0) AS maximum "
                    "FROM students WHERE student_id REGEXP '^SV[0-9]+$'"
                )
                maximum = cur.fetchone()["maximum"]
                # The sequence row serializes concurrent creates and survives deletions.
                cur.execute(
                    "UPDATE student_id_sequence "
                    "SET value = LAST_INSERT_ID(GREATEST(value, %s) + 1) WHERE id = 1",
                    (maximum,),
                )
                cur.execute("SELECT LAST_INSERT_ID() AS number")
                student_id = f"SV{cur.fetchone()['number']:03d}"
                if len(student_id) > 10:
                    conn.rollback()
                    return jsonify(error="Đã hết phạm vi mã sinh viên tự động."), 409
            cur.execute(
                "INSERT INTO students (student_id, fullname, dob, major) VALUES (%s, %s, %s, %s)",
                (student_id, fields["fullname"], fields.get("dob"), fields.get("major")),
            )
            new_id = cur.lastrowid
        conn.commit()
        return jsonify(message="Created student", id=new_id, student_id=student_id), 201
    except Exception as e:
        if conn is not None:
            conn.rollback()
        return jsonify(error=str(e)), 500
    finally:
        if conn is not None:
            conn.close()


@app.put("/students-db/<int:student_pk>")
def update_student_db(student_pk):
    fields, error = validate_student_fields(request.get_json(silent=True), partial=True)
    if error:
        return jsonify(error=error), 400
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Lock the row so a concurrent delete cannot invalidate the existence check.
            cur.execute("SELECT id FROM students WHERE id = %s FOR UPDATE", (student_pk,))
            if cur.fetchone() is None:
                conn.rollback()
                return jsonify(error="Không tìm thấy sinh viên."), 404
            if fields:
                assignments = ", ".join(f"{key} = %s" for key in fields)
                cur.execute(
                    f"UPDATE students SET {assignments} WHERE id = %s",
                    (*fields.values(), student_pk),
                )
        conn.commit()
        return jsonify(message="Updated student", id=student_pk)
    except Exception as e:
        if conn is not None:
            conn.rollback()
        return jsonify(error=str(e)), 500
    finally:
        if conn is not None:
            conn.close()


@app.delete("/students-db/<int:student_pk>")
def delete_student_db(student_pk):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM students WHERE id = %s", (student_pk,))
            deleted = cur.rowcount
        conn.commit()
        if not deleted:
            return jsonify(error="Không tìm thấy sinh viên."), 404
        return jsonify(message="Deleted student", id=student_pk)
    except Exception as e:
        if conn is not None:
            conn.rollback()
        return jsonify(error=str(e)), 500
    finally:
        if conn is not None:
            conn.close()


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
