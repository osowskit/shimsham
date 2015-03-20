from django.contrib import admin
from ifttt.models import VersionUpdateEvent, WebsiteUnavailableEvent, BeerOnTapEvent, BeerList

admin.site.register(VersionUpdateEvent)
admin.site.register(WebsiteUnavailableEvent)

#admin.site.register(BeerList)
# Register your models here.

#class BeerOnTapEventAdmin(admin.ModelAdmin):
#    fields = ['brewery_name', 'beer_name', 'venue']

#class BeerListAdmin(admin.ModelAdmin):
#    fields = ['brewery_name', 'beer_name', 'venue']

admin.site.register(BeerList)
admin.site.register(BeerOnTapEvent)
