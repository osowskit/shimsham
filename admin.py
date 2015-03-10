from django.contrib import admin
from ifttt.models import VersionUpdateEvent, WebsiteUnavailableEvent

admin.site.register(VersionUpdateEvent)
admin.site.register(WebsiteUnavailableEvent)
# Register your models here.
