import collections
import datetime
import time

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

    def serialize(self):
        return {
            'id': self.id,
            'message': self.content,
            'vehicle_id': self.vehicle_id,
            'origin_stop': self.stop_tag,
        }

class Listener(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stop_tag = db.Column(db.String, nullable=False)
    url = db.Column(db.String, nullable=False)

client = py_nextbus.NextBusClient(output_format='json')
client.agency = "sf-muni"


def load_stops(clipper_url):
    route_config = client.get_route_config()
    routes = route_config['route']
    added_stops = set([])
    for route in routes:
        for stop in route['stop']:
            if stop['tag'] not in added_stops:
                listener = Listener(stop_tag=stop['tag'], url=clipper_url)
                db.session.add(listener)

                added_stops.add(stop['tag'])
                s = Stop(tag=stop['tag'], route_tag=route['tag'])
                db.session.add(s)
    db.session.commit()

@app.route('/messages/<int:message_id>')
def get_messages_by_id(message_id):
    messages = [Message.query.get(message_id)]
    route_tag = Stop.query.filter_by(tag=messages[0].stop_tag).first().route_tag

    vehicle_to_messages = collections.defaultdict(list)
    for message in messages:
        vehicle_to_messages[message.vehicle_id].append(message)

    messages_response = {'messages': []}
    include_location = True
    if include_location:
        routes = [route_tag]
        last_min_epoch = int(time.time()) - 60000
        responses = []
        for route in routes:
            responses.append(client.get_vehicle_locations(route, last_min_epoch))
        for response in responses:
            for vehicle in response.get('vehicle') or []:
                carried_messages = vehicle_to_messages[vehicle['id']]
                to_ret = []
                for msg in carried_messages:
                    msg_serialize = msg.serialize()
                    msg_serialize['lat'] = vehicle['lat']
                    msg_serialize['lon'] = vehicle['lon']
                    messages_response['messages'].append(msg_serialize)
    return jsonify(messages_response)




@app.route('/messages')
def get_messages():
    vehicle_ids = request.args.getlist('v_id')
    include_location = request.args.get('include_location')
    if vehicle_ids: 
        messages = Message.query.filter(Message.vehicle_id.in_(vehicle_ids)).all()
    else:
        messages = Message.query.all()
    if not include_location:
        return jsonify([m.serialize() for m in messages])

    vehicle_to_messages = collections.defaultdict(list)
    for message in messages:
        vehicle_to_messages[message.vehicle_id].append(message)

    messages_response = {'messages': []}
    if include_location:
        routes = [rt[0] for rt in db.session.query(Stop.route_tag).group_by(Stop.route_tag).all()]
        last_min_epoch = int(time.time()) - 60000
        responses = []
        for route in routes:
            responses.append(client.get_vehicle_locations(route, last_min_epoch))
        for response in responses:
            for vehicle in response.get('vehicle') or []:
                if vehicle['id'] in vehicle_ids:
                    carried_messages = vehicle_to_messages[vehicle['id']]
                    to_ret = []
                    for msg in carried_messages:
                        msg_serialize = msg.serialize()
                        msg_serialize['lat'] = vehicle['lat']
                        msg_serialize['lon'] = vehicle['lon']
                        messages_response['messages'].append(msg_serialize)
    return jsonify(messages_response)


@app.route('/board', methods=['POST'])
def board_bus():
    content = request.json['message']
    stop_tag = str(request.json['stop'])
    stop = Stop.query.filter_by(tag=stop_tag).first()
    if stop is None:
        return jsonify({'error': 'invalid stop tag'}), 400

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
                stop_tag=stop.tag,
                vehicle_id=prediction['vehicle']
            )
            db.session.add(message)
            db.session.commit()
            return jsonify({'vehicle_id': message.vehicle_id, 'boarded_at': message.created_at})

    if bus_departing is False:
        min_in_ms = int(predictions[0]['minutes']) * 60 * 1000
        sec_in_ms = int(predictions[0]['seconds']) * 1000
        return jsonify({'next_bus': min_in_ms + sec_in_ms}), 503

@app.route('/broadcast', methods=['POST'])
def broadcast():
    vehicle_ids = request.json['vehicle_ids']
    stop_tags = request.json['stop_tags']
    vehicle_to_stop = request.json['vehicle_to_stop']
    messages = Message.query.filter(Message.vehicle_id.in_(vehicle_ids)).all()
    actual_vehicles = collections.defaultdict(list)
    for message in messages:
        actual_vehicles[message.vehicle_id].append(message)
    print(actual_vehicles)
    actual_stops = []
    for v in actual_vehicles.keys():
        actual_stops.append(vehicle_to_stop[v])
    print(actual_stops)
    all_messages = Message.query.all()
    print(f'Messages to send: {len(messages)} / {len(all_messages)}')
    listeners = Listener.query.filter(Listener.stop_tag.in_(actual_stops)).all()
    listeners_by_stop = collections.defaultdict(list) 
    for listener in listeners:
        listeners_by_stop[listener.stop_tag].append(listener)
    all_listeners = Listener.query.all()
    print(f'Listeners to send to: {len(listeners)} / {len(all_listeners)}')

    for vehicle, messages in actual_vehicles.items():
        current_stop = vehicle_to_stop[vehicle]
        listeners = listeners_by_stop[current_stop]
        for listener in listeners:
            for message in messages:
                print(f'Sending Message {message.id} on bus {message.vehicle_id} to {listener.id} ({listener.url}) because stop {listener.stop_tag}')
                payload = message.serialize()
                payload['stop_tag'] = listener.stop_tag
                requests.post(listener.url, json=payload)

    return 'success'

