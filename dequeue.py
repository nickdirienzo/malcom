import py_nextbus

client = py_nextbus.NextBusClient(output_format='json')
client.agency = "sf-muni"

# route_id I think is actually route_tag in the api 

def generate_route_graph( route_id ):
    route_config = client.get_route_config( route_tag=route_id )
    route = route_config['route']
    route_list = []
    for stop in route['stop']:
        route_list.append({"route_tag": route_id, "stop_tag": int(stop['tag'])})
    return route_list
            

def find_vehicles_at_stops_for_route(route_id):
    route_predictions = client.get_predictions_for_multi_stops(generate_route_graph(route_id))
    route_predictions = route_predictions['predictions']
    stop_vehicle_status = {} 
    for stop in route_predictions:
        next_at_stop = stop['direction']['prediction'][0]
        if int(next_at_stop['minutes']) < 2:
            stop_vehicle_status[stop['stopTag']] = {'vehicle': next_at_stop['vehicle'], 'minutes': next_at_stop['minutes']}
    return stop_vehicle_status

hot_garbage = find_vehicles_at_stops_for_route('F')
# hot_garbage['predictions'][<stop>0]['stopTag']
# hot_garbage['predictions'][<stop>0]['direction']['prediction'][0] > 'vehicle' 'minutes'

import pdb; pdb.set_trace()
