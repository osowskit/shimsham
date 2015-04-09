from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

import json
import requests
import time
from django.views.decorators.cache import never_cache

from datetime import datetime
import pytz
import uuid

from ifttt.VisualizerVersion import get_update_records, add_new_version, \
    get_version_url
from ifttt.VisualizerWebsite import update_website_status, \
    get_website_event_records, \
    get_website
from ifttt.BeerEventScrapper import get_beer_event_records, \
    get_beer_list_city, get_beer_list, create_beer_in_list, get_beer_in_list, \
    remove_beer_in_list, create_beer_on_tap_record
from ifttt.UntappdVenue import get_venue_id, parse_untappd_venue_activity, \
     update_venue_last_checkin
from ifttt.UntappdBeer import create_untappd_beer_on_tap_record, \
     get_untappd_event_records, process_untappd_beer_list
     

static_json = '{ \
  "data": { \
    "samples": {  \
        "triggers": { \
            "website_down": { \
              "your_website_url": "https://getvisualizer.com" \
            }, \
            "beer_on_tap": { \
              "brewery_name": "Goose Island", \
              "venue_name":"City Beer Store" \
            }, \
            "untappd_updates": { \
              "venue_name": "City Beer Store" \
            }, \
            "update_available":{ \
              "your_version_number": "1.2.50" \
            } \
        } \
    } \
  } \
}'


def get_iso_date():
    return datetime.now(pytz.utc).replace(microsecond=0).isoformat('T')


# takes a dictionary
def json_response(response_data, in_status=200):
    return HttpResponse(
        response_data,
        content_type='application/json; charset=utf-8',
        status=in_status
        )


@never_cache
@csrf_exempt
def ifttt(request, api_version=1, action='status',
          encoding='', params=None, **kwargs):
    limit = 50
    triggerFields = {}

    channel_key = request.META.get('HTTP_IFTTT_CHANNEL_KEY')
    if channel_key is None or channel_key != settings.IFTTT_CHANNEL_KEY:
        data = {}
        value = {'message': 'Unauthorized'}
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
    elif action == 'triggers':
        return triggers(request, params, limit, triggerFields)
    elif action == 'display':
        returned_records = get_update_records(limit)
        json_string = json.dumps(returned_records)
        return json_response(json_string)
    return HttpResponseBadRequest('No endpoint requested')


# Required by IFTTT endpoint test to return 200
def status(request):
    return HttpResponse()


# Required by IFTTT endpoint test to initialize test data
def test(request):
    json_string = static_json
    return HttpResponse(
        json_string,
        content_type='application/json; charset=utf-8'
        )


def json_builder(input_data, trigger_enum, limit,
                 new_values=False, value=None):
    data = {}
    data_list = []

    if trigger_enum == 2:
        data_list = get_update_records(limit)
    elif trigger_enum == 1:
        data_list = get_website_event_records(limit, input_data)
    elif trigger_enum == 3 or trigger_enum == 4:
        data_list = get_beer_event_records(limit, input_data)
    elif trigger_enum == 5:
        data_list = get_untappd_event_records(limit, input_data)

    data['data'] = data_list
    values = json.dumps(data)
    return values


@never_cache
@csrf_exempt
def triggers(request, params, limit, triggerFields):
    if params == 'website_down':
        return website_down(request, limit, triggerFields)
    elif params == 'update_available':
        return update_available(request, limit, triggerFields)
    elif params == 'beer_on_tap':
        return beer_on_tap(request, limit, triggerFields)
    elif params == 'beer_updates':
        return beer_updates(request, limit, triggerFields)
    elif params == 'untappd_updates':
        return untappd_updates(request, limit, triggerFields)
    return HttpResponse(params)


def get_untappd_api(in_url, endpoint='venue/checkins/3282',
                    headers=None, data={}):
    request_data = {}

    payload = {
        'client_id': settings.UNTAPPD_API_CLIENT_ID,
        'client_secret': settings.UNTAPPD_API_SECRET,
        }
    payload.update(data)
    url = in_url + endpoint

    try:
        r = requests.get(url, params=payload, timeout=10)
        request_data = r.json()
    except:
        request_data = {}
    return request_data


