from django.core.exceptions import ObjectDoesNotExist
from django.utils.encoding import smart_text
from ifttt.models import BeerOnTapEvent, BeerList
from bs4 import BeautifulSoup, NavigableString

import requests
import time
from datetime import datetime
import pytz
import uuid


def get_iso_date():
    return datetime.now(pytz.utc).replace(microsecond=0).isoformat('T')


def create_beer_on_tap_record(brewery_name, beer_name, venue, removed=False):
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


def get_beer_event_records(limit, names):
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


def get_beer_list_city():
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
def __process_data(r):
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


def get_beer_in_list(venue):
    beer_list = BeerList.objects.filter(
        venue=venue
        ).values_list('brewery_name', 'beer_name')
    return beer_list


def get_beer_list(location):
    beer_list = __get_beer_website(location)
    return __process_data(beer_list)


def create_beer_in_list(brewery_name, beer_name, venue):
    new_event = BeerList(
        brewery_name=brewery_name,
        beer_name=beer_name,
        venue=venue)
    new_event.save()


def remove_beer_in_list(brewery_name, beer_name, venue):
    beer = BeerList.objects.filter(
        brewery_name=brewery_name,
        beer_name=beer_name,
        venue=venue
        )
    beer.delete()
