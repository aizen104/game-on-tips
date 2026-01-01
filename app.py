from flask import Flask, render_template, request, redirect, session, url_for
from flask_login import LoginManager
from dotenv import load_dotenv
from datetime import datetime
import os, requests

from models import db, User, Match, Market

# =========================
# APP SETUP
# =========================
app = Flask(__name__)
load_dotenv()


app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "supersecret")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///game_on_tips.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
print("ENV:", os.getenv("PESAPAL_ENV"))

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "admin_login"

# =========================
# PESAPAL CONFIG (AIRTEL)
# =========================
PESAPAL_ENV = os.getenv("PESAPAL_ENV", "sandbox")

if PESAPAL_ENV == "sandbox":
    AUTH_URL = "https://cybqa.pesapal.com/pesapalv3/api/Auth/RequestToken"
else:
    AUTH_URL = "https://pay.pesapal.com/v3/api/Auth/RequestToken"

PESAPAL_KEY = os.getenv("PESAPAL_KEY")
PESAPAL_SECRET = os.getenv("PESAPAL_SECRET")

PESAPAL_ENABLED = bool(PESAPAL_KEY and PESAPAL_SECRET)

def register_ipn():
    token = get_pesapal_token()

    url = "https://cybqa.pesapal.com/pesapalv3/api/URLSetup/RegisterIPN"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "url": "http://127.0.0.1:5000/pesapal/ipn",
        "ipn_notification_type": "POST"
    }

    r = requests.post(url, json=payload, headers=headers)
    r.raise_for_status()

    data = r.json()
    print("IPN REGISTERED:", data)

    return data["ipn_id"]

def get_pesapal_token():
    url = AUTH_URL

    payload = {
        "consumer_key": PESAPAL_CONSUMER_KEY.strip(),
        "consumer_secret": PESAPAL_CONSUMER_SECRET.strip()
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    r = requests.post(url, json=payload, headers=headers, timeout=15)

    print("STATUS:", r.status_code)
    print("RAW RESPONSE:", r.text)

    if r.status_code != 200:
        raise Exception("Pesapal auth failed")

    data = r.json()

    if "access_token" not in data:
        raise Exception(f"Unexpected response: {data}")

    return data["access_token"]


# =========================
# LOGIN
# =========================
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# =========================
# PUBLIC ROUTES
# =========================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ordinary")
def ordinary_page():
    if not session.get("subscribed") or session.get("plan") != "ordinary":
        return redirect("/subscribe/ordinary")

    matches = Match.query.filter_by(plan="ordinary", is_active=True).all()
    return render_template("ordinary.html", price=30000, matches=matches)

@app.route("/vip")
def vip_page():
    if not session.get("subscribed") or session.get("plan") != "vip":
        return redirect("/subscribe/vip")

    matches = Match.query.filter_by(plan="vip", is_active=True).all()
    return render_template("vip.html", price=50000, matches=matches)

# =========================
# SUBSCRIPTION
# =========================
@app.route("/subscribe/<plan>")
def subscribe(plan):
    if plan not in ["ordinary", "vip"]:
        return redirect("/")

    prices = {
        "ordinary": 30000,
        "vip": 50000
    }

    return render_template(
        "payment.html",
        plan=plan,
        amount=prices[plan]
    )

# =========================
# ADMIN
# =========================
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if not session.get("admin"):
        return redirect("/admin/login")

    if request.method == "POST":

        # ADD MATCH
        if request.form.get("add_match"):
            match = Match(
                home_team=request.form["home_team"],
                away_team=request.form["away_team"],
                league=request.form["league"],
                kickoff_time=datetime.strptime(
                    request.form["kickoff_time"], "%Y-%m-%dT%H:%M"
                ),
                plan=request.form["plan"]
            )
            db.session.add(match)
            db.session.commit()

        # ADD MARKET
        elif request.form.get("add_market"):
            market = Market(
                match_id=request.form["match_id"],
                market_type=request.form["market_type"],
                market_detail=request.form["market_detail"],
                odds=float(request.form["odds"])
            )
            db.session.add(market)
            db.session.commit()

    matches = Match.query.order_by(Match.kickoff_time.asc()).all()
    return render_template("admin.html", matches=matches)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        session["admin"] = True
        return redirect("/admin")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect("/")

@app.route("/admin/toggle/<int:match_id>")
def toggle_match(match_id):
    if not session.get("admin"):
        return redirect("/admin/login")

    match = Match.query.get_or_404(match_id)
    match.is_active = not match.is_active
    db.session.commit()
    return redirect("/admin")

# =========================
# PESAPAL PAYMENT PLACEHOLDERS
# =========================
@app.route("/pay/<plan>")
def pay(plan):
    if plan not in ["ordinary", "vip"]:
        return redirect("/")

    # Will redirect to Pesapal
    return "Pesapal payment coming here"

@app.route("/pesapal/ipn", methods=["POST"])
def pesapal_ipn():
    # Pesapal will hit this endpoint
    # Verify payment here
    # Then:
    session["subscribed"] = True
    session["plan"] = "vip"  # or ordinary from payload
    return "OK"

# =========================
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

