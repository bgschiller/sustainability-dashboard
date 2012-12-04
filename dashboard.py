from flask import Flask, render_template, jsonify, make_response
import logging
import traceback
import json
import random

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('dashboard.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s -%(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

RESOURCES = ('water','gas','electricity','waste','steam')
BUILDINGS = (('aw','Academic West'),('bh','Bond Hall'), ('cf','Communications Facility'), ('cb','Chemistry Building'))
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
        # [ms since UNIX epoch, value]
        data = random_data() #todo: we should get the actual data instead of these numbers i just made up.
        logger.info(data)
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


