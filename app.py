
from flask import Flask, render_template, request, redirect, url_for, session
from flask import Flask, render_template, request, redirect, url_for, session
from flask_login import LoginManager
from dotenv import load_dotenv
import os, requests

from models import db, User, Match, Market, Tip

app = Flask(__name__)

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

@app.route("/")
def home():
   # auto_close_matches()

    subscribed = session.get("subscribed", False)

    matches = []
    if subscribed:
        matches = Match.query.filter_by(is_active=True).all()

    return render_template(
        "index.html",
        matches=matches,
        subscribed=subscribed
    )


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


if PESAPAL_ENV == "sandbox":
    AUTH_URL = "https://cybqa.pesapal.com/pesapalv3/api/Auth/RequestToken"
else:
    AUTH_URL = "https://pay.pesapal.com/v3/api/Auth/RequestToken"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)



