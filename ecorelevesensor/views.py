from collections import OrderedDict

from pyramid.response import Response
from pyramid.view import view_config

from sqlalchemy.exc import DBAPIError
from sqlalchemy import func, cast, Date, String, desc, select, create_engine, text, union, and_
from sqlalchemy.sql.expression import label

from pyramid.httpexceptions import HTTPBadRequest, HTTPCreated

import datetime, operator

import json, urllib2

from .models import (
   DBSession,
   Argos,
   Gps,
   ProtocolArgos,
   Station,
   Individuals,
   Sat_Trx
)

@view_config(route_name='weekData', renderer='json')
def weekData(request):
   # Initialize Json object
   data = {
      'label':[str(datetime.date.today() - datetime.timedelta(days = i)) for i in range(1,8)],
      'nbArgos': [0] * 7,
      'nbGPS': [0] * 7
   }

   # Argos data
   argos_query = select([cast(Argos.date, Date).label('date'), func.count(Argos.id).label('nb')]).where(Argos.date >= datetime.date.today() - datetime.timedelta(days = 7)).group_by(cast(Argos.date, Date))
   for date, nb in DBSession.execute(argos_query).fetchall():
      try:
         i = data['label'].index(str(date))
         data['nbArgos'][i] = nb
      except:
         pass

   # GPS data
   gps_query = select([cast(Gps.date, Date).label('date'), func.count(Gps.id).label('nb')]).where(Gps.date >= datetime.date.today() - datetime.timedelta(days = 7)).group_by(cast(Gps.date, Date))
   for date, nb in DBSession.execute(gps_query).fetchall():
      try:
         i = data['label'].index(str(date))
         data['nbGPS'][i] = nb
      except:
         pass
   
   return data

@view_config(route_name='unchecked', renderer='json')
def uncheckedData(request):
   
   try:
      ptt = int(request.GET['id'])
   except:
      raise HTTPBadRequest()

   # Get all unchecked data for this ptt
   argos_data = select([Argos.id.label('id'), Argos.date.label('date'), cast(Argos.lat, String).label('lat'), cast(Argos.lon, String).label('lon'), 0]).where(and_(Argos.checked == False, Argos.ptt == ptt))
   gps_data = select([Gps.id.label('id'), Gps.date.label('date'), cast(Gps.lat, String).label('lat'), cast(Gps.lon, String).label('lon'), 1]).where(and_(Gps.checked == False, Gps.ptt == ptt))
   all_data = union(argos_data, gps_data)

   # Initialize json object
   data = {'ptt':{}, 'locations':[], 'indiv':{}}
   
   # Type 0 = Argos data, type 1 = GPS data
   for id, date, lat, lon, type in DBSession.execute(all_data.order_by(desc(all_data.c.date))).fetchall():
      data['locations'].append({'id': id, 'type':type, 'date':date, 'lat':lat, 'lon':lon})
      
   # Get informations for this ptt
   ptt_infos = select([Sat_Trx.ptt, Sat_Trx.manufacturer, Sat_Trx.model]).where(Sat_Trx.ptt == ptt)
   try:
      data['ptt']['ptt'], data['ptt']['manufacturer'], data['ptt']['model'] = DBSession.execute(ptt_infos).fetchone()
   except TypeError:
      pass
   
   # Get informations for the individual
   indiv_infos = select([Individuals.id, Individuals.age, Individuals.sex, Individuals.specie, Individuals.status, Individuals.origin]).where(Individuals.ptt == ptt)
   try:
      data['indiv']['id'], data['indiv']['age'], data['indiv']['sex'], data['indiv']['specie'], data['indiv']['status'], data['indiv']['origin'] = DBSession.execute(indiv_infos).fetchone()
   except TypeError:
      pass

   return data

@view_config(route_name='unchecked_summary', renderer='json')
def uncheckedSummary(request):
   # Initialize json object
   data = OrderedDict()
   # SQL query
   unchecked = union(select([Argos.id.label('id'), Argos.ptt.label('ptt')]).where(Argos.checked == 0),
                  select([Gps.id.label('id'), Gps.ptt.label('ptt')]).where(Gps.checked == 0)).alias()
   # Sum GPS and Argos locations for each ptt.
   count_by_ptt = select([unchecked.c.ptt, func.count().label('nb')]).group_by(unchecked.c.ptt).alias()
   # Add the bird associated to each ptt.
   unchecked_data = DBSession.execute(select([count_by_ptt.c.ptt, count_by_ptt.c.nb, Individuals.id.label('ind_id')]).select_from(count_by_ptt.outerjoin(Individuals, count_by_ptt.c.ptt == Individuals.ptt)).order_by(count_by_ptt.c.ptt))
   # Populate Json object
   for row in unchecked_data.fetchall():
      data.setdefault(row.ptt, []).append({'count':row.nb, 'ind_id':row.ind_id})
   return data

@view_config(route_name = 'station_graph', renderer = 'json')
def station_graph(request):
   # Initialize Json object
   data = OrderedDict()

   # Calculate the bounds
   today = datetime.date.today()
   begin_date = datetime.date(day = 1, month = today.month, year = today.year - 1)
   end_date = datetime.date(day = 1, month = today.month, year = today.year)

   # Query
   query = select([func.count(Station.id).label('nb'), func.year(Station.date).label('year'), func.month(Station.date).label('month')]
                  ).where(and_(Station.date >= begin_date, Station.date < end_date)).group_by(func.year(Station.date), func.month(Station.date))

   # Execute query and sort result by year, month (faster than an order_by clause in this case)
   for nb, y, m in sorted(DBSession.execute(query).fetchall(), key = operator.itemgetter(1,2)):
      data[datetime.date(day = 1, month = m, year = y).strftime('%b') + ' ' + str(y)] = nb

   return data

@view_config(route_name = 'individuals_count', renderer = 'json')
def individuals_count(request):
   # Query
   query = select([func.count(Individuals.id).label('nb')])

   return DBSession.execute(query).fetchone()['nb']

@view_config(route_name = 'argos/insert', renderer = 'json')
def argos_insert(request):
   list_of_ptts = request.json_body
   nb_gps, nb_argos, nb_ptt = 0, 0, 0
   for ptt_obj in list_of_ptts:
      ptt = ptt_obj.ptt
      ind_id = ptt_obj.ind_id
      nb_ptt += 1
      for location in ptt_obj.locations:
         if location.type == 0:
            nb_argos += 1
         elif location.type == 1:
            nb_gps += 1
   return {'ptt':nb_ptt, 'argos':nb_argos, 'gps':nb_gps}
