import secrets
import time

import requests
from flask import Blueprint, render_template, request, redirect, flash, session, url_for, abort

import config
from ext import db
from model import Payment

app = Blueprint('main', __name__)

sent_verify_codes = {}


@app.route('/')
def index():
    def nearest_multiple(x, multiple):
        remainder = x % multiple
        if remainder > multiple / 2:
            return x - remainder
        else:
            return x + remainder

    def find_midpoint(x, y):
        return nearest_multiple(int(((x + y) / 2)), 10000)

    suggestions = config.AMOUNT_SUGGESTIONS
    if len(suggestions) == 0:
        suggestions = [
            config.MIN_AMOUNT,
            find_midpoint(config.MIN_AMOUNT, find_midpoint(config.MIN_AMOUNT, config.MAX_AMOUNT)),
            find_midpoint(config.MAX_AMOUNT, find_midpoint(config.MIN_AMOUNT, config.MAX_AMOUNT)),
            config.MAX_AMOUNT
        ]

    return render_template('main.html', config=config, amount_suggestions=suggestions)


@app.route('/pay', methods=['POST', 'GET'])
def pay():
    if request.method == "GET":
        payid = request.args.get('payment')
        pay = Payment.query.filter(Payment.id == payid).first_or_404()
        phone = pay.phone
        amount = pay.amount

    else:
        amount = int(request.form.get("amount"))
        name = request.form.get("name")
        phone = request.form.get("phone")
        description = request.form.get("description")
        show_in_livestream = True if request.form.get("show_in_livestream") != None else False
        show_desc_in_livestream = True if request.form.get("show_desc_in_livestream") != None else False
        show_in_list = True if request.form.get("show_in_list") != None else False

        if config.MIN_AMOUNT > amount or config.MAX_AMOUNT < amount \
                or not name \
                or not description \
                or not phone \
                or not len(phone) == 11 \
                or not phone.startswith('09'):
            return redirect('/')

        pay = Payment(
            amount=amount,
            name=name,
            phone=phone,
            description=description,
            show_in_livestream=show_in_livestream,
            show_desc_in_livestream=show_desc_in_livestream,
            show_in_list=show_in_list,
            gateway="zarinpal"
        )

        db.session.add(pay)
        db.session.commit()

    if session.get("phone") != phone:
        return redirect(url_for('main.verify_phone', payment=pay.id, phone=phone))

    token_request = requests.post(
        "https://payment.zarinpal.com/pg/v4/payment/request.json",
        json={
            "merchant_id": config.GATEWAY_MERCHANT_ID,
            "amount": amount * 10,
            "description": f"payment id : {pay.id}",
            "callback_url": config.GATEWAY_CALLBACK_URL,
            "metadata": {
                "mobile": phone,
            }
        },
        headers={
            "accept": 'application/json',
            "ContentType": 'application/json'
        }
    )
    token_request = token_request.json()
    if 'code' in token_request['data'] and token_request['data']['code'] == 100:
        pay.auth = token_request['data']['authority']
        db.session.commit()
        return redirect(f"https://payment.zarinpal.com/pg/StartPay/{token_request['data']['authority']}")

    return redirect('/')


@app.route('/verify')
def verify():
    auth = request.args.get('Authority')
    status = request.args.get('Status')

    if status == "NOK":
        return render_template('result.html', status="error", msg="پرداخت با خطا رو به رو شد")

    pay = Payment.query.filter(Payment.auth == auth).first_or_404()

    verify_request = requests.post(
        "https://payment.zarinpal.com/pg/v4/payment/verify.json",
        data={
            "merchant_id": config.GATEWAY_MERCHANT_ID,
            "amount": pay.amount * 10,
            "authority": auth
        },
        headers={
            "accept": 'application/json',
            "ContentType": 'application/json'
        }
    )

    verify_request = verify_request.json()
    if 'code' in verify_request['data'] and verify_request['data']['code'] in [100, 101]:

        pay.refid = verify_request['data']['ref_id']
        db.session.commit()

        return render_template('result.html', status="success",
                               payment=pay)


    else:
        return render_template('result.html', status="error",
                               msg="پرداخت با خطا رو به رو شد. در صورت کسر مبلغ از حساب شما، تا 72 ساعت بعد به حساب شما برگشت داده خواهد شد")


def send_otp(phone, verify_code):
    requests.post("http://edge.ippanel.com/v1/api/send",
                  headers={'Content-Type': 'application/json',
                           'ACCEPT': 'application/json',
                           'Authorization': config.IPPANEL_AUTH},
                  json={
                      "sending_type": "pattern",
                      "from_number": "+983000505",
                      "code": "",
                      "recipients": [
                          str(phone)
                      ],
                      "params": {
                          "CODE": verify_code
                      }
                  }
                  )


@app.route('/verify-phone', methods=['GET', 'POST'])
def verify_phone():
    payment_id = request.args.get('payment')

    check_payment_exist = Payment.query.filter(Payment.id == payment_id, Payment.time_created < (time.time() - 1800)).first_or_404()

    if request.method == "GET":
        phone = request.args.get('phone')
        verify_code = secrets.randbelow(9000) + 1000

        if not phone or not verify_code:
            abort(404)

        if not phone in sent_verify_codes or \
                not (sent_verify_codes[phone]['expire_at'] > time.time()):
            sent_verify_codes[phone] = {"code": verify_code, "expire_at": int(time.time() + 300)}  # 5 mins
            send_otp(phone, verify_code)
            print(sent_verify_codes)

        return render_template('verify-phone.html', phone=phone)
    else:
        code = request.form.get('code')
        phone = request.form.get('phone')

        if phone in sent_verify_codes and \
                sent_verify_codes[phone]['code'] == int(code) and \
                sent_verify_codes[phone]['expire_at'] > time.time():

            session.permanent = True
            session['phone'] = phone
            return redirect(url_for('main.pay', payment=payment_id))
        else:
            return redirect(url_for('main.verify_phone', phone=phone, payment_id=payment_id))

