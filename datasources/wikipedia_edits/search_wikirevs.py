"""
Collect Wikipedia revisions
"""
import geoip2.database
import datetime
import re

from backend.lib.search import Search
from extensions.wikitools.wikipedia_scraper import WikipediaSearch
from common.lib.helpers import UserInput
from common.lib.item_mapping import MappedItem
from common.lib.exceptions import QueryParametersException, ProcessorInterruptedException
from pathlib import Path

class SearchWikiRevisions(Search, WikipediaSearch):
    """
    Scrape Wikipedia article revisions
    """
    type = "wikirevs-search"  # job ID
    category = "Search"  # category
    title = "Wikipedia revisions scraper"  # title displayed in UI
    description = "Retrieve metadata for Wikipedia revisions."  # description displayed in UI
    extension = "ndjson"  # extension of result file, used internally and in UI

    # not available as a processor for existing datasets
    accepts = [None]

    options = {
        "intro": {
            "type": UserInput.OPTION_INFO,
            "help": "For a given list of Wikipedia page URLs, retrieve a number of revisions of those pages and their"
                    "metadata. This allows for analysis of how actively an article is edited, and by whom.\n\n"
                    "Note that not all historical versions of a page may be available; for example, if the page has "
                    "been deleted its contents can no longer be retrieved."
        },
        "rvlimit": {
            "type": UserInput.OPTION_TEXT,
            "help": "Number of revisions",
            "min": 1,
            "max": 25000,
            "coerce_type": int,
            "default": 50,
            "tooltip": "Number of revisions to collect per page. Cannot be more than 500. Note that pages may have "
                       "fewer revisions than the upper limit you set."
        },
        "urls": {
            "type": UserInput.OPTION_TEXT_LARGE,
            "help": "Article URLs",
            "tooltip": "E.g. 'https://en.wikipedia.org/wiki/Man_in_Business_Suit_Levitating_emoji'. Put each URL on a "
                       "separate line."
        },
        "geolocate": {
            "type": UserInput.OPTION_TOGGLE,
            "help": "Attempt to geolocate anonymous edits",
            "tooltip": "Uses the [MaxMind](https://www.maxmind.com/en/solutions/ip-geolocation-databases-api-services) "
                       "GeoIP database to locate anonymous users based on their IP address. Note that locations may be "
                       "inaccurate and or unavailable for certain IP addresses."
        }
    }

    config = {
        "api.wikipedia": {
            "type": UserInput.OPTION_TEXT_LARGE,
            "help": "Wikipedia Access Token",
            "tooltip": "API key for the Wikimedia API. With an API key, more requests can be made per minute, which "
                       "will speed up Wikipedia-based data sources."
        }
    }

    @classmethod
    def get_options(cls, parent_dataset=None, user=None):
        """
        Get processor options

        Only offer geolocation if a geolocation database is present.

        :param DataSet parent_dataset:  Dataset that will be uploaded
        :param User user:  User that will be uploading it
        :return dict:  Option definition
        """
        options = cls.options.copy()
        geoip_database = Path(__file__).absolute().joinpath("../../../GeoLite2-City.mmdb").resolve()

        if not geoip_database.exists():
            del options["geolocate"]

        return options


    def get_items(self, query):
        """
        Retrieve revisions

        :param dict query:  Search query parameters
        """
        urls = [url.strip() for url in self.parameters.get("urls").split("\n")]
        urls = [url for url in urls if url]
        wiki_apikey = self.config.get("api.wikipedia")
        geoip_database = Path(__file__).absolute().joinpath("../../../GeoLite2-City.mmdb").resolve()
        geolocator = None
        if geoip_database.exists():
            geolocator = geoip2.database.Reader(geoip_database)

        location_cache = {}

        num_pages = 0
        num_revisions = 0
        for language, pages in self.normalise_pagenames(wiki_apikey, urls).items():
            for page in pages:
                num_pages += 1

                # get revisions from API
                rvlimit = self.parameters.get("rvlimit")
                page_revisions = self.get_revisions(wiki_apikey, language, page, rvlimit)

                if not page_revisions:
                    continue

                self.dataset.update_status(
                    f"Collected {len(page_revisions):,} revisions for article '{page}' on {language}.wikipedia.org")

                for revision in page_revisions:
                    location = ""

                    # geolocate only anonymous requests
                    if "anon" in revision and geolocator:
                        if revision["user"] in location_cache:
                            location = location_cache[revision["user"]]
                        else:
                            geo = geolocator.city(revision["user"])
                            location = f"{geo.country.iso_code} / {geo.country.name} / {geo.subdivisions.most_specific.name} / {geo.city.name}"
                            location_cache[revision["user"]] = location

                    yield {
                        "title": page,
                        "language": language,
                        "location": location,
                        **revision
                    }
                    num_revisions += 1

        if geolocator:
            geolocator.close()
        self.dataset.update_status(f"Retrieved {num_revisions:,} revisions for {num_pages:,} page(s)", is_final=True)

    @staticmethod
    def validate_query(query, request, user):
        """
        Validate input for a dataset query

        Will raise a QueryParametersException if invalid parameters are
        encountered. Parameters are additionally sanitised.

        :param dict query:  Query parameters, from client-side.
        :param request:  Flask request
        :param User user:  User object of user who has submitted the query
        :return dict:  Safe query parameters
        """
        if not query.get("urls").strip():
            raise QueryParametersException("You need to provide at least one Wikipedia article URL")

        return {
            "urls": query.get("urls").strip(),
            "rvlimit": query.get("rvlimit"),
            "geolocate": query.get("geolocate")
        }

    @staticmethod
    def map_item(item):
        """
        Map collected item

        :param item:  Item collected
        :return MappedItem:  Item mapped for display in CSV files, etc
        """
        timestamp = datetime.datetime.strptime(item["timestamp"], "%Y-%m-%dT%H:%M:%SZ")

        section = ""
        if re.match(r"/\* ([^*]+) \*/", item.get("comment", "")):
            # this is not foolproof, but a nice extra bit of info
            section = re.findall(r"/\* (.*) \*/", item["comment"])[0]

        return MappedItem({
            "id": item["revid"],
            "thread_id": item.get("parentid"),
            "page": item["title"],
            "language": item["language"],
            "url": f"https://{item['language']}.wikipedia.org/w/index.php?title={item['title'].replace(' ', '_')}&oldid={item['revid']}",
            "author": item["user"],
            "author_anonymous_location": item.get("location", ""),
            "is_anonymous": "yes" if "anon" in item else "no",
            "is_minor_edit": "yes" if "minor" in item else "no",
            "is_probably_bot": "yes" if item["user"].lower().endswith("bot") else "no", # not foolproof, still useful
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "section": section,
            "body": item.get("comment", ""),
            "unix_timestamp": int(timestamp.timestamp())
        })
