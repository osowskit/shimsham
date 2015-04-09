from django.core.exceptions import ObjectDoesNotExist
from ifttt.models import WebsiteUnavailableEvent

import requests
import time
from datetime import datetime
import pytz
import uuid

def __new_website_status(status, user_url):
    try:
        last_event = WebsiteUnavailableEvent.objects.filter(
            web_url=user_url
            ).order_by('-meta_timestamp').first()
        if last_event.status_code != str(status):
            return True
    except:
        # assume list is empty
        return True
    return False


def get_iso_date():
    return datetime.now(pytz.utc).replace(microsecond=0).isoformat('T')


def get_website_event_records(limit=50, user_url=None):
    recipe_list = []
    object_list = WebsiteUnavailableEvent.objects.filter(
        web_url=user_url
        ).order_by('-meta_timestamp')[:limit]
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
        trigger_name="website_down",
        meta_id=meta_list['id'],
        meta_timestamp=meta_list['timestamp'],
        occurred_at=recipe_list['occurred_at'],
        status_code=recipe_list['status_code'],
        web_url=recipe_list['web_url'],
    )
    new_event.save()


def update_website_status(status, user_url):
    # get DB status, fixed
    has_changed = __new_website_status(status, user_url)

    # if status doesn't match
    if has_changed:
        #   create new event -
        __create_website_unavailable_record(status, user_url)
