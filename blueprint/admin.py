from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from pip._internal import req

import config
from ext import csrf, db
from model import Payment

app = Blueprint('admin', __name__)


@app.before_request
def br():
    if 'admin' not in session and request.endpoint != "admin.login":
        return redirect(url_for('admin.login'))


@app.route('/login', methods=['GET', "POST"])
def login():
    if request.method == "GET":
        return render_template('admin/login.html')
    else:
        username = request.form.get("username")
        password = request.form.get("password")

        if username == config.ADMIN_USERNAME and \
                password == config.ADMIN_PASSWORD:
            session['admin'] = username

        return redirect(url_for('admin.dashboard'))


@app.route('/dashboard', methods=['GET'])
def dashboard():
    return render_template('admin/dashboard.html')


@app.route('/get-donations', methods=['POST'])
@csrf.exempt
def get_donations():
    offset = int(request.json.get('offset', 0))
    newest_donation_time_created = str(request.json.get('check_new_donation', 0))

    limit = 10

    if newest_donation_time_created != "-1":
        pays = Payment.query.filter(Payment.refid != None,
                                    Payment.time_created > newest_donation_time_created).order_by(
            Payment.id.asc()).limit(limit).all()
    else:
        pays = Payment.query.filter(Payment.refid != None).order_by(
            Payment.id.desc()).offset(offset).limit(limit).all()

    return jsonify(
        [
            pay.to_dict()
            for pay in pays
        ]
    )


@app.route('/replay-donation', methods=['POST'])
@csrf.exempt
def replay():
    id = request.json.get('id')

    pay = Payment.query.filter(Payment.id == id).first()
    pay.shown_in_live_stream = False
    db.session.commit()

    return jsonify(
        {
            "status": "ok"
        }
    )
