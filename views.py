from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.utils.encoding import smart_text

from django.conf import settings

import json
import requests
from bs4 import BeautifulSoup, NavigableString

import time
from django.views.decorators.cache import never_cache
from datetime import date, datetime
import pytz
import uuid
import xml.etree.ElementTree as ET
from distutils.version import StrictVersion
from xml.etree.ElementTree import tostring
from ifttt.models import VersionUpdateEvent, WebsiteUnavailableEvent, BeerOnTapEvent, BeerList

static_json = '{ \
  "data": { \
    "samples": {  \
        "triggers": { \
            "website_down": { \
              "your_website_url": "https://getvisualizer.com" \
            }, \
            "beer_on_tap": { \
              "brewery_name": "Goose Island" \
            }, \
            "update_available":{ \
              "your_version_number": "1.2.50" \
            } \
        } \
    } \
  } \
}'

uid = [
    '4126e23e-f56c-4334-b7e3-c9981b3fd576',
    'cbc66b6f-0797-4b5e-811d-2e92624e47a9',
    'fbb0b22a-2c51-48b3-8398-d366da3a92a0',
    ]
def __get_website(in_url):
    status = 404
    try:
        r = requests.get(in_url, timeout=5)
        status = r.status_code
    except:
        status = 404
    return status

def get_iso_date():
    return datetime.now(pytz.utc).replace(microsecond=0).isoformat('T')

# takes a dictionary
def json_response(response_data, in_status=200):    
    return HttpResponse(response_data, content_type='application/json; charset=utf-8', status=in_status)

def __version_from_xml_response(xml_data):
    root = ET.fromstring(xml_data)
    return_data = {}
    if root is not None:
        new_versions = root.findall('./version/*')
        for elem in new_versions:
            return_data[elem.tag] = elem.text
    return return_data

def __get_url(url, user_agent):
    my_data = None
    header = {'User-Agent':user_agent}
    try:
        r = requests.get(url, headers=header)
        
        if r.status_code == 200:
            xml_data = r.content
            my_data = __version_from_xml_response(xml_data)
    except:
        my_data = []
    return my_data

# Return a version string if it is newer than customer value. None otherwise.
def __add_new_version(version_list):
    # Iterate list and add to DB if it doesn't exist    
    for version_name, value in version_list.iteritems():
        try:
            obj = VersionUpdateEvent.objects.get(
                version_number=value)
        except VersionUpdateEvent.DoesNotExist:
            __create_version_update_record(value)

def __new_website_status(status, user_url):
    try:
        last_event = WebsiteUnavailableEvent.objects.filter(web_url=user_url).order_by('-meta_timestamp').first()
        if last_event.status_code != str(status):
            return True
    except:
        # assume list is empty
        return True
    return False

def __create_version_update_record(value):
    counter = str(uuid.uuid4())
    meta_list = {
        'id': counter,
        'timestamp': int(time.time())
    }
    recipe_list = {
        'created_at': get_iso_date(),
        'version_number': value,
        'meta': meta_list
    }
    new_event = VersionUpdateEvent(
        trigger_name = "update_available",
        meta_id = meta_list['id'],
        meta_timestamp = meta_list['timestamp'],
        created_at = recipe_list['created_at'],
        version_number = recipe_list['version_number']
    )
    new_event.save()

def __create_website_unavailable_record(value, user_url):
    counter = str(uuid.uuid4())
    meta_list = {
        'id': counter,
        'timestamp': int(time.time())
    }
    recipe_list = {
        'occurred_at': get_iso_date(),
        'status_code': value,
        'web_url': user_url,
        'meta': meta_list
    }
    new_event = WebsiteUnavailableEvent(
        trigger_name = "website_down",
        meta_id = meta_list['id'],
        meta_timestamp = meta_list['timestamp'],
        occurred_at = recipe_list['occurred_at'],
        status_code = recipe_list['status_code'],
        web_url = recipe_list['web_url'],
    )
    new_event.save()

def __create_beer_in_list(brewery_name, beer_name, venue):
    new_event = BeerList(
        brewery_name = brewery_name,
        beer_name = beer_name,
        venue= venue)
    new_event.save()

