from pyramid.config import Configurator
from sqlalchemy import engine_from_config
from pyramid.request import Request, Response
from sqlalchemy.engine import Connection

from ecorelevesensor.models import (
   DBSession,
   Base,
   _Base,
   dbConfig
)

# Define a new request factory allowing cross-domain AJAX calls.
def request_factory(env):
	request = Request(env)
	request.response = Response()
	request.response.headerlist.extend([('Access-Control-Allow-Origin', '*')])
	return request

# Add all the routes of the application.
def add_routes(config):
   config.add_route('weekData', 'ecoReleve-Sensor/weekData')
   config.add_route('argos/unchecked/list', 'ecoReleve-Sensor/argos/unchecked/list')
   config.add_route('argos/unchecked/count', 'ecoReleve-Sensor/argos/unchecked/count')
   config.add_route('argos/unchecked', 'ecoReleve-Sensor/argos/unchecked')
   config.add_route('argos/check', 'ecoReleve-Sensor/argos/check')
   config.add_route('argos/insert', 'ecoReleve-Sensor/argos/insert')
   config.add_route('station_graph', 'ecoReleve-Core/stations/graph')

   config.add_route('theme/list', 'ecoReleve-Core/theme/list')
   ##### Individuals routes #####
   config.add_route('core/individuals/stations', 'ecoReleve-Core/individuals/stations')
   config.add_route('core/individuals/search/values', 'ecoReleve-Core/individuals/search/values')
   config.add_route('core/individuals/search', 'ecoReleve-Core/individuals/search')
   config.add_route('core/individuals/count', 'ecoReleve-Core/individuals/count')

   config.add_route('core/user/fieldworkers','ecoReleve-Core/user/fieldworkers')
   config.add_route('core/protocoles/list','ecoReleve-Core/protocoles/list')
   config.add_route('core/views/list','ecoReleve-Core/views/list')
   config.add_route('core/views/export/details','ecoReleve-Core/views/details/{name}')
   config.add_route('core/views/export/count', 'ecoReleve-Core/views/{name}/count')
   config.add_route('core/views/export/filter/count', 'ecoReleve-Core/views/filter/{name}/count')
   config.add_route('core/views/export/filter/geo', 'ecoReleve-Core/views/filter/{name}/geo')
   config.add_route('core/views/export/filter/result', 'ecoReleve-Core/views/filter/{name}/result')
   config.add_route('core/views/export/filter/export', 'ecoReleve-Core/views/filter/{name}/export')

   ##### Autocomplete routes #####
   config.add_route('core/autocomplete', 'ecoReleve-Core/autocomplete')
   config.add_route('rfid_import', 'ecoReleve-Sensor/rfid/import')
   config.add_route('rfid_list', 'ecoReleve-Sensor/rfid/list')
   config.add_route('monitored_station_list', 'ecoReleve-Sensor/monitored_station/list')
   config.add_route('rifd_monitored_add', 'ecoReleve-Sensor/rifd_monitored/add')
   ##### Map routes #####
   config.add_route('map/add', 'ecoReleve-Sensor/map/add/{name}')
   config.add_route('map/create', 'ecoReleve-Sensor/map/create/{name}')
   config.add_route('map/closest_to', 'ecoReleve-Sensor/map/{name}/closest_to')
   config.add_route('map/drop', 'ecoReleve-Sensor/map/drop/{name}')
   
def add_views(config):
   config.add_view('ecorelevesensor.views.map.create', route_name='map/create')

def main(global_config, **settings):
   """ This function returns a Pyramid WSGI application.
   """
   engine = engine_from_config(settings, 'sqlalchemy.')
   dbConfig['data_schema'] = settings['data_schema']
   DBSession.configure(bind=engine)
   Base.metadata.bind = engine
   _Base.metadata.bind = engine
   _Base.metadata.reflect(schema = 'ecoReleve_Data.dbo', views=True, extend_existing=True)
   config = Configurator(settings=settings)
   config.include('pyramid_chameleon')
   config.include('pyramid_tm')
   config.set_request_factory(request_factory)
   add_routes(config)
   #add_views(config)
   config.scan()
   return config.make_wsgi_app()