def untappd_updates(request, limit, triggerFields):

    if "venue_name" in triggerFields:
        venue_name = triggerFields['venue_name']
    else:
        data = {}
        value = {'message': 'Missing Trigger parameter for venue_name'}
        data['errors'] = [value]
        return json_response(json.dumps(data), 400)

    # lookup venue ID or search/create if it doesn't exist
    venue_data = get_venue_id(venue_name)
    venue_uid = venue_data['venue_uid']
    last_checkin = venue_data['last_checkin_id']
    venue_name = venue_data['venue_name']

    # Get checkin list for a venue
    untappd_api_version = 'v4/'
    endpoint = 'venue/checkins/' + str(venue_uid)
    # min_id is the last checkin_id queried
    url_param = {
        'min_id': last_checkin
        }
    venue_activity_list = get_untappd_api(
        'https://api.untappd.com/' + untappd_api_version,
        endpoint,
        data=url_param
        )
    activity_beer_list = parse_untappd_venue_activity(venue_activity_list)
    venue_activity_list = []

    # create or update beer information
    # return list of updated and created
    updated_list, created_list, highest_checkin = process_untappd_beer_list(
        activity_beer_list,
        {
            'venue': venue_name,
            'venue_uid': venue_uid
        }
        )
    activity_beer_list = []
    # It is possible that there weren't any results
    if last_checkin < highest_checkin:
        update_venue_last_checkin(venue_uid, highest_checkin)

    # return json_response(json.dumps(updated_list))
    for beer in created_list:
        create_untappd_beer_on_tap_record(
            beer['brewery_name'],
            beer['beer_name'],
            venue_name,
            venue_data['venue_social_name']
        )

    # update Venue with last seen. return list of beer not seen in 48 hours

    # create events for new beer
    data = []
    data = json_builder(venue_name, 5, limit)
    return json_response(data)


def beer_updates(request, limit, triggerFields):
    data = json_builder(None, 4, limit)
    return json_response(data)


def beer_on_tap(request, limit, triggerFields):
    brewery_name = None
    if "brewery_name" in triggerFields:
        brewery_name = triggerFields['brewery_name']
    else:
        data = {}
        value = {'message': 'Missing Trigger parameter for brewery_name'}
        data['errors'] = [value]
        return json_response(json.dumps(data), 400)

    if "venue_name" in triggerFields:
        venue_name = triggerFields['venue_name']
    else:
        venue_name = 'City Beer Store'

    beer_list = []
    # scrap website
    if 'City Beer Store' in venue_name:
        beer_list = get_beer_list_city()
    else:
        beer_list = get_beer_list('http://www.thetrappist.com/on-tap.php')

    # Get beer list stored in DB
    db_beer_list = get_beer_in_list(venue_name)

    # Update DB
    for beer in beer_list:
        already_on_tap = (beer[0], beer[1]) in db_beer_list

        # Don't need to do anything
        if already_on_tap:
            continue
        else:
            # add to menu : 0 is Brewery Name, 1 is Beer Name
            create_beer_in_list(beer[0], beer[1], venue_name)
            # create event
            create_beer_on_tap_record(beer[0], beer[1], venue_name)

    for beer in db_beer_list:
        if beer not in beer_list:
            # remove from menu
            remove_beer_in_list(beer[0], beer[1], venue_name)
            # create a removed event
            create_beer_on_tap_record(beer[0], beer[1], venue_name, True)

    # Return all records of matching names
    data = json_builder([brewery_name, venue_name], 3, limit)
    return json_response(data)


def website_down(request, limit, triggerFields):

    url = None
    if "your_website_url" in triggerFields:
        url = triggerFields['your_website_url']
    else:
        data = {}
        value = {'message': 'Missing Trigger parameter for website_down'}
        data['errors'] = [value]
        return json_response(json.dumps(data), 400)

    # Is website reachable
    status = get_website(url)

    # Query last event.  If status changed, add a new record
    update_website_status(status, url)

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
        value = {'message': 'Missing Trigger parameter for update_available'}
        data['errors'] = [value]
        return json_response(json.dumps(data), 400)

    user_agent = "Visualizer for SketchUp %s/xml" % version_number
    # get latest from getvisualizer if greater than input version
    version_list = get_version_url(version_url, user_agent)

    # Add to DB if newer
    if version_list is not None and len(version_list) > 0:
        new_version = add_new_version(version_list)

    # Return data
    return_data = json_builder(
        None, 2, limit,
        new_version is not None, new_version
        )
    return json_response(return_data)


def actions(request, params):
    return HttpResponse('actions')
