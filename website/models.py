from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    phone = db.Column(db.String(150))
    histories = db.relationship('History')
    farms = db.relationship('Farm')
    
class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    img = db.Column(db.LargeBinary, nullable=False)
    name = db.Column(db.Text, nullable=False)
    mimetype = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime(timezone=True), default=func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    label = db.Column(db.String(150))
    conf = db.Column(db.String(150))
    
class Farm(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    state = db.Column(db.String(150))
    city = db.Column(db.String(150))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

