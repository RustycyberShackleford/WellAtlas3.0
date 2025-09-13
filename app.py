
import os, sqlite3, random, datetime
from flask import Flask, render_template, request, jsonify, abort

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "wellatlas.db")

app = Flask(__name__)

def db():
    if not os.path.isdir(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def ensure_schema():
    c = db(); cur = c.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS customers(id INTEGER PRIMARY KEY, name TEXT UNIQUE, address TEXT, phone TEXT, email TEXT, notes TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS sites(id INTEGER PRIMARY KEY, customer_id INTEGER, name TEXT, description TEXT, latitude REAL, longitude REAL)")
    cur.execute("CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY, site_id INTEGER, job_number TEXT, job_category TEXT, description TEXT, depth_ft REAL, casing_diameter_in REAL, pump_hp REAL, flow_rate_gpm REAL, static_level_ft REAL, drawdown_ft REAL, install_date TEXT, status TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS job_notes(id INTEGER PRIMARY KEY, job_id INTEGER, body TEXT, created_at TEXT)")
    c.commit(); c.close()

def seed_data():
    c = db(); cur = c.cursor()
    cur.execute("SELECT COUNT(*) FROM customers")
    if cur.fetchone()[0] > 0:
        c.close(); return

    presidents = [
        "Washington","Adams","Jefferson","Madison","Monroe","JQ Adams","Jackson","Van Buren","WH Harrison","Tyler","Polk","Taylor",
        "Fillmore","Pierce","Buchanan","Lincoln","A Johnson","Grant","Hayes","Garfield","Arthur","Cleveland","B Harrison","McKinley",
        "T Roosevelt","Taft","Wilson","Harding","Coolidge","Hoover","FDR","Truman","Eisenhower","Kennedy","LBJ","Nixon","Ford","Carter","Reagan","Bush"
    ]
    mining_terms = [
        "Mother Lode","Prospector's Claim","Stamp Mill","Ore Vein","Pay Dirt","Hydraulic Pit","Tailings Pile","Mine Shaft",
        "Pan Creek","Drift Tunnel","Headframe","Sluice Box","Bedrock Bend","Quartz Ridge","Assay Flats","Nugget Gulch",
        "Pickaxe Point","Rocker Reach","Gold Pan Flat","Tailrace Trail"
    ]

    rnd = random.Random(77)
    job_no = 25001
    today = datetime.date.today()

    def phone():
        return f"(530) {rnd.randint(200,999)}-{rnd.randint(1000,9999)}"

    for pres in presidents[:40]:
        cur.execute("INSERT INTO customers(name,address,phone,email,notes) VALUES(?,?,?,?,?)",
            (pres+" Well Co.", f"{rnd.randint(100,999)} Main St, North State, CA",
             phone(), f"contact@{pres.replace(' ','').lower()}.example",
             "Preferred vendor; service area within 60mi. Terms: net-30. Primary contact: Ops Manager."))
        cid = cur.lastrowid

        chosen = rnd.sample(mining_terms, k=10)
        for sname in chosen:
            lat = 39.9 + rnd.uniform(-0.35,0.35)
            lon = -122.0 + rnd.uniform(-0.35,0.35)
            sdesc = f"Site '{sname}' supporting irrigation/domestic supply near North State corridor. Soil: alluvium & sand/gravel. Access: county easement; power on pole."
            cur.execute("INSERT INTO sites(customer_id,name,description,latitude,longitude) VALUES(?,?,?,?,?)",
                        (cid, sname, sdesc, lat, lon))
            sid = cur.lastrowid

            cat = rnd.choice(["Domestic","Drilling","Ag","Electrical"])
            depth = rnd.choice([120,160,200,240,280,320,360,400])
            casing = rnd.choice([4,6,8])
            pump = rnd.choice([2,3,5,7.5,10])
            flow = rnd.choice([15,25,35,45,60])
            static = rnd.choice([20,30,40,50,60])
            draw = rnd.choice([5,10,15,20])
            status = rnd.choice(["Scheduled","In Progress","Complete"])

            jdesc = (f"{cat} well scope: target depth ~{depth} ft; {casing} in steel casing; set {pump} HP pump; expected yield ~{flow} GPM based on nearby logs. "
                     f"Static level ~{static} ft; predicted drawdown {draw} ft at duty flow. Test pumping, chlorination, panel inspection, flow verification. "
                     "Deliverables: as-built, coordinates, pump curve, bacteriological test, and start-up checklist.")

            cur.execute(
                "INSERT INTO jobs(site_id,job_number,job_category,description,depth_ft,casing_diameter_in,pump_hp,flow_rate_gpm,static_level_ft,drawdown_ft,install_date,status) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (sid, str(job_no), cat, jdesc, depth, casing, pump, flow, static, draw, str(today), status)
            )
            jid = cur.lastrowid

            notes = [
                f"Pre-mobilization call with owner; access confirmed; power on-site. GPS: {lat:.5f}, {lon:.5f}",
                f"Crew on-site 07:00; pad graded; safety tailgate. Pilot hole advanced to {min(depth, rnd.randint(80,depth))} ft; cuttings: sand/gravel lenses.",
                f"Casing set {casing} in; cemented to surface. Screens sized per sieve analysis; development with surge & airlift.",
                f"Pump install {pump} HP; drop pipe sch40; wiring pulled and megger-tested. Chlorination completed.",
                f"Step test 4x60min up to {flow} GPM; constant-rate 8h @ {flow} GPM. Static {static} ft; drawdown stabilized {draw} ft.",
                "Panel inspection: voltage within spec; pressure switch set; relief tested. Discharge clear after 20 min.",
            ]
            for i, n in enumerate(notes):
                when = datetime.datetime.combine(today, datetime.time(8,0)) + datetime.timedelta(hours=2*i)
                cur.execute("INSERT INTO job_notes(job_id,body,created_at) VALUES(?,?,?)", (jid, n, str(when)))

            job_no += 1

    c.commit(); c.close()

@app.get("/")
def index():
    return render_template("index.html", maptiler_key=os.getenv("MAPTILER_KEY",""))

@app.get("/customers")
def customers_index():
    c=db();cur=c.cursor();cur.execute("SELECT * FROM customers ORDER BY name")
    rows=[dict(r) for r in cur.fetchall()]; c.close()
    return render_template("customers.html", customers=rows)

@app.get("/customer/<int:cid>")
def customer_detail(cid):
    c=db();cur=c.cursor()
    cur.execute("SELECT * FROM customers WHERE id=?", (cid,)); customer=cur.fetchone()
    if not customer: c.close(); abort(404)
    cur.execute("SELECT * FROM sites WHERE customer_id=? ORDER BY name", (cid,))
    sites=[dict(r) for r in cur.fetchall()]; c.close()
    return render_template("customer_detail.html", customer=dict(customer), sites=sites)

@app.get("/site/<int:site_id>")
def site_detail(site_id):
    c=db();cur=c.cursor()
    cur.execute("SELECT sites.*, customers.name as customer FROM sites JOIN customers ON customers.id=sites.customer_id WHERE sites.id=?", (site_id,))
    site=cur.fetchone()
    if not site: c.close(); abort(404)
    cur.execute("SELECT * FROM jobs WHERE site_id=? ORDER BY job_number", (site_id,))
    jobs=[dict(r) for r in cur.fetchall()]; c.close()
    return render_template("site_detail.html", site=dict(site), jobs=jobs)

@app.get("/jobs", endpoint="jobs_index")
def jobs_index():
    c=db(); cur=c.cursor()
    cur.execute(
        "SELECT jobs.id as job_id, jobs.job_number, jobs.job_category, "
        "sites.id as site_id, sites.name as site_name, "
        "customers.id as customer_id, customers.name as customer_name "
        "FROM jobs "
        "JOIN sites ON sites.id = jobs.site_id "
        "JOIN customers ON customers.id = sites.customer_id "
        "ORDER BY CAST(jobs.job_number AS INTEGER)"
    )
    rows = [dict(r) for r in cur.fetchall()]
    c.close()
    return render_template("jobs.html", jobs=rows)

@app.get("/site/<int:site_id>/job/<int:job_id>")
def job_detail(site_id,job_id):
    order = request.args.get("order","desc").lower()
    if order not in ("asc","desc"): order="desc"
    c=db();cur=c.cursor()
    cur.execute("SELECT * FROM jobs WHERE id=?", (job_id,)); job=cur.fetchone()
    if not job or job["site_id"]!=site_id: c.close(); abort(404)
    cur.execute("SELECT sites.*, customers.name as customer FROM sites JOIN customers ON customers.id=sites.customer_id WHERE sites.id=?", (site_id,))
    site=cur.fetchone()
    cur.execute("SELECT * FROM job_notes WHERE job_id=? ORDER BY datetime(created_at) {}".format("ASC" if order=="asc" else "DESC"), (job_id,))
    notes=[dict(r) for r in cur.fetchall()]; c.close()
    return render_template("job_detail.html", site=dict(site), job=dict(job), notes=notes)

@app.post("/api/site_create")
def api_site_create():
    data = request.get_json(force=True, silent=True) or {}
    required = ("customer_id","name")
    if not all(k in data and str(data[k]).strip() for k in required):
        return ("Missing required fields", 400)
    try:
        cid = int(data.get("customer_id"))
        name = str(data.get("name")).strip()
        desc = str(data.get("description") or "").strip()
        lat = float(data.get("latitude") or 0.0)
        lng = float(data.get("longitude") or 0.0)
    except Exception:
        return ("Bad payload", 400)
    c=db();cur=c.cursor()
    cur.execute("SELECT id FROM customers WHERE id=?", (cid,))
    if not cur.fetchone(): c.close(); return ("Customer not found", 404)
    cur.execute("INSERT INTO sites(customer_id,name,description,latitude,longitude) VALUES(?,?,?,?,?)",
                (cid, name, desc, lat, lng))
    site_id = cur.lastrowid
    c.commit(); c.close()
    return jsonify({"ok":True, "site_id": site_id})

@app.get("/api/customers")
def api_customers():
    c=db();cur=c.cursor();cur.execute("SELECT id,name FROM customers ORDER BY name")
    rows=[dict(r) for r in cur.fetchall()]; c.close()
    return jsonify(rows)

@app.get("/api/sites_for")
def api_sites_for():
    cid = request.args.get("customer_id")
    if not cid: return jsonify([])
    c=db();cur=c.cursor();cur.execute("SELECT id,name FROM sites WHERE customer_id=? ORDER BY name",(cid,))
    rows=[dict(r) for r in cur.fetchall()]; c.close()
    return jsonify(rows)

@app.get("/api/jobs_for")
def api_jobs_for():
    sid = request.args.get("site_id")
    if not sid: return jsonify([])
    c=db();cur=c.cursor();cur.execute("SELECT id,job_number FROM jobs WHERE site_id=? ORDER BY job_number",(sid,))
    rows=[dict(r) for r in cur.fetchall()]; c.close()
    return jsonify(rows)

@app.get("/api/sites")
def api_sites():
    q = (request.args.get("q") or "").strip()
    customer = (request.args.get("customer") or "").strip()
    category = (request.args.get("category") or "").strip()

    c=db();cur=c.cursor()
    sql = (
      "SELECT DISTINCT sites.*, customers.name as customer "
      "FROM sites "
      "JOIN customers ON customers.id = sites.customer_id "
      "LEFT JOIN jobs ON jobs.site_id = sites.id "
    )
    params, wh = [], []

    if customer:
        wh.append("customers.name = ?"); params.append(customer)
    if category:
        wh.append("jobs.job_category = ?"); params.append(category)
    if q:
        like = f"%{q}%"
        wh.append("(customers.name LIKE ? OR sites.name LIKE ? OR sites.description LIKE ? "
                  "OR jobs.job_number LIKE ? OR jobs.description LIKE ? "
                  "OR EXISTS(SELECT 1 FROM job_notes jn JOIN jobs j2 ON j2.id=jn.job_id AND j2.site_id=sites.id WHERE jn.body LIKE ?))")
        params += [like, like, like, like, like, like]
    if wh: sql += " WHERE " + " AND ".join(wh)
    sql += " ORDER BY customers.name, sites.name"
    cur.execute(sql, params)
    rows=[dict(r) for r in cur.fetchall()]; c.close()
    return jsonify(rows)

@app.get("/healthz")
def healthz(): 
    return "ok"

@app.errorhandler(404)
def nf(e): 
    return ("Not found", 404)

@app.errorhandler(500)
def ie(e): 
    return ("Internal error", 500)

if __name__ == "__main__":
    ensure_schema(); seed_data()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT","5000")))
else:
    ensure_schema(); seed_data()