def __remove_beer_in_list(brewery_name, beer_name, venue):
    beer = BeerList.objects.filter(brewery_name = brewery_name, beer_name = beer_name, venue= venue)
    beer.delete()

def __get_beer_in_list(venue):
    beer_list = BeerList.objects.filter(venue=venue).values_list('brewery_name', 'beer_name')
    return beer_list
    
def __create_beer_on_tap_record(brewery_name, beer_name, venue, removed = False):
    counter = str(uuid.uuid4())
    meta_list = {
        'id': counter,
        'timestamp': int(time.time())
    }
    event_list = {
        'created_at': get_iso_date(),
        'removed': removed,
        'brewery_name': brewery_name,
        'beer_name': beer_name,
        'venue': venue,
        'meta': meta_list
    }
    new_event = BeerOnTapEvent(
        trigger_name = 'beer_on_tap',
        meta_id = meta_list['id'],
        meta_timestamp = meta_list['timestamp'],
        created_at = event_list['created_at'],
        removed = event_list['removed'],
        brewery_name = event_list['brewery_name'],
        beer_name = event_list['beer_name'],
        venue = event_list['venue'],
    )
    new_event.save()

def __get_beer_event_records(limit, names):
    event_list = []
    user_brewery_name = names[0]
    venue = names[1]
    
    object_list = BeerOnTapEvent.objects.filter(brewery_name__contains=user_brewery_name, venue__iexact=venue).order_by('-meta_timestamp')[:limit]
    for beer_event in object_list:
        meta_list = {
            'id': beer_event.meta_id,
            'timestamp': beer_event.meta_timestamp,
        }
        returned_event = {
            'created_at': str(beer_event.created_at.isoformat('T')),
            'beer_name': beer_event.beer_name,
            'venue': beer_event.venue,
            'still_available': not beer_event.removed,
            'meta': meta_list
        }
        event_list.append(returned_event)
    return event_list

def __get_website_event_records(limit=50, user_url=None):
    recipe_list = []
    object_list = WebsiteUnavailableEvent.objects.filter(web_url=user_url).order_by('-meta_timestamp')[:limit]
    for version_event in object_list:
        meta_list = {
            'id': version_event.meta_id,
            'timestamp': version_event.meta_timestamp,
        }
        returned_event = {
            'occurred_at': str(version_event.occurred_at.isoformat('T')),
            'status_code': version_event.status_code,
            'meta': meta_list
        }
        recipe_list.append(returned_event)
    return recipe_list


def __get_update_records(limit=50):
    recipe_list = []
    object_list = VersionUpdateEvent.objects.order_by('-meta_timestamp')[:limit]
    for version_event in object_list:
        meta_list = {
            'id': version_event.meta_id,
            'timestamp': version_event.meta_timestamp,
        }
        returned_event = {
            'created_at': str(version_event.created_at.isoformat('T')),
            'version_number': version_event.version_number,
            'meta': meta_list
        }
        recipe_list.append(returned_event)
    return recipe_list

@never_cache
@csrf_exempt
def ifttt(request, api_version=1, action='status', encoding='', params=None, **kwargs):
    limit = 50
    triggerFields = {}

    channel_key = request.META.get('HTTP_IFTTT_CHANNEL_KEY')
    if channel_key is None or channel_key != settings.IFTTT_CHANNEL_KEY:
        data = {}
        value = {'message':'Unauthorized'}
        data['errors'] = [value]
        return json_response(json.dumps(data), 401)

    if request.method == 'POST' and int(request.META['CONTENT_LENGTH']) > 0:
        body_json = json.loads(request.body)
        if 'limit' in body_json:
            limit = body_json['limit']
            if int(limit) < 1:
                json_value = json_builder(None, 0, int(limit), False)
                return json_response(json_value)
        if 'triggerFields' in body_json:
            triggerFields = body_json['triggerFields']
        
    if action == 'status':
        return status(request)
    elif action == 'test':
        return test(request)
    elif action == 'user':
        return user_info(request)
    elif action == 'triggers':
        return triggers(request, params, limit, triggerFields)
    elif action == 'create':
        #__create_record()
        return HttpResponse('created something')
    elif action == 'show':
        val = __new_website_status(200)
        return HttpResponse(val)
    elif action == 'display':
        returned_records = __get_update_records()
        json_string = json.dumps(returned_records)
        return json_response(json_string)
    return HttpResponseBadRequest('No endpoint requested')

