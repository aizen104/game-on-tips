from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    home_team = db.Column(db.String(50))
    away_team = db.Column(db.String(50))
    league = db.Column(db.String(50))
    kickoff_time = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

class Market(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("match.id"), nullable=False)

    market_name = db.Column(db.String(100))
    pick = db.Column(db.String(50))
    odds = db.Column(db.Float)
    status = db.Column(db.String(20), default="pending")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    match = db.relationship("Match", backref="markets")

class Tip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("match.id"))
    market_type = db.Column(db.String(50))
    market_detail = db.Column(db.String(50))
    pick = db.Column(db.String(50))
    odds = db.Column(db.Float)
    plan = db.Column(db.String(20))  # vip / ordinary
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

