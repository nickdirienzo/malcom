import py_nextbus
import requests

client = py_nextbus.NextBusClient(output_format='json')
client.agency = "sf-muni"

# route_id I think is actually route_tag in the api 

def generate_route_graph():
    route_config = client.get_route_config()
    routes = route_config['route']
    route_stop_lists = {} 
    for route in routes:
        route_id = route['tag']
        route_stop_lists[route_id] = []
        for stop in route['stop']:
            route_stop_lists[route_id].append( {"route_tag": route_id, "stop_tag": int(stop['tag'])})
    return route_stop_lists

route_stop_dict = generate_route_graph()

def find_vehicles_at_stops_for_route(route):
    route_predictions = client.get_predictions_for_multi_stops(route_stop_dict[route])
    route_predictions = route_predictions.get('predictions') or []
    stop_vehicle_status = {}
    for stop in route_predictions:
        try:
            stop['direction']
        except KeyError:
            continue
        if isinstance(stop['direction'], dict):
            directions = [stop['direction']]
        else:
            directions = stop['direction']
        for direction in directions:
            if isinstance(direction['prediction'],list):
                next_at_stop = direction['prediction'][0]
            else:
                next_at_stop = direction['prediction']
            if int(next_at_stop['minutes']) < 2:
                stop_vehicle_status[stop['stopTag']] = {'vehicle': next_at_stop['vehicle'], 'minutes': next_at_stop['minutes']}
    return stop_vehicle_status

all_stopped_vehicles = []
for route in route_stop_dict.keys():
    print(route)
    all_stopped_vehicles.append(find_vehicles_at_stops_for_route(route))

stop_tags = []
vehicle_ids = []
for route in all_stopped_vehicles:
    stop_tags += [k for k in route.keys()]
    for stop, vehicle in route.items():
        vehicle_ids.append(vehicle['vehicle'])

response = requests.post('http://localhost:5000/broadcast', json={'stop_tags': stop_tags, 'vehicle_ids': vehicle_ids})
#hot_garbage = find_vehicles_at_stops_for_route('J')

import pdb; pdb.set_trace()
# hot_garbage['predictions'][<stop>0]['stopTag']
# hot_garbage['predictions'][<stop>0]['direction']['prediction'][0] > 'vehicle' 'minutes'
