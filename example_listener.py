import flask

app = flask.Flask(__name__)

@app.route('/incoming', methods=['POST'])
def incoming():
    print(flask.request.json)
    return ''
