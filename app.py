
import os, sqlite3, random, datetime
from flask import Flask, render_template, request, jsonify, abort

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "wellatlas.db")

app = Flask(__name__)

def db():
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
    if cur.fetchone()[0] > 0: c.close(); return

    last_names = ["Washington","Adams","Jefferson","Madison","Monroe","Jackson","Lincoln","Grant","Roosevelt","Kennedy","Reagan","Clinton","Obama","Trump","Biden"]
    suffixes = [" Farms"," Ranch"," Dairy"," Cattle Co."," Orchards"," Vineyards"]
    # Ensure uniqueness and believable ag names, and explicitly include Trump
    rng = random.Random(42)
    customers = []
    used = set()
    for ln in last_names:
        for _ in range(2):  # try two variants per last name to build a decent list
            name = ln + rng.choice(suffixes)
            if name in used:
                continue
            used.add(name); customers.append(name)
        if len(customers) >= 20:
            break
    if not any("Trump" in n for n in customers):
        customers.append("Trump Ranch")

    mining_sites = ["Mother Lode","Prospector's Claim","Stamp Mill","Ore Vein","Pay Dirt","Hydraulic Pit","Tailings Pile","Mine Shaft","Pan Creek","Drift Tunnel","Headframe","Sluice Box","Bedrock Bend","Quartz Ridge","Assay Flats","Nugget Gulch","Pickaxe Point","Rocker Reach","Gold Pan Flat","Tailrace Trail"]

    job_no = 25001
    today = datetime.date.today()

    def rand_phone(r):
        return f"(530) {r.randint(200,999)}-{r.randint(1000,9999)}"

    r = rng
    for cust in customers[:20]:
        cur.execute("INSERT INTO customers(name,address,phone,email,notes) VALUES(?,?,?,?,?)",
                    (cust, f"{r.randint(120,899)} County Rd, North State, CA",
                     rand_phone(r), f"office@{cust.split()[0].lower()}.example",
                     "Account: net-30; contact via main line. Water use: irrigation & domestic. Priority: seasonal."))
        cid = cur.lastrowid

        for sname in r.sample(mining_sites, k=5):  # 5 sites per customer
            lat = 39.9 + r.uniform(-0.35,0.35)
            lon = -122.0 + r.uniform(-0.35,0.35)
            sdesc = f"{sname} block; access via farm road; soils: alluvium/gravel. Power nearby; backflow required."
            cur.execute("INSERT INTO sites(customer_id,name,description,latitude,longitude) VALUES(?,?,?,?,?)",
                        (cid, sname, sdesc, lat, lon))
            sid = cur.lastrowid

            # 1–2 jobs per site
            for _ in range(r.randint(1,2)):
                cat = r.choice(["Domestic","Drilling","Ag","Electrical"])
                depth = r.choice([160,200,240,280,320,360,400])
                casing = r.choice([4,6,8])
                pump = r.choice([3,5,7.5,10,15])
                flow = r.choice([20,30,40,55,70])
                static = r.choice([25,35,45,55,65])
                draw = r.choice([6,10,14,18,22])
                status = r.choice(["Scheduled","In Progress","Complete"])

                jdesc = (f"{cat} scope: drill to ~{depth} ft, set {casing} in steel casing with screens per sieve; "
                         f"install {pump} HP pump; expected yield {flow} GPM. Static {static} ft, drawdown {draw} ft. "
                         "Deliverables: as-built, GPS, pump curve, bacteriological test, start-up checklist.")
                cur.execute(
                    "INSERT INTO jobs(site_id,job_number,job_category,description,depth_ft,casing_diameter_in,pump_hp,flow_rate_gpm,static_level_ft,drawdown_ft,install_date,status) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (sid, str(job_no), cat, jdesc, depth, casing, pump, flow, static, draw, str(today), status)
                )
                jid = cur.lastrowid

                # Rich notes (8 entries)
                times = [datetime.datetime.combine(today, datetime.time(7,30)) + datetime.timedelta(hours=i*1.5) for i in range(8)]
                bodies = [
                    f"Kickoff with owner; easements confirmed; utility locates requested. GPS {lat:.5f}, {lon:.5f}.",
                    f"MOB complete; rig set; pilot advanced to {min(depth, r.randint(80, depth))} ft. Cuttings: sandy gravel; occasional clay seams.",
                    f"Casing {casing} in set; annular seal placed; screens matched to gradation.",
                    f"Development: surge + airlift; turbidity trending down; conductivity stable.",
                    f"Pump {pump} HP installed; drop pipe schedule 40; electrical insulation tested (megger OK).",
                    f"Step test up to {flow} GPM; constant-rate 6h at duty flow; static {static} ft; drawdown {draw} ft.",
                    "Panel verification: voltage within spec; pressure switch & VFD settings recorded.",
                    "Disinfection & flush complete; bacteriological sample submitted to lab; as-built drafted."
                ]
                for t, b in zip(times, bodies):
                    cur.execute("INSERT INTO job_notes(job_id,body,created_at) VALUES(?,?,?)", (jid, b, str(t)))

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

@app.get("/site/<int:site_id>/job/<int:job_id>")
def job_detail(site_id,job_id):
    c=db();cur=c.cursor()
    cur.execute("SELECT * FROM jobs WHERE id=?", (job_id,)); job=cur.fetchone()
    if not job or job["site_id"]!=site_id: c.close(); abort(404)
    cur.execute("SELECT sites.*, customers.name as customer FROM sites JOIN customers ON customers.id=sites.customer_id WHERE sites.id=?", (site_id,))
    site=cur.fetchone()
    cur.execute("SELECT * FROM job_notes WHERE job_id=? ORDER BY datetime(created_at) DESC", (job_id,))
    notes=[dict(r) for r in cur.fetchall()]; c.close()
    return render_template("job_detail.html", site=dict(site), job=dict(job), notes=notes)

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

@app.get("/api/sites")
def api_sites():
    q = (request.args.get("q") or "").strip()
    customer = (request.args.get("customer") or "").strip()
    category = (request.args.get("category") or "").strip()
    site_id = (request.args.get("site_id") or "").strip()

    c=db();cur=c.cursor()
    sql = (
      "SELECT DISTINCT sites.*, customers.name as customer "
      "FROM sites "
      "JOIN customers ON customers.id = sites.customer_id "
      "LEFT JOIN jobs ON jobs.site_id = sites.id "
    )
    params, wh = [], []

    if site_id:
        wh.append("sites.id = ?"); params.append(site_id)
    if customer:
        wh.append("customers.name = ?"); params.append(customer)
    if category:
        wh.append("jobs.job_category = ?"); params.append(category)
    if q:
        like = f"%{q}%"
        wh.append("(customers.name LIKE ? OR sites.name LIKE ? OR sites.description LIKE ? OR jobs.job_number LIKE ? OR jobs.description LIKE ?)")
        params += [like, like, like, like, like]

    if wh: sql += " WHERE " + " AND ".join(wh)
    sql += " ORDER BY customers.name, sites.name"
    cur.execute(sql, params)
    rows=[dict(r) for r in cur.fetchall()]; c.close()
    return jsonify(rows)

@app.get("/healthz")
def healthz(): return "ok"

if __name__ == "__main__":
    ensure_schema(); seed_data()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT","5000")))
else:
    ensure_schema(); seed_data()
