from django.views.generic import ListView
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.conf import settings
from ifttt.models import UntappdBeer, User
from django.utils.http import urlencode
import requests

class UntappdBeerList(ListView):
    model = UntappdBeer

def get_untappd_api(in_url, endpoint='venue/checkins/3282',
                    headers=None, data={}, access_token=None):
    request_data = {}
    payload = {}
    
    if access_token is None:
        payload = {
            'client_id': settings.UNTAPPD_API_CLIENT_ID,
            'client_secret': settings.UNTAPPD_API_SECRET,
            }
    else:
        payload = {
            'access_token': access_token
            }
    payload.update(data)
    url = in_url + endpoint
    try:
        r = requests.get(url, params=payload, timeout=10)
        request_data = r.json()
    except:
        request_data = {}
    return request_data

def getAPIUserInfo(access_token):
    endpoint = '/user/info/'
    url = settings.UNTAPPD_API_URL
    data = get_untappd_api(url, endpoint, None, {}, access_token)
    return data


def getAPIWishlist(access_token):
    endpoint = '/user/wishlist'
    url = settings.UNTAPPD_API_URL
    data = get_untappd_api(url, endpoint, None, {}, access_token)
    #if data['response'].has_key('pagination'):
    #    if data['response']['pagination'].has_key('next_url'):
    #        url = data['response']['pagination']['next_url')]
    #        endpoint = ""
    #        next_data = get_untappd_api(url, endpoint, None, {}, access_token)
    return data


def getAPIBeerActivity(access_token, wish_bid_list):
    data = []
    for bid in wish_bid_list:
        endpoint = '/beer/checkins/' + str(bid)
        url = settings.UNTAPPD_API_URL
        data.append(get_untappd_api(url, endpoint, None, {}, access_token))
    return data


# WAT this should return None if bad response
def getUsername(data):
    return data['response']['user']['user_name']


def getUserStats(data):
    return data['response']['user']['stats']


def getUserWishlistBID(data):
    return_list = []
    for beer in data['response']['beers']['items']:
        return_list.append(beer['beer']['bid'])
    return return_list


def getUserWishlist(data):
    return_list = {}
    for beer in data['response']['beers']['items']:
        return_list.update( {
                beer['brewery']['brewery_name']:beer['beer']['beer_name']
            }
        )
    return return_list


def getBeerAcitivy(data):
    return_list = {}
    counter = 0
    for item in data:
        item_list = {}
        for checkin in item['response']['checkins']['items']:
            if len(checkin['venue']) > 0:
                if checkin['venue']['public_venue'] == True:
                    item_list.update({
                            checkin['venue']['venue_name']: "%s, %s" % (
                                    checkin['venue']['location']['venue_city'],
                                    checkin['venue']['location']['venue_state']
                                )
                        }
                    )
        beer_name = checkin['beer']['beer_name']
        return_list[beer_name] = item_list
        counter = counter + 1
    return return_list


# Add or update Token
def addUserToken(username, token):
    returned_entry = getUserToken(username)
    if returned_entry is None:
        entry = User(username=username,
                     access_token=token
                     )
        entry.save()
    else:
        returned_entry.access_token = token
        returned_entry.save()


def getUserToken(username):
    entry = None
    try:
        entry = User.objects.get(username=username)
    except:
        entry = None
    return entry


def getToken(code):
    url_param = {
            'response_type':'code',
            'redirect_url':'http://osowskit.com/auth/',
            'code':code
        }
    endpoint =  'oauth/authorize/'
    response = get_untappd_api(
        'https://untappd.com/',
        endpoint,
        data=url_param
    )
    return response


def getCodeURL():
    url_param = {
        'client_id': settings.UNTAPPD_API_CLIENT_ID,
        'response_type':'code',
        'redirect_url':'http://osowskit.com/auth/',
    }
    endpoint = 'oauth/authenticate/'
    url = "%s%s?%s" % (
        'https://untappd.com/',
        endpoint,
        urlencode(url_param),
    )
    return url


def clear_token(request):
    if 'username' in request.session:
        del request.session['username']
        request.session.modified = True
    if 'access_token' in request.session:
        del request.session['access_token']
        request.session.modified = True
    return HttpResponseRedirect('/')


def returnStats(request, access_token, username):
    data = getAPIUserInfo(access_token)
    user_stats = getUserStats(data)

    wish_data = getAPIWishlist(access_token)
    wish_list = getUserWishlist(wish_data)

    wish_bid_list = getUserWishlistBID(wish_data)
    wish_location_data = getAPIBeerActivity(access_token, wish_bid_list)
    wish_checkins = getBeerAcitivy(wish_location_data)

    return render(request, 'ifttt/dashboard.html',
                  {
                      'username':username,
                      'user_stats':user_stats,
                      'wish_list':wish_list,
                      'wish_checkins':wish_checkins,
                    }
                )
    
    
def oauth(request):
    # code is returned from Untappd Oauth to this page
    code = request.GET.get('code', None)
    stored_user = None

    username = request.session.get('username', None)
    access_token = request.session.get('access_token', None)
    if username is not None and access_token is not None:
        return returnStats(request, access_token, username)
    
    # Somehow no access token
    if username is not None:
        stored_user = getUserToken(username)

        # If we have a username and they have a token, use it
        if stored_user is not None:
            request.session['access_token'] = stored_user.access_token
            return returnStats(request, access_token, username)

    if code is None:
        url = getCodeURL()
        return HttpResponseRedirect(url)

    # If we have a code, we should get new token and store it
    if code is not None:
        response = getToken(str(code))

        access_token = None
        if 'response' in response:
            if 'access_token' in response['response']:
                access_token = response['response']['access_token']
                
                if username is None:
                    data = getAPIUserInfo(access_token)
                    username = getUsername(data)

                request.session['access_token'] = access_token
                request.session['username'] = username
                request.session.updated = True

                addUserToken(username, access_token)
                return returnStats(request, access_token, username)

    print_str = '%s %s' % (code, username)
    return HttpResponseBadRequest()