# status return 200
def status(request):
    return HttpResponse()

# test/setup
def test(request):
    json_string = static_json
    return HttpResponse(json_string, content_type='application/json; charset=utf-8')

def __update_website_status(status, user_url):
    # get DB status, fixed
    has_changed = __new_website_status(status, user_url)

    # if status doesn't match
    if has_changed:
        #   create new event -
        __create_website_unavailable_record(status, user_url)
    
def __test_data(trigger_enum, record_iter, data=None):

    if trigger_enum == 0:
        if record_iter < 3:
            counter = uid[record_iter]
        else:
            counter = str(uuid.uuid4())
        meta_list = {
            'id': counter,
            'timestamp': int(time.time())
        }
        recipe_list = {
            'created_at': get_iso_date(),
            'where_to_go': 'https://getvisualizer.com/blog',
            'number_of_posts': '0',
            'meta': meta_list
        }
    elif trigger_enum == 1:
        value = 200
        if record_iter > 2 and data is not None:
            value = data

        if record_iter < 3:
            counter = uid[record_iter]
        else:
            counter = str(uuid.uuid4())
        meta_list = {
            'id': counter,
            'timestamp': int(time.time())
        }
        recipe_list = {
            'occurred_at': get_iso_date(),
            'status_code': value,
            'meta': meta_list
        }
    return recipe_list

def json_builder(input_data, trigger_enum, limit, new_values=False, value=None):
    data = {}
    data_list = []

    # generate three for fun
    num_records = 3
    if new_values:
        num_records = 4
    count = 0

    if trigger_enum == 2:
        data_list = __get_update_records(limit)
    elif trigger_enum == 1:
        data_list = __get_website_event_records(limit, input_data)
    elif trigger_enum == 3:
        data_list = __get_beer_event_records(limit, input_data)
    else:
        while limit > count and num_records > count:
            data_list.append(__test_data(trigger_enum, count, value))
            count = count + 1

    data['data'] = data_list
    values = json.dumps(data)
    return values

@never_cache
@csrf_exempt
def triggers(request, params, limit, triggerFields):
    if params == 'notification_this_month':
        return notification_month(request, limit)
    elif params == 'website_down':
        return website_down(request, limit, triggerFields)
    elif params == 'update_available':
        return update_available(request, limit, triggerFields)
    elif params == 'beer_on_tap':
        return beer_on_tap(request, limit, triggerFields )
    return HttpResponse(params)

def user_info(request):

    user_info = {'name': 'anonymous',
        'id': 'banana_split',
        'url': 'https://getvisualizer.com'
    }
    data = {}
    data['data'] = user_info
    return json_response(json.dumps(data))

def __get_beer_list_city():
    # return a list of brewery name and beer name
    city_beer_store_url = 'http://citybeerstore.com/menu/'
    brewery_list = []
    try:
        r = requests.get(city_beer_store_url, timeout=10)
        status = r.status_code     
    except:
        status = 500
        return brewery_list
    
    soup = BeautifulSoup(r.text)
    # Data is in the first 'ul' HTML element
    beerlist = soup.ul
    for beer in beerlist.children:
        # Only interate over Tag elements
        if type(beer) is not NavigableString:
            brewery_list.append( ( unicode(beer.select("div")[0].string), unicode(beer.select("div")[1].string) ))

    return brewery_list

def __get_beer_website(in_url):
    status = 404
    
    try:
        r = requests.get(in_url, timeout=10)
        status = r.status_code
        r.encoding = 'utf-8'
    except:
        status = 500
        return []
    return r

