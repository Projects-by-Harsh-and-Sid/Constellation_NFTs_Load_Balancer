from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return "https://127.0.0.1:5000"

if __name__ == '__main__':
    app.run(port=5996,debug=True,host='0.0.0.0')