from django.core.exceptions import ObjectDoesNotExist
from ifttt.models import UntappdBeerOnTapEvent, UntappdBeer

import requests
import time
from datetime import datetime
import pytz
import uuid


def get_iso_date():
    return datetime.now(pytz.utc).replace(microsecond=0).isoformat('T')


def create_untappd_beer_on_tap_record(
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


def get_untappd_event_records(limit, venue_name):
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


def process_untappd_beer_list(beer_list, venue_data):
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
