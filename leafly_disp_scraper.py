import sys
import urlparse

from runner import run
from disp_filter import *
from leafly_helpers import *
from httpclient import HttpClient


class LeaflyDispensaryScraper(object):
    def __init__(self, dispensary_filter, http_client, leafly_details_extractor):
        self._dispensary_filter = dispensary_filter
        self._http_client = http_client
        self._details_extractor = leafly_details_extractor
        self._url = 'https://www.leafly.com/finder/{}'
        self._api_url = 'https://web-finder.leafly.com/finder/search?slug={}'
        self._data = {'Take': 1000, 'Page': 0}

    def produce(self, state_name):
        url_list = None
        response = self._http_client.get(self._api_url.format(state_name))
        if response.success:
            content = re.compile(r'__NEXT_DATA__ = (.*);__NEXT_LOADED_PAGES__=').search(response.content).group(1)
            json_data = loadJson(content)
            zipcode = json_data.get('props').get('pageProps').get('zip')
            state = json_data.get('props').get('pageProps').get('stateName')

            r = self._http_client.get(self._url.format(state))
            if r.success:
                tree_html = html.fromstring(r.content)
                url_list = tree_html.xpath("//div[contains(@class, 'view-menu')]//a/@href")

            itemsLst = try_get_list(json_data.get('props').get('pageProps'), 'dispensaries')
            if len(itemsLst) > 0:
                for i, item in enumerate(itemsLst[0]):
                    cityLst = try_get_list(item, 'city')
                    if len(cityLst) > 0:
                        if self._dispensary_filter.match_city(cityLst[0]):
                            item['UrlName'] = None
                            if url_list and url_list[i]:
                                item['UrlName'] = '/'.join(url_list[i].split('/')[:-1])
                            item['zip'] = zipcode
                            item['state'] = state
                            item['Latitude'] = item.get('location', {}).get('lat')
                            item['Longitude'] = item.get('location', {}).get('lon')
                            yield self.get_partial_dispensary(item)

    def consume(self, item_from_produce):
        url = try_get_list(item_from_produce, 'url')
        if url and url[0]:
            url = url[0]
        else:
            return item_from_produce

        absoluteUrl = urlparse.urljoin('https://www.leafly.com/dispensary-info/', url)
        item_from_produce['about_dispensary'] = self._details_extractor.get_about_info(absoluteUrl)
        item_from_produce['menu'] = self._details_extractor.get_menu_info(item_from_produce['dispensary_id'])
        item_from_produce['url'] = 'https://www.leafly.com' + item_from_produce['url']
        return item_from_produce

    def get_partial_dispensary(self, json_data):
        paths = {'url': 'UrlName',
                 'rating': 'star_rating',
                 'reviews_count': 'number_of_reviews',
                 'name': 'name',
                 'city': 'city',
                 'phone_number': 'phone',
                 'hours_of_operation': 'weekly_schedule',
                 'state': 'state',
                 'latitude': 'Latitude',
                 'longitude': 'Longitude',
                 'avatar_url': 'cover_image_url',
                 'zip_code': 'zip',
                 'address': 'address1',
                 'dispensary_id' :'dispensary_id'}

        result = {}
        fill_obj(result, json_data, paths)
        return result

def scrape(arr):
    dispFilter = get_dispensary_filter(arr)
    leaflyScraper = LeaflyDispensaryScraper(dispFilter, HttpClient(), LeaflyDetailsExtractor(HttpClient()))
    result = run(dispFilter.get_state_names(), leaflyScraper.produce, leaflyScraper.consume)

    return json.dumps(result)

if __name__ == "__main__":
    print (scrape(sys.argv[1:]))