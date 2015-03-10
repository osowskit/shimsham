from django.db import models

# Create your models here.
class TriggerEvent(models.Model):
    TRIGGER_NAMES = (
        ('notification_this_month', 'blog notifications'),
        ('website_down', 'website unavailable'),
        ('update_available', 'update'),
    )
    trigger_name = models.CharField(max_length=80, choices=TRIGGER_NAMES)
    meta_id = models.CharField(max_length=100)
    meta_timestamp = models.CharField(max_length=40)
    class Meta:
        abstract = True
    
class VersionUpdateEvent(TriggerEvent):
    created_at = models.DateTimeField()
    version_number = models.CharField(max_length=25)

class WebsiteUnavailableEvent(TriggerEvent):
    occurred_at = models.DateTimeField()
    status_code = models.CharField(max_length=3)
    fixed = models.BooleanField(default=False)
    web_url = models.CharField(max_length=200, default='https://getvisualizer.com')
