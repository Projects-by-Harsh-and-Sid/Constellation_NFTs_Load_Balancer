from functools import wraps
import datetime
import secrets
import jwt
from flask import request, jsonify

from app import app


#  to be replace by reddis or on chain session management storage
api_keys            = app.config['API_KEYS'] 
chat_sessions       = app.config['CHAT_SESSIONS']
SECRET_KEY          = app.config['SECRET_KEY']
ALLOWED_EXTENSIONS  = app.config['ALLOWED_EXTENSIONS']
MASTER_API_KEY      = app.config['MASTER_API_KEY']

import PyPDF2

UPLOAD_FOLDER = app.config['UPLOAD_FOLDER']

def generate_api_key():
    return secrets.token_urlsafe(32)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def api_key_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or (api_key not in api_keys and api_key != MASTER_API_KEY):
            return jsonify({'message': 'Invalid API key'}), 401
        return f(*args, **kwargs)
    return decorated

def generate_jwt_token(api_key):
    payload = {
        'api_key': api_key,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            api_key = data['api_key']
            if api_key not in api_keys:
                return jsonify({'message': 'Invalid session'}), 401
        except:
            return jsonify({'message': 'Token is invalid'}), 401
        return f(api_key, *args, **kwargs)
    return decorated