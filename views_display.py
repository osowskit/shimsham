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
    payload.update(data)
    url = in_url + endpoint
    try:
        r = requests.get(url, params=payload, timeout=10)
        request_data = r.json()
    except:
        request_data = {}
    return request_data

def getUsername(access_token):
    endpoint = '/user/info/'
    url = settings.UNTAPPD_API_URL
    data = get_untappd_api(url, endpoint, None, {}, access_token)
    return data['response']['user']['username']

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
    return HttpResponseRedirect('/')
    
def oauth(request):
    # code is returned from Untappd Oauth to this page
    code = request.GET.get('code', None)
    stored_user = None

    username = request.session.get('username', None)
    if username is not None:
        stored_user = getUserToken(username)

        # If we have a username and they have a token, use it
        if stored_user is not None:
            request.session['access_token'] = stored_user.access_token
            return render(request, 'ifttt/dashboard.html', {'username':username} )

    if code is None:
        url = getCodeURL()
        return HttpResponseRedirect(url)

    # If we have a code, we should get new token and store it
    if code is not None:
        response = getToken(str(code))
        return HttpResponse(str(response))
        access_token = None
        if 'response' in response:
            if 'access_token' in response['response']:
                access_token = response['response']['access_token']

                if username is None:
                    username = getUsername(access_token)
                addUserToken(username, access_token)
                return render(request, 'ifttt/dashboard.html', {'username':username} )

    print_str = '%s %s' % (code, username)
    return HttpResponseBadRequest()
