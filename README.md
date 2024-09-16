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

All data sources use the Wikipedia API to collect data. An API key can be configured in the 4CAT control panel's 
"Settings" page. Things will also work without an API key, but with a lower rate limit (meaning processors may fail 
with heavy use).

## Installation
In 4CAT, navigate to the extensions folder, and check out this repository there as 'wikitools'. **Note**: the name of 
the extensions folder **must** be `wikitools` (not `4cat-wikitools`):

```shell
cd [4cat root]
cd extensions
git clone https://github.com/digitalmethodsinitiative/4cat-wikitools.git wikitools
```

If you restart 4CAT, the data sources will be available. You still need to enable them via the control panel.

If you want to enable geolocation of revision authors, you need to put the `GeoLite2-City.mmdb` file from the 
[MaxMind](https://www.maxmind.com/en/solutions/ip-geolocation-databases-api-services) GeoIP database in the folder's 
root (i.e. `wikitools`). This file can be downloaded for free but we cannot redistribute it. More information on how to
download this file [here](https://support.maxmind.com/hc/en-us/articles/4408216157723-Database-Formats).

## Credits & license
The 4CAT Wikipedia tools extension was developed by Stijn Peeters for the [Digital Methods 
Initiative](https://digitalmethods.net) and is licensed under the Mozilla Public License, 2.0. Refer to the LICENSE 
file for more information. The original versionso of these tools were developed by Koen Martens and Erik Borra for the 
DMI.