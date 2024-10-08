"""
Collect Wikipedia images
"""

from backend.lib.processor import BasicProcessor
from extensions.wikitools.wikipedia_scraper import WikipediaSearch
from common.lib.exceptions import (
    QueryParametersException,
    QueryNeedsExplicitConfirmationException,
)
from common.lib.helpers import UserInput

from bs4 import BeautifulSoup


class SearchWikiImages(BasicProcessor, WikipediaSearch):
    """
    Scrape Wikipedia images
    """

    type = "wikimages-search"  # job ID
    category = "Search"  # category
    title = "Wikipedia Cross-Lingual Image Analysis"  # title displayed in UI
    description = "Retrieve images for Wikipedia pages in many languages."  # description displayed in UI
    extension = "html"  # extension of result file, used internally and in UI

    # not available as a processor for existing datasets
    accepts = [None]

    options = {
        "intro": {
            "type": UserInput.OPTION_INFO,
            "help": "For a given Wikipedia URL, retrieve all other languages that article exists in, and then all "
            "images used on all language versions of that article. Images are displayed side by side to allow "
            "for visual comparison of the articles, in the order they appear in in the original article.",
        },
        "urls": {
            "type": UserInput.OPTION_TEXT,
            "help": "Article URL",
            "tooltip": "E.g. 'https://en.wikipedia.org/wiki/Man_in_Business_Suit_Levitating_emoji'",
        },
    }

    def process(self):
        """
        Retrieve revisions

        :param dict query:  Search query parameters
        """

        html = """
        <!DOCTYPE html>
        <head>
          <title>Wikipedia Cross-Lingual Image Analysis &#8226; {url}</title>
          <style>
            h1, h2 { background: #363636; color: white; padding: 0.4em 0.25em 0.25em 0.25em; }
            html { font-family: sans-serif; background: white; color: #363636; white-space: nowrap }
            img { max-height: 125px; }
            a { color: inherit; }
            nav { font-weight: bold; }
            td { background: #eff0f3; padding: 0.25em; }
            *[title] { border-bottom: 1px dashed #363636; cursor: help; }
          </style>
        </head>
        <body>
          <h1>Wikipedia Cross-Lingual Image Analysis</h1>
          <nav>Navigate: <a href="#per-article">Images per article</a> &#8226; <a href="#per-image">Articles per image</a></nav>
          <h2 id="per-article">Images per article version</h2>
          <table>
          <tr>
            <th>Page</th>
            <th>Language</th>
            <th>Images</th>
          </tr> 
                """

        wiki_apikey = self.config.get("api.wikipedia")
        urls = [url.strip() for url in self.parameters.get("urls").split("\n")]
        urls = [url for url in urls if url][0]
        num_images = 0

        image_map = {}
        all_languages = []
        url_map = {}
        for language, pages in self.normalise_pagenames(wiki_apikey, [urls]).items():
            page = pages.pop()
            lang_api = f"https://api.wikimedia.org/core/v1/wikipedia/{language}/page/{page.replace(' ', '_')}/links/language"

            languages = self.wiki_request(wiki_apikey, lang_api)
            if not languages:
                self.dataset.update_status(
                    f"Cannot get language versions for page {page} - may not exist, skipping"
                )
                continue

            languages.insert(0, {"title": page, "code": language})
            self.dataset.update_status(
                f"Found {len(languages)} language versions for Wikipedia page {page}"
            )

            languages_done = 0
            for language_version in languages:
                page = language_version["title"]
                page_language = language_version["code"]
                page_url = f"https://{page_language}.wikipedia.org/wiki/{page}"

                api_base = f"https://{page_language}.wikipedia.org/w/api.php"
                languages_done += 1
                self.dataset.update_status(
                    f"Getting images for article {page} ({self.map_lang(page_language)}/{page_language})"
                )
                self.dataset.update_progress(languages_done / len(languages))

                # get the image URLs from the page source
                # since that is the most reliable source of image order
                image_urls = self.wiki_request(
                    wiki_apikey,
                    api_base,
                    params={"action": "parse", "page": page, "format": "json"},
                )

                if not image_urls:
                    self.dataset.update_status(
                        f"Cannot get images for article {page} for language '{page_language}' - skipping"
                    )
                    continue

                all_languages.append(page_language)
                dom = BeautifulSoup(image_urls["parse"]["text"]["*"], "html.parser")
                images = dom.find_all("img")

                html += f"""
                <tr>
                  <td><a href="https://{page_language}.wikipedia.org/wiki/{page}">{page}</a></td>
                  <td><span title="{page_language}">{self.map_lang(page_language)}</span></td>
                  <td>"""

                for image in images:
                    num_images += 1
                    image_url = image["src"]
                    image_filename = image_url.split("/")[-2]
                    if image_url.startswith("//"):
                        image_url = "https:" + image_url

                    if image_filename not in image_map:
                        image_map[image_filename] = set()

                    image_map[image_filename].add(page_url)
                    url_map[image_filename] = image_url

                    html += f'<a href="https://{page_language}.wikipedia.org/wiki/File:{image_filename}"><img src="{image_url}" alt=""></a>'
                html += """
    </td>
  </tr>
"""
        html += "</table>"

        html += """
  <h2 id="per-image">Article versions per image</h2>
  <table>
  <tr>
    <th>Image</th>
    <th>Occurrences</th>
"""
        for language in all_languages:
            html += f'<th><a href="https://{language}.wikipedia.org"><span title="{self.map_lang(language)}">{language}</span></a></th>'
        html += "</tr>"

        image_map = {
            k: image_map[k]
            for k in sorted(image_map, key=lambda v: len(image_map[v]), reverse=True)
        }

        for image, languages in image_map.items():
            available_languages = {l.split("/")[2].split(".")[0]: l for l in languages}
            html += f'<tr><td><a href="https://{list(available_languages.keys())[0]}.wikipedia.org/wiki/File:{image}"><img src="{url_map[image]}" alt=""></a></td>'
            html += f"<td>{len(available_languages):,}</td>"
            for language in all_languages:
                html += "<td>"
                if language in available_languages:
                    html += f'<a href="{available_languages[language]}">&times;</a>'
                html += "</td>"
        html += "</tr></table></body>"

        with self.dataset.get_results_path().open("w") as outfile:
            outfile.write(html)

        return self.dataset.finish(num_images)

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
            raise QueryParametersException("You need to provide a valid Wikipedia URL")

        urls = [url.strip() for url in query.get("urls").split("\n")]
        urls = [[url for url in urls if url][0]]

        return {"urls": query.get("urls").strip()}
