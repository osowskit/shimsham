# shimsham
Api Shim for IFTTT
## Introduction
Django app that provides an API endpoint for IFTTT notification services.  IFTTT will regularly poll various endpoint for a list of stored events - not realtime.  
## API endpoint and channels
The IFTTT endpoint will route traffic through a single API.  It will post data to specific Triggers
### Website Down
Functionality - Enter a FQDN to monitor and get notified if the status changes.
### Beer On Tap
Functionality - Monitor either The Trappist or City Beer Store for changes to their tap list.  If a Brewery you enter has something added, IFTTT will trigger a notification.
### Beer Updates
Functionality - Get notified if either The Trappist or City Beer Store updates their tap list
