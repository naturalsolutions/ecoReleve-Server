"""
Created on Fri Sep 19 17:24:09 2014
@author: Natural Solutions (Thomas)
"""

from pyramid.view import view_config
from sqlalchemy import select, distinct, join, text,Table, and_, bindparam, update
from ecorelevesensor.models import * #(TProtocolBirdBiometry,
# 	TProtocolChiropteraCapture,TProtocolSimplifiedHabitat,
# 	TProtocolChiropteraDetection,TProtocolBuildingAndActivity,
# 	TProtocolVertebrateIndividualDeath, TProtocolStationDescription,
# 	Station, Individual,
# 	Base,
# 	DBSession,
# 	User)
import numpy as np
import sys, datetime, transaction
from sqlalchemy.sql import func
import json
prefix = 'station'
dict_proto={
	'Bird Biometry': TProtocolBirdBiometry,
	'Chiroptera capture':TProtocolChiropteraCapture,
	'Simplified Habitat':TProtocolSimplifiedHabitat,
	'Chiroptera detection':TProtocolChiropteraDetection,
	'Building and Activities':TProtocolBuildingAndActivity,
	'station description':TProtocolStationDescription,
	'Vertebrate individual death':TProtocolVertebrateIndividualDeath,
	'Phytosociology habitat': TProtocolPhytosociologyHabitat,
	'Phytosociology releve': TProtocolPhytosociologyReleve,
	'Sighting conditions': TProtocolSightingCondition,
	'Simplified Habitat': TProtocolSimplifiedHabitat,
	'Station equipment': TProtocolStationEquipment,
	'Track clue': TProtocolTrackClue,
	'Capture Group': TProtocolCaptureGroup,
	'Capture Individual': TProtocolCaptureIndividual,
	'Nest Description': TProtocolNestDescription,
	'Clutch Description': TProtocolClutchDescription,
	'Entomo population': TProtocolEntomoPopulation,
	# 'Entomo Pop Census': TSubProtocolEntomoPopCensus,
	'Release Group': TProtocolReleaseGroup,
	'Release Individual': TProtocolReleaseIndividual,
	'Transects': TProtocolTransect,
	# 'SubProtocol Transect': TSubProtocolTransect,
	'Vertebrate group': TProtocolVertebrateGroup,
	'Vertebrate individual': TProtocolVertebrateIndividual
	}

@view_config(route_name=prefix, renderer='json', request_method='GET')
def monitoredSites(request):
   
	data = DBSession.query(Station).all()
	return data

@view_config(route_name=prefix+'/id', renderer='json', request_method='GET')
def monitoredSite(request):
   
	id_ = request.matchdict['id']
	print(id_)
	print(Station)
	data = DBSession.query(Station).filter(Station.id == id_).one()
	return data

	
@view_config(route_name=prefix+'/area', renderer='json', request_method='GET')
def monitoredSitesArea(request):	
	print('passed')
	proto_view_Name=request.matchdict['name_vue'].replace('%20',' ')
	print ('______________')
	print (proto_view_Name)
	try :
		proto_view_Table=Base.metadata.tables[proto_view_Name]
		join_table=join(proto_view_Table, Station, proto_view_Table.c['TSta_PK_ID'] == Station.id )
	except :
		print('_______except______')
		proto_view_Table=dict_proto[proto_view_Name]()
		join_table=join(proto_view_Table, Station, proto_view_Table.FK_TSta_ID == Station.id )

	print (proto_view_Table)

	
	slct=select([Station.area]).distinct().select_from(join_table)
	data = DBSession.execute(slct).fetchall()

	return [row['Region' or 'Area'] for row in data]


@view_config(route_name=prefix+'/locality', renderer='json', request_method='GET')
def monitoredSitesLocality(request):
	print('passed')

	proto_view_Name=request.matchdict['name_vue'].replace('%20',' ')
	print ('______________')
	print (proto_view_Name)
	try :
		proto_view_Table=Base.metadata.tables[proto_view_Name]
		join_table=join(proto_view_Table, Station, proto_view_Table.c['TSta_PK_ID'] == Station.id )

	except :
		print('_______except______')
		
		proto_view_Table=dict_proto[proto_view_Name]()
		join_table=join(proto_view_Table, Station, proto_view_Table.FK_TSta_ID == Station.id )
		
	print (proto_view_Table)

	
	slct=select([Station.locality]).distinct().select_from(join_table)
	data = DBSession.execute(slct).fetchall()

	return [row['Place' or 'Locality'] for row in data]

