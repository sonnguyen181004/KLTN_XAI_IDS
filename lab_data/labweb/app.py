from flask import Flask, request, session, redirect, url_for, render_template_string, jsonify, abort
from markupsafe import escape

app = Flask(__name__)
app.secret_key = "lab-only-secret-key"

PRODUCTS = [
    {"id": i + 1, "name": n, "price": p, "desc": d}
    for i, (n, p, d) in enumerate([
        ("Laptop Lab 14", 15900000, "Laptop mong nhe cho sinh vien."),
        ("Chuot khong day", 250000, "Chuot khong day yen tinh."),
        ("Ban phim co", 890000, "Ban phim co switch do."),
        ("Man hinh 24 inch", 3200000, "Man hinh IPS 75Hz."),
        ("Tai nghe", 450000, "Tai nghe chup tai."),
        ("Webcam HD", 520000, "Webcam 1080p."),
        ("O cung SSD 512GB", 1100000, "SSD SATA toc do cao."),
        ("Balo laptop", 380000, "Balo chong nuoc."),
    ])
]
MESSAGES = []

BASE = """<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }} - Lab Shop</title>
<style>
body{font-family:Arial,sans-serif;margin:0;background:#f4f6f8;color:#222}
header{background:#1f3a5f;color:#fff;padding:14px 24px;display:flex;justify-content:space-between;align-items:center}
header a{color:#fff;margin-left:16px;text-decoration:none}
main{max-width:960px;margin:24px auto;padding:0 16px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:16px}
.card{background:#fff;border-radius:8px;padding:16px;box-shadow:0 1px 3px #0002}
.price{color:#c0392b;font-weight:bold}
input,textarea{width:100%;padding:8px;margin:6px 0 12px;box-sizing:border-box}
button{background:#1f3a5f;color:#fff;border:0;padding:9px 18px;border-radius:5px;cursor:pointer}
.err{color:#c0392b}.ok{color:#1e8449}
footer{text-align:center;color:#888;padding:24px;font-size:13px}
</style></head><body>
<header><b>Lab Shop</b><nav>
<a href="/">Trang chu</a><a href="/products">San pham</a><a href="/search">Tim kiem</a>
<a href="/contact">Lien he</a><a href="/about">Gioi thieu</a>
{% if session.get('user') %}<a href="/dashboard">{{ session['user'] }}</a><a href="/logout">Thoat</a>
{% else %}<a href="/login">Dang nhap</a>{% endif %}</nav></header>
<main>{{ body|safe }}</main>
<footer>Lab Shop - web thu nghiem trong mang noi bo, khong co du lieu that.</footer>
</body></html>"""


def page(title, body):
    return render_template_string(BASE, title=title, body=body)


def card(p):
    return ('<div class="card"><h3><a href="/product/%d">%s</a></h3><p>%s</p>'
            '<p class="price">%s d</p></div>' % (p["id"], escape(p["name"]), escape(p["desc"]), format(p["price"], ",")))


@app.get("/")
def home():
    body = "<h1>Chao mung den Lab Shop</h1><p>Cua hang thiet bi may tinh dung de thu nghiem he thong IDS.</p><div class='grid'>"
    body += "".join(card(p) for p in PRODUCTS[:4]) + "</div>"
    return page("Trang chu", body)


@app.get("/products")
def products():
    return page("San pham", "<h1>San pham</h1><div class='grid'>" + "".join(card(p) for p in PRODUCTS) + "</div>")


@app.get("/product/<int:pid>")
def product(pid):
    p = next((x for x in PRODUCTS if x["id"] == pid), None)
    if not p:
        abort(404)
    return page(p["name"], "<h1>%s</h1><p>%s</p><p class='price'>%s d</p>" % (escape(p["name"]), escape(p["desc"]), format(p["price"], ",")))


@app.get("/search")
def search():
    q = request.args.get("q", "").strip().lower()
    found = [p for p in PRODUCTS if q and q in p["name"].lower()]
    body = "<h1>Tim kiem</h1><form method='get'><input name='q' placeholder='Nhap ten san pham' value='%s'><button>Tim</button></form>" % escape(q)
    if q:
        body += "<p>Tim thay %d ket qua cho '%s'.</p><div class='grid'>%s</div>" % (len(found), escape(q), "".join(card(p) for p in found))
    return page("Tim kiem", body)


@app.route("/contact", methods=["GET", "POST"])
def contact():
    note = ""
    if request.method == "POST":
        MESSAGES.append({"name": request.form.get("name", "")[:80], "msg": request.form.get("msg", "")[:500]})
        note = "<p class='ok'>Da nhan tin nhan cua ban.</p>"
    body = "<h1>Lien he</h1>%s<form method='post'><label>Ten</label><input name='name'><label>Noi dung</label><textarea name='msg' rows='4'></textarea><button>Gui</button></form>" % note
    return page("Lien he", body)


@app.get("/about")
def about():
    return page("Gioi thieu", "<h1>Gioi thieu</h1><p>Day la web thu nghiem cua de tai IDS co giai thich.</p>")


@app.get("/big")
def big():
    return page("Trang dai", "<h1>Trang noi dung dai</h1>" + "<p>noi dung lab </p>" * 3000)


@app.route("/login", methods=["GET", "POST"])
def login():
    err = ""
    if request.method == "POST":
        if request.form.get("u") == "labdemo" and request.form.get("p") == "Lab-Pass-01":
            session["user"] = "labdemo"
            return redirect(url_for("dashboard"))
        err = "<p class='err'>Sai ten dang nhap hoac mat khau.</p>"
    body = "<h1>Dang nhap</h1>%s<form method='post'><label>Ten dang nhap</label><input name='u'><label>Mat khau</label><input name='p' type='password'><button>Dang nhap</button></form>" % err
    return page("Dang nhap", body)


@app.get("/dashboard")
def dashboard():
    if not session.get("user"):
        return redirect(url_for("login"))
    return page("Tai khoan", "<h1>Xin chao, %s</h1><p>Ban dang dang nhap. Co %d tin nhan lien he.</p>" % (escape(session["user"]), len(MESSAGES)))


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.get("/api/products")
def api_products():
    return jsonify(PRODUCTS)


@app.get("/health")
def health():
    return "ok"


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, threaded=True)
