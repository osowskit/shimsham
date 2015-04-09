from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.utils.encoding import smart_text
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

import json
import requests
from bs4 import BeautifulSoup, NavigableString

import time
from django.views.decorators.cache import never_cache
from django.utils.http import urlencode
from datetime import datetime
import pytz
import uuid
from ifttt.models import VersionUpdateEvent, BeerOnTapEvent, \
    BeerList, UntappdBeerOnTapEvent
from ifttt.models import UntappdBeer, Venue
from ifttt.VisualizerVersion import get_update_records, add_new_version, get_version_url
from ifttt.VisualizerWebsite import update_website_status, get_website_event_records

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
    return HttpResponse(
        response_data,
        content_type='application/json; charset=utf-8',
        status=in_status
        )


def __create_beer_in_list(brewery_name, beer_name, venue):
    new_event = BeerList(
        brewery_name=brewery_name,
        beer_name=beer_name,
        venue=venue)
    new_event.save()


def __remove_beer_in_list(brewery_name, beer_name, venue):
    beer = BeerList.objects.filter(
        brewery_name=brewery_name,
        beer_name=beer_name,
        venue=venue
        )
    beer.delete()


def __get_beer_in_list(venue):
    beer_list = BeerList.objects.filter(
        venue=venue
        ).values_list('brewery_name', 'beer_name')
    return beer_list


def __get_venue_info(venue_name):
    venue_list = Venue.objects.filter(venue_name=venue_name).values()
    return venue_list


def __create_venue_untappd(data):
    new_event = Venue(
        venue_name=data['venue_name'],
        venue_uid=data['venue_uid'],
        last_checkin_id=data['last_checkin_id'],
        venue_social_name=data['venue_social_name'],
        )
    new_event.save()


def __create_beer_in_untappd_list(
        brewery_name,
        brewery_id,
        beer_name,
        beer_id,
        venue,
        venue_id,
        checkin_id,
        last_seen
        ):
    new_event = UntappdBeer(
        brewery_name=brewery_name,
        brewery_id=brewery_id,
        beer_name=beer_name,
        beer_uid=beer_id,
        venue=venue,
        venue_uid=venue_id,
        checkin_id=checkin_id,
        last_seen=last_seen
    )
    new_event.save()


def __get_beer_in_untappd_list(venue_uid):
    beer_list = UntappdBeer.objects.filter(
        venue_uid=venue_uid
        ).values_list(
            'brewery_name',
            'beer_name',
            'last_seen',
            'checkin_id'
            )
    return beer_list


def __create_beer_on_tap_record(brewery_name, beer_name, venue, removed=False):
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
        trigger_name='beer_on_tap',
        meta_id=meta_list['id'],
        meta_timestamp=meta_list['timestamp'],
        created_at=event_list['created_at'],
        removed=event_list['removed'],
        brewery_name=event_list['brewery_name'],
        beer_name=event_list['beer_name'],
        venue=event_list['venue'],
    )
    new_event.save()


def __create_untappd_beer_on_tap_record(
        brewery_name,
        beer_name,
        venue,
        twitter_handle
        ):
    counter = str(uuid.uuid4())
    meta_list = {
        'id': counter,
        'timestamp': int(time.time())
    }
    event_list = {
        'created_at': get_iso_date(),
    }
    new_event = UntappdBeerOnTapEvent(
        trigger_name='untapped_beer_on_tap',
        meta_id=meta_list['id'],
        meta_timestamp=meta_list['timestamp'],
        created_at=event_list['created_at'],
        brewery_name=brewery_name,
        beer_name=beer_name,
        venue=venue,
        twitter_handle=twitter_handle
    )
    new_event.save()


def __get_untappd_event_records(limit, venue_name):
    event_list = []
    object_list = UntappdBeerOnTapEvent.objects.filter(
        venue__iexact=venue_name
        ).order_by(
        '-meta_timestamp'
        )[:limit]
    for beer_event in object_list:
        meta_list = {
            'id': beer_event.meta_id,
            'timestamp': beer_event.meta_timestamp,
        }
        returned_event = {
            'created_at': str(beer_event.created_at.isoformat('T')),
            'brewery_name': beer_event.brewery_name,
            'beer_name': beer_event.beer_name,
            'venue': beer_event.venue,
            'twitter_handle': beer_event.twitter_handle,
            'meta': meta_list
        }
        event_list.append(returned_event)
    return event_list


