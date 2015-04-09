from django.core.exceptions import ObjectDoesNotExist
from ifttt.models import VersionUpdateEvent
import xml.etree.ElementTree as ET

import requests
import time
import uuid

def __version_from_xml_response(xml_data):
    root = ET.fromstring(xml_data)
    return_data = {}
    if root is not None:
        new_versions = root.findall('./version/*')
        for elem in new_versions:
            return_data[elem.tag] = elem.text
    return return_data


def get_version_url(url, user_agent):
    my_data = None
    header = {'User-Agent': user_agent}
    try:
        r = requests.get(url, headers=header)
    
        if r.status_code == 200 and r.headers['content-type'] == 'xml':
            xml_data = r.content
            my_data = __version_from_xml_response(xml_data)
    except requests.exceptions.RequestException as e:
        return [{'error':e}]
    return my_data


def get_iso_date():
    return datetime.now(pytz.utc).replace(microsecond=0).isoformat('T')


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
        trigger_name="update_available",
        meta_id=meta_list['id'],
        meta_timestamp=meta_list['timestamp'],
        created_at=recipe_list['created_at'],
        version_number=recipe_list['version_number']
        )
    new_event.save()


# Return a version string if it is newer than customer value. None otherwise.
def add_new_version(version_list):
    # Iterate list and add to DB if it doesn't exist
    for version_name, value in version_list.iteritems():
        try:
            VersionUpdateEvent.objects.get(
                version_number=value)
        except VersionUpdateEvent.DoesNotExist:
            __create_version_update_record(value)


def get_update_records(limit=50):
    recipe_list = []
    object_list = VersionUpdateEvent.objects.order_by(
        '-meta_timestamp'
        )[:limit]
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
