import py_nextbus

client = py_nextbus.NextBusClient(output_format='json')
agency = "sf-muni"

stops_to_listeners = {}

def load_stops(clipper_url):
    route_config = client.get_route_config(agency=agency)
    routes = route_config['route']
    for route in routes:
        for stop in route['stop']:
            stops_to_listeners[stop['stopId']] = clipper_url
    return stops_to_listeners

load_stops('ngrok')