def process_data(r):
    # Parse HTML document for beer names in two columns
    #soup = BeautifulSoup(open('Trappist.html'))
    soup = BeautifulSoup(r.text)

    search_id = ['back_bar_content', 'front_bar_content']

    # Set type prevents duplicate beer names
    beer_names = []
    
    for html_id in search_id:
        beerlist = soup.find(id=html_id)

        for beer in beerlist.children:
            if type(beer) is not NavigableString:
                beer_name = u''
                brewery_name = u''
                if beer is not None:
                    # Stripped strings will remove spacing from ends
                    counter = 0
                    for iter_string in beer.stripped_strings:
                        # Replace nbsp with ' ' and strange punctuation with '
                        temp_name = smart_text(iter_string, 'utf-8')
                        if counter == 0:
                            brewery_name = temp_name
                        elif counter == 1:
                            beer_name = temp_name
                        else:
                            beer_name = beer_name + " " + temp_name
                        counter = counter + 1
                    if counter == 1:
                        beer_name = brewery_name
                    if len(brewery_name) is not 0:
                        beer_names.append( (brewery_name, beer_name ) )
    return beer_names

def __get_beer_list(location):
    beer_list = __get_beer_website(location)
    return process_data(beer_list)
    
def __create_record():
    beer_list = __get_beer_list()
    for beer in beer_list:
        __create_beer_on_tap_record(beer[0], beer[1], 'City Beer Store')

def beer_on_tap(request, limit, triggerFields ):
    brewery_name = None
    if "brewery_name" in triggerFields:
        brewery_name = triggerFields['brewery_name']
    else:
        data = {}
        value = {'message':'Missing Trigger parameter for brewery_name'}
        data['errors'] = [value]
        return json_response(json.dumps(data), 400)

    if "venue_name" in triggerFields:
        venue_name = triggerFields['venue_name']
    else:
        venue_name = 'City Beer Store'

    beer_list = []
    # scrap website
    if 'City Beer Store' in venue_name:
        beer_list = __get_beer_list_city()
    else:
        beer_list = __get_beer_list('http://www.thetrappist.com/on-tap.php')

    # Get beer list stored in DB
    db_beer_list = __get_beer_in_list(venue_name)
    
    # Update DB
    for beer in beer_list:
        already_on_tap = (beer[0] , beer[1]) in db_beer_list

        # Don't need to do anything
        if already_on_tap:
            continue
        else:
            # add to menu : 0 is Brewery Name, 1 is Beer Name
            __create_beer_in_list(beer[0], beer[1], venue_name)
            # create event
            __create_beer_on_tap_record(beer[0], beer[1], venue_name)

    for beer in db_beer_list:
        if beer not in beer_list:
            # remove from menu
            __remove_beer_in_list(beer[0], beer[1], venue_name)
            # create a removed event
            __create_beer_on_tap_record(beer[0], beer[1], venue_name, True)
            
    # Return all records of matching names
    data = json_builder( [brewery_name, venue_name] , 3, limit) 
    return json_response(data)

def website_down(request, limit, triggerFields):

    url = None
    if "your_website_url" in triggerFields:
        url = triggerFields['your_website_url']
    else:
        data = {}
        value = {'message':'Missing Trigger parameter for website_down'}
        data['errors'] = [value]
        return json_response(json.dumps(data), 400)

    # Is website reachable
    status = __get_website(url)

    # Query last event.  If status changed, add a new record
    __update_website_status(status, url)

    # Return all records
    data = json_builder(url, 1, limit)
    return json_response(data)

def update_available(request, limit, triggerFields):
    version_number = None
    new_version = None
    version_url = 'https://getVisualizer.com/api/v1/stats'

    if "your_version_number" in triggerFields:
        version_number = triggerFields['your_version_number']
    else:
        data = {}
        value = {'message':'Missing Trigger parameter for update_available'}
        data['errors'] = [value]
        return json_response(json.dumps(data), 400)
    user_agent = "Visualizer for SketchUp %s/xml" % version_number
    # get latest from getvisualizer if greater than input version
    version_list = __get_url(version_url, user_agent)

    # Add to DB if newer
    if len(version_list):
        new_version = __add_new_version(version_list)
    
    # Return data
    return_data = json_builder(None, 2, limit, new_version is not None, new_version)
    return json_response(return_data)

def notification_month(request, limit):
    data = json_builder(None, 0, limit)
    return json_response(data)

def actions(request, params):
    return HttpResponse('actions')
