from flask import Flask, render_template, jsonify, make_response
from datetime import datetime
from airquote_database_airquote import airquote_database_airquote
 #Pronunciation note: do not say the airquote part of this variable name. Rather, make airquotes with your fingers, like ''database''
for building in airquote_database_airquote:
    for resource in airquote_database_airquote[building]: #I'm tired of fucking with this data... this only happens once on start-up of the webserver
        airquote_database_airquote[building][resource] = sorted(airquote_database_airquote[building][resource])
import logging
import traceback
import json
import random
import pyodbc
import time

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('dashboard.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s -%(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

conn = pyodbc.connect("Driver=/usr/local/lib/libtdsodbc.so;Server=140.160.141.163;UID=WIN-EFOCD61SVFV\Administrator;PWD=morethan12characters!;PORT=1433;DATABASE=ION_Data2;TDS_VERSION=8.0;")
if conn :
    logger.info('successfully connected to the db')

cmd = '''select top 10 DLS.TimestampSourceLT, DL.Value, S.Name
from Source S, DataLogStamp DLS, DataLog DL 
where S.ID = DLS.SourceID and 
DL.DataLogStampID = DLS.ID and 
DL.Value is not null and 
DL.Value > 0 and 
DLS.TimestampSourceLT < '{NextYear}' and 
S.Name >= '{earliestName}' and 
S.Name <= '{latestName}' 
order by DLS.TimestampSourceLT;'''

cmd2 = '''select top 10 T.TimestampSourceLT, DL.Value from 
    (select distinct DLS.TimestampSourceLT, DL.DataLogStampID 
        from DataLogStamp DLS, DataLog DL, Source S
            where DL.DataLogStampID = DLS.ID and
                DL.Value is not null and
                DL.Value > 0 and
                DLS.TimestampSourceLT < '{NextYear}' and
                S.Name >= '{earliestName}' and
                S.Name <= '{latestName}') as T,
    DataLog DL
        where DL.DataLogStampID = T.DataLogStampID
        order by T.TimestampSourceLT;'''



source_names = {'ah':['AH.C1', 'AH.E1_Main', 'AH.E2_Eatery'],
    'aic':['AIC.C1', 'AIC.E1_AI', 'AIC.E2_AW'],
    'bh':['BH.C1', 'BH.E1_Main'],
    'bi':['BI.C1', 'BI.E1_2NA', 'BI.E2_2NB', 'BI.E3_4NA', 'BI.E4_4NB'],
    'cb':['CB.C1', 'CB.E1_SHA', 'CB.E2_SHB', 'CB.E3_SLA', 'CB.E4_SLB'],
    'cf':['CF.C1', 'CF.E1_A', 'CF.E2_B'],
    'es':['ES.C1', 'ES.E1_Main'],
    'et':['ET.C1', 'ET.E1_Main'],
    'fi':['FI.C1', 'FI.E1_Main'],
    'hh':['HH.C1', 'HH.E1_Main'],
    'pa':['PA.C1', 'PA.E1_South', 'PA.E2_North'],
    'ph':['PH.C1', 'PH.E1_Main'],
    'sp':['SP.E2_Main']
    }
RESOURCES = ('water','gas','electricity','waste','steam')
BUILDINGS = (('bi','Biology Building'),('pa','Performing Arts'), ('ac','Administrative Services'), ('cb','Chemistry Building'))

dateformat = '%Y/%m/%d'

app = Flask(__name__)

app.debug = False #this is off because we are exposing the webserver to the open internet. If the program errors and debug is True, it will present a python prompt. This is obviously bad news from a security standpoint.

@app.route('/')
def dashboard():
    try:
        logger.info('rendered_template for dashboard')
        return render_template('dash.html', resources=RESOURCES, buildings=BUILDINGS)
    except Exception as e:
        msg = 'Error occurred in dashboard: {}. Traceback:\n{}'.format(e, traceback.format_exc())
        logger.error(msg)
        return make_response('<pre>' + msg + '</pre>', 500) # the <pre> tag preserves newlines.

#we can register a function to respond to more than one url. Here, we will respond differently if the user requests .json or .csv
#we could also pass parameters via GET requests like 'http://newman.cs.wwu.edu:5000/data?resource="water"&building="bh"' Then they would be available through the flask.request object, 
# http://flask.pocoo.org/docs/quickstart/#the-request-object
@app.route('/data/<resource>/<building>.<fmt>/')
@app.route('/data/<resource>/<building>/')
def query_database(resource, building, fmt='html'):
    try: #it can be a headache trying to debug flask. This is something I took to doing when I was using it. Notice the traceback call in the except clause.
        cursor = conn.cursor()
        if building in airquote_database_airquote and resource in airquote_database_airquote[building]:
            data = airquote_database_airquote[building][resource]
        elif building in source_names.keys():
            options = {'NextYear':str(datetime.now().year + 1),
                    'earliestName':source_names[building][0], #first in the list
                    'latestName':source_names[building][-1]} #last in the list
            cursor.execute(cmd2.format(**options))
            data = cursor.fetchall()
            logger.debug('retrieved data for {}'.format(building) + str(data))
            data = map(lambda (this_time, value): (time.mktime(this_time.timetuple())*1000, value), data)
            #data = map(lambda (this_time, value, name): (time.mktime(this_time.timetuple())*1000, value), data) # multiply by 1000 to get units of ms
        else:    
            data = random_data() #todo: we should get the actual data instead of these numbers i just made up.
        #data is a list of (ms since UNIX epoch, value) pairs
        logger.info('someone asked for {} at {} in format {}'.format(resource,building,fmt))
        if fmt == 'html':
            return render_template('data.html', r=resource, b=building, data=data)
        elif fmt == 'json':
            resp = make_response(json.dumps(data),200)
            resp.mimetype = 'text/json'
            return resp
        elif fmt == 'csv':
            resp =   make_response(
                    'Timestamp, Value\n' + '\n'.join(map(lambda elem: '{}, {}'.format(elem[0],elem[1]), data)))
            resp.mimetype = 'text/csv'
            return resp
        else:
            logger.info('Someone asked for a bad format "{}"'.format(fmt))
            return make_response('the format {} is not supported'.format(fmt),404)
        
    except Exception as e:
        msg = 'Error occurred in query_database: {}. Traceback:\n{}'.format(e, traceback.format_exc())
        logger.error(msg)
        return make_response('<pre>' + msg + '</pre>', 500) # the <pre> tag preserves newlines.

def random_data():
    num_points = random.randint(10,50)
    seq = (sum(n_dice_rolls(6)) for _ in xrange(num_points))
    return map(list, enumerate(seq))

def n_dice_rolls(n):
    dice_size = 12
    return map(lambda _: random.randint(1,dice_size), range(n))

if __name__ == '__main__':
    app.run(host='0.0.0.0')




