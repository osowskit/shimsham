from django.views.generic import ListView
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings
from ifttt.models import UntappdBeer, User
from django.utils.http import urlencode
import requests

class UntappdBeerList(ListView):
    model = UntappdBeer


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

def oauth(request):
    # search for CODE
    code = request.GET.get('code', None)
    # If not None call Authorize 
    stored_user = None
    username = request.POST.get('username', None)

    # If we have a username and they have a token, use it
    if username is not None:
        request.session['username'] = username
        stored_user = getUserToken(username)
        if stored_user is not None:
            request.session['access_token'] = stored_user.access_token
            return render(request, 'ifttt/dashboard.html', {'username':username} )
    else:
        username = request.session.get('username', None)
        if username is None:
            return HttpResponseRedirect('/')

    if code is None:
        url = getCodeURL()
        return HttpResponseRedirect(url)

    # If we have a code, we should get new token and store it
    if code is not None and username is not None:
        response = getToken(str(code))
        access_token = None
        if 'response' in response:
            if 'access_token' in response['response']:
                access_token = response['response']['access_token']
                addUserToken(username, access_token)
                return render(request, 'ifttt/dashboard.html', {'username':username} )

    print_str = '%s %s' % (code, username)
    return HttpResponse(print_str)
