from django.db import models


# Create your models here.
class TriggerEvent(models.Model):
    TRIGGER_NAMES = (
        ('notification_this_month', 'blog notifications'),
        ('website_down', 'website unavailable'),
        ('update_available', 'update'),
        ('beer_on_tap', 'beer_available'),
        ('untapped_beer_on_tap', 'untapped_beer_available'),
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
    web_url = models.CharField(
        max_length=200,
        default='https://getvisualizer.com'
        )


class BeerEvent(TriggerEvent):
    created_at = models.DateTimeField()
    brewery_name = models.CharField(max_length=128)
    beer_name = models.CharField(max_length=128)
    venue = models.CharField(max_length=128)

    class Meta:
        abstract = True


class BeerOnTapEvent(BeerEvent):
    removed = models.BooleanField(default=False)

    def __unicode__(self):
        return '%s: %s at %s was removed %s' % (
            self.brewery_name,
            self.beer_name,
            self.venue,
            str(self.removed)
        )


class UntappdBeerOnTapEvent(BeerEvent):
    twitter_handle = models.CharField(max_length=128)

    def __unicode__(self):
        return '%s: %s at %s @%s' % (
            self.brewery_name,
            self.beer_name,
            self.venue,
            self.twitter_handle
            )


class Beer(models.Model):
    brewery_name = models.CharField(max_length=128)
    beer_name = models.CharField(max_length=128)
    venue = models.CharField(max_length=128)

    class Meta:
        abstract = True


class BeerList(Beer):

    def __unicode__(self):
        return '%s: %s at %s' % (
            self.brewery_name,
            self.beer_name,
            self.venue
            )


class Venue(models.Model):
    venue_uid = models.BigIntegerField()
    venue_name = models.CharField(max_length=256)
    last_checkin_id = models.BigIntegerField()
    venue_social_name = models.CharField(max_length=128)

    def __unicode__(self):
        return '%s: %s' % (
            self.venue_name,
            str(self.last_checkin_id)
            )


class UntappdBeer(Beer):
    last_seen = models.DateTimeField()
    beer_uid = models.BigIntegerField()
    venue_uid = models.BigIntegerField()
    brewery_id = models.BigIntegerField()
    checkin_id = models.BigIntegerField()

    def __unicode__(self):
        return '%s: %s at %s' % (
            self.brewery_name,
            self.beer_name,
            self.venue
            )