def __get_beer_event_records(limit, names):
    object_list = []
    event_list = []
    if names is not None:
        user_brewery_name = names[0]
        venue = names[1]

        object_list = BeerOnTapEvent.objects.filter(
            brewery_name__contains=user_brewery_name,
            venue__iexact=venue
        ).order_by('-meta_timestamp')[:limit]
    else:
        object_list = BeerOnTapEvent.objects.filter(
            removed=False
        ).order_by('-meta_timestamp')[:limit]

    for beer_event in object_list:
        meta_list = {
            'id': beer_event.meta_id,
            'timestamp': beer_event.meta_timestamp,
        }
        returned_event = {
            'created_at': str(beer_event.created_at.isoformat('T')),
            'brewery_name': beer_event.brewery_name,
            'beer_name': beer_event.beer_name,
            'venue': beer_event.venue.replace(" ", ""),
            'still_available': not beer_event.removed,
            'meta': meta_list
        }
        event_list.append(returned_event)
    return event_list


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
    elif action == 'user':
        return user_info(request)
    elif action == 'triggers':
        return triggers(request, params, limit, triggerFields)
    elif action == 'create':
        # __create_record()
        return HttpResponse('created something')
    elif action == 'show':
        val = __new_website_status(200)
        return HttpResponse(val)
    elif action == 'display':
        returned_records = get_update_records(limit)
        json_string = json.dumps(returned_records)
        return json_response(json_string)
    return HttpResponseBadRequest('No endpoint requested')


# status return 200
def status(request):
    return HttpResponse()


# test/setup
def test(request):
    json_string = static_json
    return HttpResponse(
        json_string,
        content_type='application/json; charset=utf-8'
        )


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


def json_builder(input_data, trigger_enum, limit,
                 new_values=False, value=None):
    data = {}
    data_list = []

    # generate three for fun
    num_records = 3
    if new_values:
        num_records = 4
    count = 0

    if trigger_enum == 2:
        data_list = get_update_records(limit)
    elif trigger_enum == 1:
        data_list = get_website_event_records(limit, input_data)
    elif trigger_enum == 3 or trigger_enum == 4:
        data_list = __get_beer_event_records(limit, input_data)
    elif trigger_enum == 5:
        data_list = __get_untappd_event_records(limit, input_data)
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
        return beer_on_tap(request, limit, triggerFields)
    elif params == 'beer_updates':
        return beer_updates(request, limit, triggerFields)
    elif params == 'untappd_updates':
        return untappd_updates(request, limit, triggerFields)
    return HttpResponse(params)


