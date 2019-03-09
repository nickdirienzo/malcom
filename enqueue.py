import datetime

from flask import g, request, Flask, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
import py_nextbus
import requests

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/malcom.db'
db = SQLAlchemy(app)


class Stop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tag = db.Column(db.String, nullable=False)
    route_tag = db.Column(db.String, nullable=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    stop_tag = db.Column(db.String, nullable=False)
    vehicle_id = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)

client = py_nextbus.NextBusClient(output_format='json')
client.agency = "sf-muni"

stops_to_listeners = {}
stops_to_routes = {}

def load_stops(clipper_url):
    route_config = client.get_route_config()
    routes = route_config['route']
    for route in routes:
        for stop in route['stop']:
            stops_to_listeners[stop['tag']] = clipper_url
            stops_to_routes[stop['tag']] = route['tag']
            s = Stop(tag=stop['tag'], route_tag=route['tag'])
            db.session.add(s)
    db.session.commit()
    return stops_to_listeners


@app.route('/board', methods=['POST'])
def board_bus():
    content = request.json['message']
    stop_tag = str(request.json['stop'])
    stop = Stop.query.filter_by(tag=stop_tag).first()
    if stop is None:
        abort(400)

    response = requests.get('http://webservices.nextbus.com/service/publicJSONFeed?command=predictions&a=sf-muni&s={}&r={}'.format(
        stop_tag,
        stop.route_tag
    ))
    predictions = response.json()['predictions']['direction']['prediction']
    bus_departing = False
    for prediction in predictions:
        minutes = int(prediction['minutes'])
        # There's a bus departing. Enqueue.
        if minutes < 1:
            bus_departing = True
            message = Message(
                content=content,
                stop_tag=stop,
                vehicle_id=prediction['vehicle']
            )
            db.session.add(message)
            db.session.commit()
            return jsonify({'vehicle_id': message.vehicle_id, 'boarded_at': message.created_at})

    if bus_departing is False:
        return jsonify({'next_bus': {'minutes': predictions[0]['minutes'], 'seconds': predictions[0]['seconds']}}), 503


