
from flask import Flask, render_template, request, redirect, url_for, session
from flask import Flask, render_template, request, redirect, url_for, session
from flask_login import LoginManager
from dotenv import load_dotenv
import os, requests

from models import db, User, Match, Market, Tip

app = Flask(__name__)
PESAPAL_ENV = os.getenv("PESAPAL_ENV", "sandbox")

app.config["SECRET_KEY"] = "supersecret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///game_on_tips.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

load_dotenv()


PESAPAL_CONSUMER_KEY = os.getenv("gFgd8p32X38EdnBUbwx6fIwKGTsO36db")
PESAPAL_CONSUMER_SECRET = os.getenv("KhEhrvluXyrpSgZ7eLGciBbKiHQ=")

def get_pesapal_token():
    payload = {
        "consumer_key": PESAPAL_CONSUMER_KEY,
        "consumer_secret": PESAPAL_CONSUMER_SECRET
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    r = requests.post(AUTH_URL, json=payload, headers=headers)
    data = r.json()

    print("TOKEN RESPONSE:", data)

    if "access_token" not in data:
        raise Exception("Pesapal auth failed. Check keys + environment.")

    return data["access_token"]


#Routes
def auto_close_matches():
    # TODO: implement logic later
    pass

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/ordinary")
def ordinary():
    if not session.get("subscribed"):
        return redirect("/subscribe?plan=ordinary")
    return render_template("ordinary.html")


@app.route("/vip")
def vip():
    if not session.get("subscribed"):
        return redirect("/subscribe?plan=vip")
    return render_template("vip.html")


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if not session.get("admin"):
        return redirect("/admin/login")

    if request.method == "POST":
        if request.form.get("type") == "match":
            match = Match(
                home_team=request.form["home_team"],
                away_team=request.form["away_team"],
                league=request.form["league"],
                kickoff_time=datetime.strptime(
                    request.form["kickoff_time"], "%Y-%m-%dT%H:%M"
                )
            )
            db.session.add(match)
            db.session.commit()

        elif request.form.get("type") == "market":
            market = Market(
                match_id=request.form["match_id"],
                market_name=request.form["market_name"],
                pick=request.form["pick"],
                odds=request.form["odds"]
            )
            db.session.add(market)
            db.session.commit()

    matches = Match.query.order_by(Match.kickoff_time.asc()).all()
    return render_template("admin.html", matches=matches)

@app.route("/admin/markets/create", methods=["GET", "POST"])
def create_market():
    if not session.get("admin"):
        return redirect("/admin/login")

    matches = Match.query.order_by(Match.kickoff_time.asc()).all()

    if request.method == "POST":
        market = Market(
            match_id=request.form["match_id"],
            market_name=request.form["market_name"],
            pick=request.form["pick"],
            odds=float(request.form["odds"])
        )
        db.session.add(market)
        db.session.commit()

        return redirect("/admin/markets")

    return render_template("create_market.html", matches=matches)

@app.route("/admin/markets")
def admin_markets():
    if not session.get("admin"):
        return redirect("/admin/login")

    markets = Market.query.order_by(Market.created_at.desc()).all()
    return render_template("admin_markets.html", markets=markets)

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


@app.route("/subscribe")
def subscribe():
    plan = request.args.get("plan")
    if plan not in ["ordinary", "vip"]:
        return "Invalid plan", 400

    prices = {
        "ordinary": 30000,
        "vip": 50000
    }

    return render_template(
        "subscribe.html",
        plan=plan,
        amount=prices[plan],
        public_key=FLW_PUBLIC_KEY
    )

@app.route("/admin/toggle/<int:match_id>")
def toggle_match(match_id):
    if not session.get("admin"):
        return redirect("/admin/login")

    match = Match.query.get_or_404(match_id)
    match.is_active = not match.is_active
    db.session.commit()
    return redirect("/admin")


@app.route("/verify-payment")
def verify_payment():
    tx_id = request.args.get("tx_id")
    plan = request.args.get("plan")

    headers = {
        "Authorization": f"Bearer {FLW_SECRET_KEY}"
    }

    response = requests.get(
        f"https://api.flutterwave.com/v3/transactions/{tx_id}/verify",
        headers=headers
    )

    data = response.json()

    if (
        data["status"] == "success"
        and data["data"]["status"] == "successful"
    ):
        session["subscribed"] = True
        session["plan"] = plan
        return redirect("/")

    return "Payment failed", 400

def register_ipn():
    token = get_pesapal_token()

    url = "https://pay.pesapal.com/v3/api/URLSetup/RegisterIPN"
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
    print("✅ IPN REGISTERED:", data)

    return data["ipn_id"]


# =========================
# ENVIRONMENT CONFIG
# =========================
import os

PESAPAL_ENV = os.getenv("PESAPAL_ENV", "sandbox")

if PESAPAL_ENV == "sandbox":
    AUTH_URL = "https://cybqa.pesapal.com/pesapalv3/api/Auth/RequestToken"
else:
    AUTH_URL = "https://pay.pesapal.com/v3/api/Auth/RequestToken"


# =========================
# COMING SOON MODE
# =========================
COMING_SOON = True  # change to False when ready
@app.route("/")
def index():
    return """
<!DOCTYPE html>
<html>
<head>
<title>Game On Tips</title>
<style>
    body {
        margin: 0;
        background: #0b0f0c;
        color: #00ff66;
        font-family: Arial, sans-serif;
    }

    nav {
        padding: 10px 20px;
        border-bottom: 1px solid #00ff66;
    }

    nav a {
        color: #00ff66;
        margin-right: 15px;
        text-decoration: none;
        font-size: 14px;
    }

    .container {
        max-width: 1000px;
        margin: 40px auto;
        border: 1px solid #00ff66;
        padding: 40px;
        border-radius: 10px;
        box-shadow: 0 0 20px #00ff6655;
    }

    h1 {
        text-align: center;
        margin-bottom: 5px;
    }

    .status {
        text-align: center;
        color: #7fffaf;
        font-size: 14px;
        margin-bottom: 30px;
    }

    .cards {
        display: flex;
        gap: 40px;
        justify-content: center;
    }

    .card {
        width: 300px;
        padding: 25px;
        border-radius: 10px;
        border: 2px solid #00ff66;
        text-align: center;
        box-shadow: 0 0 15px #00ff6640;
    }

    .vip {
        border-color: #ffff00;
        box-shadow: 0 0 15px #ffff0040;
        color: #ffffaa;
    }

    .card h2 {
        margin-bottom: 10px;
    }

    .card p {
        font-size: 14px;
        color: #aaffcc;
    }

    .vip p {
        color: #ffffcc;
    }

    .btn {
        margin-top: 15px;
        padding: 10px 20px;
        background: transparent;
        border: 1px solid #00ff66;
        color: #00ff66;
        cursor: pointer;
        border-radius: 6px;
    }

    .vip .btn {
        border-color: #ffff00;
        color: #ffff00;
    }

    .btn:hover {
        background: #00ff6620;
    }

    .locked {
        margin-top: 40px;
        padding: 15px;
        border: 1px dashed #00ff66;
        text-align: center;
        color: #7fffaf;
        font-size: 13px;
    }
</style>
</head>

<body>

<nav>
    <a href="/">Home</a>
    <a href="/subscribe/ordinary">Ordinary Tips</a>
    <a href="/subscribe/vip">VIP Tips</a>
    <a href="/admin">Admin</a>
</nav>

<div class="container">
    <h1>Game On Tips</h1>
    <div class="status">System running successfully.</div>

    <div class="cards">
        <div class="card">
            <h2>Ordinary Tips</h2>
            <p>Reliable daily tips for consistent wins.</p>
            <form action="/subscribe/ordinary">
                <button class="btn">Subscribe</button>
            </form>
        </div>

        <div class="card vip">
            <h2>VIP Tips</h2>
            <p>High-confidence expert predictions.</p>
            <form action="/subscribe/vip">
                <button class="btn">Go VIP</button>
            </form>
        </div>
    </div>

    <div class="locked">
        🔒 Upcoming Matches Locked<br>
        Subscribe to view upcoming matches and predictions.
    </div>
</div>

</body>
</html>
"""

@app.route("/subscribe/ordinary")
def ordinary_coming_soon():
    return """
    <html>
    <head>
    <title>Ordinary – Coming Soon</title>
    <style>
        body {
            background: #0b0f0c;
            color: #00ff66;
            font-family: Arial;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            text-align: center;
        }
    </style>
    </head>
    <body>
        <div>
            <h1>🎮 Ordinary Tips</h1>
            <p>Coming soon.</p>
        </div>
    </body>
    </html>
    """
@app.route("/subscribe/vip")
def vip_coming_soon():
    return """
    <html>
    <head>
    <title>VIP – Coming Soon</title>
    <style>
        body {
            background: #0b0f0c;
            color: #ffff00;
            font-family: Arial;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            text-align: center;
        }
    </style>
    </head>
    <body>
        <div>
            <h1>🚀 VIP Tips</h1>
            <p>Coming soon.</p>
        </div>
    </body>
    </html>
    """

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

