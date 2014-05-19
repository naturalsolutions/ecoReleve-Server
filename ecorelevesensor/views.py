from pyramid.response import Response
from pyramid.view import view_config

from sqlalchemy.exc import DBAPIError
from sqlalchemy import func, cast, Date

import datetime

from .models import (
    DBSession,
    Argos,
    Gps
    )


@view_config(route_name='home', renderer='templates/mytemplate.pt')
def my_view(request):
    try:
        one = DBSession.query(Argos.date).count()
    except DBAPIError as e:
        return Response(conn_err_msg, content_type='text/plain', status_int=500)
    return {'one': one, 'project': 'app'}

conn_err_msg = """\
Pyramid is having a problem using your SQL database.  The problem
might be caused by one of the following things:

1.  You may need to run the "initialize_app_db" script
    to initialize your database tables.  Check your virtual 
    environment's "bin" directory for this script and try to run it.

2.  Your database server may not be running.  Check that the
    database server referred to by the "sqlalchemy.url" setting in
    your "development.ini" file is running.

After you fix the problem, please restart the Pyramid application to
try it again.
"""

@view_config(route_name='weekData', renderer='json')
def weekData(request):
	data = {
		'label':[str(datetime.date.today() - datetime.timedelta(days = i)) for i in range(1,8)],
		'nbArgos': [0] * 8,
		'nbGPS': [0] * 8
	}
	argos_query = DBSession.query(cast(Argos.date, Date).label('date'), func.count(Argos.id).label('nb')).filter(Argos.date >= datetime.date.today() - datetime.timedelta(days = 7)).group_by(cast(Argos.date, Date))
	gps_query = DBSession.query(cast(Gps.date, Date).label('date'), func.count(Gps.id).label('nb')).filter(Gps.date >= datetime.date.today() - datetime.timedelta(days = 7)).group_by(cast(Gps.date, Date))
	for date, nb in argos_query.all():
		i = data['label'].index(str(date))
		data['nbArgos'][i] = nb
	for date, nb in gps_query.all():
		i = data['label'].index(str(date))
		data['nbGPS'][i] = nb
	return data

@view_config(route_name='unchecked', renderer='json')
def uncheckedData(request):
    argos_data = DBSession.query(Argos).filter(Argos.checked == False).order_by(Argos.ptt)
    data = {argos.ptt:{'date': str(argos.date), 'lat':str(argos.lat), 'lon':str(argos.lon)} for argos in argos_data.all()}
    return data