from django.core.exceptions import ObjectDoesNotExist
from django.utils.http import urlencode
from ifttt.models import Venue

import requests
import time
from datetime import datetime
import pytz
import uuid


def get_iso_date():
    return datetime.now(pytz.utc).replace(microsecond=0).isoformat('T')


def __create_venue_untappd(data):
    new_event = Venue(
        venue_name=data['venue_name'],
        venue_uid=data['venue_uid'],
        last_checkin_id=data['last_checkin_id'],
        venue_social_name=data['venue_social_name'],
        )
    new_event.save()


def __get_venue_info(venue_name):
    venue_list = Venue.objects.filter(venue_name=venue_name).values()
    return venue_list


def update_venue_last_checkin(venue_uid, highest_checkin):
    venue_entry = Venue.objects.get(venue_uid=venue_uid)
    venue_entry.last_checkin_id = highest_checkin
    venue_entry.save()


def get_venue_id(venue_name):
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
        # WAT - should not hardcode search to first result
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


def parse_untappd_venue_activity(venue_activity_list):
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