@view_config(route_name=prefix+'/addStation', renderer='json', request_method='POST')
def insertNewStation(request):

	data=request.params
	check_duplicate_station = select([func.count(Station.id)]).where(and_(Station.date == bindparam('date'),
		Station.lat == bindparam('lat'),Station.lon == bindparam('lon')))

	if DBSession.execute(check_duplicate_station, {'date':data['Date_'], 'lat':data['LAT'], 'lon':data['LON']}).scalar() == 0 and data.has_key('PK')==False :
		try :

			# get REGION and UTM by stored procedure
			print ('_______Region___________')
			stmt_Region = text("""
				DECLARE @geoPlace varchar(255);
				EXEC """ + dbConfig['data_schema'] + """.sp_GetRegionFromLatLon :lat, :lon, @geoPlace OUTPUT;
				SELECT @geoPlace;"""
			).bindparams(bindparam('lat', value=data['LAT'] , type_=Numeric(9,5)),bindparam('lon', value=data['LON'] , type_=Numeric(9,5)))
			geoRegion=DBSession.execute(stmt_Region).scalar()
			print (geoRegion)

			print ('_______UTM___________')
			stmt_UTM=text("""
				DECLARE @geoPlace varchar(255);
				EXEC """ + dbConfig['data_schema'] + """.sp_GetUTMCodeFromLatLon   :lat, :lon, @geoPlace OUTPUT;
				SELECT @geoPlace;"""
			).bindparams(bindparam('lat', value=data['LAT'] , type_=Numeric(9,5)),bindparam('lon', value=data['LON'] , type_=Numeric(9,5)))
			geoUTM=DBSession.execute(stmt_UTM).scalar()
			print (geoUTM)

			#get userID with fieldWorker_Name
			users_ID_query = select([User.id], User.fullname.in_((data['FieldWorker1'],data['FieldWorker2'],data['FieldWorker3'])))
			users_ID = DBSession.execute(users_ID_query).fetchall()
			users_ID=[row[0] for row in users_ID]
			if len(users_ID) <3 :
				users_ID.extend([None,None])

			#get ID fieldActivity
			id_field_query=select([ThemeEtude.id], ThemeEtude.Caption == data['FieldActivity_Name'])
			id_field=DBSession.execute(id_field_query).scalar()

			# set station and insert it
			station=Station(name=data['Name'],lat=data['LAT'], lon= data['LON'], 
				date=data['Date_'], fieldActivityName = data['FieldActivity_Name'],
				creator=request.authenticated_userid, area=geoRegion, utm=geoUTM, fieldActivityId=id_field,
				fieldWorker1=users_ID[0],fieldWorker2=users_ID[1],fieldWorker3=users_ID[2])

			DBSession.add(station)
			DBSession.flush()
			id_sta=station.id
		
			print(id_sta)
			return id_sta

		except :
			return "Unexpected error during INSERT station:", sys.exc_info()[0]

	elif data.has_key('PK') :
		
		try : 

			up_station=DBSession.query(Station).get(data['PK'])
			del data['PK']
			for k, v in data.items() :
				setattr(up_station,k,v)

			transaction.commit()
			return 'station updated with success'

		except :
			return "Unexpected error during UPDATE station:", sys.exc_info()[0]

	else :
		return 'a station exists at same date and coordinates'
	

@view_config(route_name=prefix+'/searchStation', renderer='json', request_method='GET')
def check_newStation (request):
	print ('_____________________')

	data=request.params
	check_duplicate_station = select([func.count(Station.id)]).where(and_(Station.date == bindparam('date'),
		Station.lat == bindparam('lat'),Station.lon == bindparam('lon')))

	if DBSession.execute(check_duplicate_station, {'date':data['Date_'], 'lat':data['LAT'], 'lon':data['LON']}).scalar() == 0:
		return 0
	else :

		return 1


@view_config(route_name=prefix+'/addProtocol', renderer='json', request_method='POST')
def insert_protocol (request):

	data=dict(request.params)
	protocolName=data['name']

		# insert new row in the protocol

	if request.params.has_key('PK')!=True :
		try : 
			print('_______add proto_____')	
			new_proto=dict_proto[protocolName]()
			new_proto.InitFromFields(data)
			DBSession.add(new_proto)
			DBSession.flush()
			id_proto= new_proto.PK
			print(id_proto)
			return id_proto
		except : 
			return "Unexpected error in INSERT protocols:", sys.exc_info()[0]

	else :
		try : 

			print('_______update proto__________')
			up_proto=DBSession.query(dict_proto[protocolName]).get(data['PK'])
			del data['name']
			del data['PK']
			for k, v in data.items() :
				setattr(up_proto,k,v)
			transaction.commit()

			return 'protocol updated with succes'
		except : 
			return "Unexpected error in UPDATE protocols:", sys.exc_info()[0]
    
@view_config(route_name=prefix+'/getProtocol', renderer='json', request_method='GET')
def get_protocol (request):

	data=request.params
	id_sta=data.get('id_sta')
	proto_onSta={}
	for protoName, Tproto in dict_proto :
		print(protoName+' : '+ Tproto)
		query=select(Tproto,Tproto.FK_TSta_ID==id_sta)
		res=DBSession.execute(query).scalar()
		print(res)
		if res!=None :
			proto_onSta[protoName]=res

	return proto_onSta


@view_config(route_name=prefix+'/station_byDate', renderer='json', request_method='GET')
def station_byDate (request) :

	data=reques.params

	query= select(Station).filter(Station.date>=data.get('begin_date')).filter(Station.date<=data.get('end_date'))
	result= DBSession.execute(query).fetchall()
    
	return result

