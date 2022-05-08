import re
import json
import pymysql
import os
import time
import pymongo
import secrets

from flask import Flask, render_template, request, Response, stream_with_context, flash, make_response, session
from flask_bootstrap import Bootstrap
# from flask_socketio import SocketIO, emit
from random import random
from utils import logger
from pytz import timezone
from streamer import RaonStreamer
from datetime import timedelta

# Fetch common configuration properties.
# When you modify config, you have to modify config.json

with open('config.json') as config_file:
    config_data = json.load(config_file)

flask_settings = config_data['flask_settings']
mysql_settings = config_data['mysql_settings']
mongo_settings = config_data['mongo_settings']

CAPTURE_PATH = flask_settings['CAPTURE_PATH']
SECRET_KEY = flask_settings['SECRET_KEY']
MYSQL_HOST = mysql_settings['MYSQL_HOST']
MYSQL_USER = mysql_settings['MYSQL_USER']
MYSQL_PASSWORD = mysql_settings['MYSQL_PASSWORD']
MYSQL_DB = mysql_settings['MYSQL_DB']
MYSQL_CHARSET = mysql_settings['MYSQL_CHARSET']
MONGO_HOST = mongo_settings['MONGO_HOST']
MONGO_DB = mongo_settings['MONGO_DB']
MONGO_COLLECTION = mongo_settings['MONGO_COLLECTION']

application = Flask(__name__)
secret_key_session = secrets.token_hex(16)
application.secret_key = secret_key_session

# Initialize CLASS file.
Bootstrap(application)
# socketio = SocketIO(application)
streamer = RaonStreamer()

# Global variables to maintain whole source.
userid = ""
stream_src = ""

def stream_gen(src, userid, timer):
    try:
        streamer.run(src)
        while True:
            frame = streamer.bytescode(userid, timer)
            timer += 1
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    except GeneratorExit:
        streamer.stop()

@application.before_request
def make_session_permanent():
    session.permanent = True
    application.permanent_session_lifetime = timedelta(minutes=10)


@application.route('/stream')
def stream():
    src = stream_src
    timer = 0
    try:
        return Response(stream_with_context(stream_gen(src, userid, timer)),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    except Exception as e:
        print('[FlaskServer] ', 'stream error : ', str(e))


@application.route('/')
def login():
    if 'id' in session:
        id = session['id']
        return render_template('index.html', msg=id)
    else:
        return render_template('login.html')

@application.route('/join', methods=['POST'])
def join():
    TITLE = 'Join Page'

    if request.method == 'POST':
        joinid = request.form['joinid']
        joinEmail = request.form['joinem']
        joinPassword = request.form['joinpw']
        str_result = ""
        dupcheck_sql = "SELECT * FROM raonzena.joininfo WHERE joinid = '{}'".format(str(joinid))

        try:
            connection = pymysql.connect(host=MYSQL_HOST, user=MYSQL_USER,
                             password=MYSQL_PASSWORD, db=MYSQL_DB, charset=MYSQL_CHARSET, autocommit=True)
            with connection.cursor() as curs:
                curs.execute(dupcheck_sql)
                result = curs.fetchall()
                str_result = str(result)
        except Exception as e:
                logger.info("join duplicate check error " + str(e))
        finally:
            connection.close()

        joinInsertQuery = "INSERT INTO raonzena.joininfo (joinid,joinem,joinpw) values ('{}','{}','{}')".format(joinid, joinEmail, joinPassword)

        if str_result == '()':
            try:
                connection = pymysql.connect(host=MYSQL_HOST, user=MYSQL_USER,
                             password=MYSQL_PASSWORD, db=MYSQL_DB, charset=MYSQL_CHARSET, autocommit=True)
                with connection.cursor() as curs:                    
                    curs.execute(joinInsertQuery)
                userFilepath = CAPTURE_PATH + joinid
                os.makedirs(userFilepath, exist_ok=True)
                connection.commit()
            except Exception as e:
                logger.info("insert error " + str(e))
                connection.rollback()
            finally:
                connection.close()
            flash('Congratulations!')
        else:
            flash('Your Name is already existed. Try Another Name!')

    return render_template("login.html")


@application.route('/login_check', methods=['GET'])
def login_check():
    TITLE = 'Login Check'
    joinIdByQuery = ""
    joinStreamByQuery = ""

    if request.method == 'GET':
        result = request.form

    joinid = request.args.get('loginid')
    joinpw = request.args.get('loginpw')
    streamByJoinId_SQL = "SELECT joinid, stream FROM raonzena.joininfo WHERE joinid = '{}' and joinpw = '{}'".format(joinid, joinpw)

    try:
        connection = pymysql.connect(host=MYSQL_HOST, user=MYSQL_USER,
                             password=MYSQL_PASSWORD, db=MYSQL_DB, charset=MYSQL_CHARSET, autocommit=True)
        with connection.cursor() as curs:
            curs.execute(streamByJoinId_SQL)
            result = curs.fetchone()
            joinIdByQuery = result[0]
            joinStreamByQuery = result[1]
    except Exception as e:
        logger.info("login check error " + str(e))
    finally:
        connection.close()

    if str(joinIdByQuery) != "":
        global userid
        global stream_src
        userid = joinIdByQuery
        stream_src = joinStreamByQuery
        session['id'] = userid
        # session['stream'] = stream_src
        return render_template('index.html', msg=joinid)
    else:
        flash('Your ID or Password is not correct!')
        return render_template('login.html', TITLE=TITLE)

@application.route('/gauge')
def live_data():
    mongo_client = pymongo.MongoClient(MONGO_HOST)
    mongo_db = mongo_client[MONGO_DB]
    mongo_collection = mongo_db[MONGO_COLLECTION]

    gauge_raon = mongo_collection.find().limit(1).sort([('$natural',-1)])
    for gauge in gauge_raon:
        temperature = gauge["tmp"]
        humidity = gauge["hum"]
    
    data = [time.time() * 1000, float(temperature), float(humidity)]
    response = make_response(json.dumps(data))
    response.content_type = 'application/json'
    return response

if __name__ == '__main__':
    application.run(host='0.0.0.0', port=5000, debug=True, threaded=True)