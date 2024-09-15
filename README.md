# 4CAT Wikipedia tools extension

An extension for [4CAT](https://4cat.nl) with three Wikipedia-related data sources:

* **Wikipedia Cross-Lingual Image Comparison**: For a given Wikipedia article, get all language versions of that 
  article. Then extract all images from all articles. Visually compare which images appear in which articles, and in 
  what order. Do all versions use the same imagery to illustrate the same topic?
* **Wikipedia revision scraper**: Collect metadata for all revisions of a given (set of) Wikipedia article(s). 
  Optionally, anonymous revisions' IP addresses can be geolocated. From what area of the world is an article being 
  edited? What sections receive the most attention?
* **Wikipedia TOC scraper**: Collect the tables of contents (TOCs) of historical versions of a Wikipedia article. How 
  does the table of contents evolve over time? Which sections appear and which disappear?

All data sources use the Wikipedia API to collect data. To use geolocation features, a (free) API key for the
[Abstract](https://www.abstractapi.com/api/ip-geolocation-api) geolocation API is required. Optionally, a Wikimedia API
access token can be provided to speed up requests. These API keys are configured in the 4CAT control panel's "Settings"
page.

## Credits & license
The 4CAT Wikipedia tools extension was developed by Stijn Peeters for the [Digital Methods 
Initiative](https://digitalmethods.net) and is licensed under the Mozilla Public License, 2.0. Refer to the LICENSE 
file for more information. The original versionso of these tools were developed by Koen Martens and Erik Borra for the 
DMI.