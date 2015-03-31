from django.contrib import admin
from ifttt.models import VersionUpdateEvent, \
    WebsiteUnavailableEvent, \
    BeerOnTapEvent, \
    BeerList, \
    UntappdBeer, \
    Venue, \
    UntappdBeerOnTapEvent

admin.site.register(VersionUpdateEvent)
admin.site.register(WebsiteUnavailableEvent)
admin.site.register(UntappdBeerOnTapEvent)
admin.site.register(BeerList)
admin.site.register(BeerOnTapEvent)
admin.site.register(UntappdBeer)
admin.site.register(Venue)
