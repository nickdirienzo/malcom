import py_nextbus

client = py_nextbus.NextBusClient(output_format='json')
agency = "sf-muni"

# route_id I think is actually route_tag in the api 

def generate_route_graph( route_id ):
    route_config = client.get_route_config(agency=agency, r = route_id )
    routes = route_config['route']
    for route in routes:
        route_list = []
        for stop in route['stop']:
            route_list.append({"route_tag": route_id, "stop_tag": int(stop['tag'])})
    return route_list
            

def find_next_vehicle_for_route(route_id):
    return client.get_predictions_for_multi_stops(generate_route_graph(route_id), agency=agency)

import pdb
pdb.set_trace()