def user_info(request):

    user_info = {
        'name': 'anonymous',
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
    except:
        return brewery_list

    soup = BeautifulSoup(r.text)
    # Data is in the first 'ul' HTML element
    beerlist = soup.ul
    for beer in beerlist.children:
        # Only interate over Tag elements
        if type(beer) is not NavigableString:
            brewery_list.append(
                (
                    unicode(beer.select("div")[0].string),
                    unicode(beer.select("div")[1].string)
                )
            )

    return brewery_list


def __get_beer_website(in_url):
    try:
        r = requests.get(in_url, timeout=10)
        r.encoding = 'utf-8'
    except:
        return []
    return r


# trappist
def process_data(r):
    # Parse HTML document for beer names in two columns
    # soup = BeautifulSoup(open('Trappist.html'))
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
                        beer_names.append(
                            (
                                brewery_name,
                                beer_name
                            )
                        )
    return beer_names


def __get_beer_list(location):
    beer_list = __get_beer_website(location)
    return process_data(beer_list)


def __create_record():
    beer_list = __get_beer_list()
    for beer in beer_list:
        __create_beer_on_tap_record(beer[0], beer[1], 'City Beer Store')


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


def __update_venue_last_checkin(venue_uid, highest_checkin):
    venue_entry = Venue.objects.get(venue_uid=venue_uid)
    venue_entry.last_checkin_id = highest_checkin
    venue_entry.save()


def __get_venue_id(venue_name):
    # get venue id and last_checkin_id from DB or create new record
    untappd_api_version = 'v4/'

    venue_info = __get_venue_info(venue_name)
    venue_data = {}

    if len(venue_info) == 0:
        # search for it
        endpoint = 'search/venue?' + urlencode(
            {
                'q': venue_name
            }
            )
        returned_data = get_untappd_api(
            'https://api.untappd.com/' + untappd_api_version,
            endpoint
            )
        first_venue = returned_data['response']['venues']['items'][0]
        returned_venue = first_venue['venue']

        # get info using id
        endpoint = 'venue/info/' + str(returned_venue['venue_id'])
        returned_data = get_untappd_api(
            'https://api.untappd.com/' + untappd_api_version,
            endpoint
            )
        venue_info = returned_data['response']['venue']
        venue_data['venue_uid'] = returned_venue['venue_id']
        venue_data['venue_name'] = venue_info['venue_name']
        venue_data['venue_social_name'] = venue_info['contact']['twitter']
        venue_data['last_checkin_id'] = 0
        __create_venue_untappd(venue_data)
    else:
        venue_data['venue_uid'] = venue_info[0]['venue_uid']
        venue_data['last_checkin_id'] = venue_info[0]['last_checkin_id']
        venue_data['venue_name'] = venue_info[0]['venue_name']
        venue_data['venue_social_name'] = venue_info[0]['venue_social_name']
    return venue_data


def __parse_untappd_venue_activity(venue_activity_list):
    beer_list = []
    for checkin in venue_activity_list['response']['checkins']['items']:
        beer_info = {}
        beer_info['brewery_name'] = checkin['brewery']['brewery_name']
        beer_info['beer_name'] = checkin['beer']['beer_name']
        beer_info['beer_uid'] = checkin['beer']['bid']
        beer_info['brewery_id'] = checkin['brewery']['brewery_id']
        beer_info['checkin_id'] = checkin['checkin_id']
        beer_info['last_seen'] = get_iso_date()
        beer_list.append(beer_info)
    return beer_list


def __process_untappd_beer_list(beer_list, venue_data):
    added_list = []
    updated_list = []
    highest_checkin = 0
    for beer in beer_list:
        # Could assume first entry is highest checkin id
        highest_checkin = beer['checkin_id'] if beer['checkin_id'] > highest_checkin \
            else highest_checkin
        try:
            UntappdBeer.objects.get(
                beer_uid=beer['beer_uid'],
                venue_uid=venue_data['venue_uid']
                )
            # update it if checkin id
            updated_list.append(beer)
        except ObjectDoesNotExist:
            __create_beer_in_untappd_list(
                beer['brewery_name'],
                beer['brewery_id'],
                beer['beer_name'],
                beer['beer_uid'],
                venue_data['venue'],
                venue_data['venue_uid'],
                beer['checkin_id'],
                get_iso_date()  # Should use the date from Untappd Query
                )
            added_list.append(beer)
    return updated_list, added_list, highest_checkin


def untappd_updates(request, limit, triggerFields):

    if "venue_name" in triggerFields:
        venue_name = triggerFields['venue_name']
    else:
        data = {}
        value = {'message': 'Missing Trigger parameter for venue_name'}
        data['errors'] = [value]
        return json_response(json.dumps(data), 400)

    # lookup venue ID or search/create if it doesn't exist
    venue_data = __get_venue_id(venue_name)
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
    activity_beer_list = __parse_untappd_venue_activity(venue_activity_list)
    venue_activity_list = []

    # create or update beer information
    # return list of updated and created
    updated_list, created_list, highest_checkin = __process_untappd_beer_list(
        activity_beer_list,
        {
            'venue': venue_name,
            'venue_uid': venue_uid
        }
        )
    activity_beer_list = []
    # It is possible that there weren't any results
    if last_checkin < highest_checkin:
        __update_venue_last_checkin(venue_uid, highest_checkin)

    # return json_response(json.dumps(updated_list))
    for beer in created_list:
        __create_untappd_beer_on_tap_record(
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
        beer_list = __get_beer_list_city()
    else:
        beer_list = __get_beer_list('http://www.thetrappist.com/on-tap.php')

    # Get beer list stored in DB
    db_beer_list = __get_beer_in_list(venue_name)

    # Update DB
    for beer in beer_list:
        already_on_tap = (beer[0], beer[1]) in db_beer_list

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
    status = __get_website(url)

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


def notification_month(request, limit):
    data = json_builder(None, 0, limit)
    return json_response(data)


def actions(request, params):
    return HttpResponse('actions')
