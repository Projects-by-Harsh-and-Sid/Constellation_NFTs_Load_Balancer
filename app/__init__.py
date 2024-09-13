
import os
from flask import Flask, request, jsonify

from flask_cors import CORS

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}

SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'chatwithme')
CHAT_URL = os.environ.get('CHAT_URL', 'http://localhost:8000/query')
MASTER_API_KEY = os.environ.get('MASTER_API_KEY', '1234567890')



app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = SECRET_KEY
app.config['CHAT_URL'] = CHAT_URL
app.config['MASTER_API_KEY'] = MASTER_API_KEY
app.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS
app.config['API_KEYS'] = {}
app.config['CHAT_SESSIONS'] = {}




from app import routes

