# shimsham
Api Shim for finding out what beer is on tap while being notified via IFTTT.  Data is sourced from Untappd via OAuth2 integration.  Also utilizes Google Analytics, New Relic, and Python to parse HTML information from websites.
## Introduction
Django app that provides an API endpoint for IFTTT notification services.  IFTTT will regularly poll various endpoint for a list of stored events - not realtime.  
## API endpoint and channels
The IFTTT endpoint will route traffic through a single API.  It will post data to specific Triggers
### Untappd Updates
Functionality - Enter a Venue name and receive a notification if a new, unique beer is checked in.
### Website Down - Retired
Functionality - Enter a FQDN to monitor and get notified if the status changes.
### Beer On Tap
Functionality - Monitor either The Trappist or City Beer Store for changes to their tap list.  If a Brewery you enter has something added, IFTTT will trigger a notification.
### Beer Updates
Functionality - Get notified if either The Trappist or City Beer Store updates their tap list
