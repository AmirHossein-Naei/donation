from flask import Blueprint, render_template, request, jsonify
import config
from ext import csrf, db
from model import Payment

app = Blueprint('overlay', __name__)

csrf.exempt(app)


@app.route('/donation', methods=['GET', 'POST'])
def donation():
    if request.method == 'GET':
        return render_template('overlay/donation.html', DONATE_SOUND_URL=config.DONATE_SOUND_URL)
    else:
        pays = Payment.query.filter(Payment.refid != None, Payment.show_in_livestream == True,
                                    Payment.shown_in_live_stream == False).order_by(Payment.id.asc()).all()

        for pay in pays:
            pay.shown_in_live_stream = True
        db.session.commit()

        return jsonify(
            [
                {
                    "name": pay.name[0:20],
                    "description": pay.description if pay.show_desc_in_livestream else "",
                    "amount": pay.amount
                }
                for pay in pays
            ]
        )


@app.route('/recent-donors', methods=['GET', 'POST'])
def recent_donors():
    if request.method == 'GET':
        return render_template('overlay/recent-donors.html')
    else:
        pays = Payment.query.filter(Payment.refid != None, Payment.show_in_list == True).order_by(
            Payment.id.desc()).limit(10).all()

        return jsonify(
            [
                {
                    "name": pay.name[0:10],
                    "amount": pay.amount
                }
                for pay in pays
            ]
        )
