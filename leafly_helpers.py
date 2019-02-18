from lxml import html
from utils import HtmlUtils
from httpclient import HttpClient
import re
from jsonutils import *

class LeaflyDetailsExtractor(object):

    def __init__(self, http_client):
        self._http_client = http_client

    def get_menu_info(self, dispensary_id):
        menu_items = self._menu_items(dispensary_id)
        all_items = map(self._get_menu_item_info, menu_items)
        categories = {}
        for item in all_items:
            if item['category'] not in categories:
                categories[item['category']] = []
            categories[item['category']].append(item)
        return categories

    def get_about_info(self, url):
        response = self._http_client.get(url)
        if response.success:
            html_doc = html.fromstring(response.content)
            return HtmlUtils.get_element_value(html_doc, "//div[@class='store-about']/text()")
        return ''


    def _menu_items(self, dispensary_id):     
        url = 'https://web-dispensary.leafly.com/api/menu/' + str(dispensary_id)
        page = 1
        should_continue = True
        while should_continue:
            response = self._http_client.post(url, json.dumps(self._post_menu_body(page)), headers={'Content-Type' : 'application/json'})
            should_continue = response.success
            if response.success:
                response_obj = loadJson(response.content)
                menu = self._get_first_or_empty(try_get_list(response_obj, 'menu'))
                should_continue = len(menu) > 0
                for item in menu:
                    yield item
                page = page + 1

    def _post_menu_body(self, page):
        body = {
                    "categories": [
                    ],
                    "priceRange": {
                    },
                    "quantity": 0,
                    "thcRange": {
                    },
                    "cbdRange": {
                    },
                    "page": page
                } 

        return body

    def _get_menu_item_info(self, item):
        result = {}
        result['name'] = self._get_first_or_empty(try_get_list(item, 'name'))
        result['description'] = self._get_first_or_empty(try_get_list(item, 'description'))
        result['category'] = self._get_first_or_empty(try_get_list(item, 'category'))
        result['imageUrl'] = ''
        image_url = self._get_first_or_empty(try_get_list(item, 'imageUrl'))

        if image_url and image_url.startswith('http'):
            result['imageUrl'] = image_url

        result['strain'] = self._get_menu_item_strain(item)
        result['brand'] = self._get_menu_item_brand(item)

        pricesLst = try_get_list(item, 'variants')
        if len(pricesLst) > 0:
            result['prices'] = [p for p in map(self._get_menu_item_prices, pricesLst[0]) if p]
        else:
            result['prices'] = []

        return result

    def _get_menu_item_strain(self, json_data):
        result = {}
        result['name'] = self._get_first_or_empty(try_get_list(json_data, 'strainName'))

        strainSlug = self._get_first_or_empty(try_get_list(json_data, 'strainSlug'))
        strainCategory = self._get_first_or_empty(try_get_list(json_data, 'strainCategory'))

        if strainSlug and strainCategory:
            result['url'] = 'https://www.leafly.com/{0}/{1}'.format(strainCategory.lower(), strainSlug)
        else:
            result['url'] = ''
        return result

    def _get_menu_item_brand(self, json_data):
        result = {}
        result['name'] = self._get_first_or_empty(try_get_list(json_data, 'brandName'))

        brandSlug = self._get_first_or_empty(try_get_list(json_data, 'brandSlug'))

        if brandSlug:
            result['url'] = 'https://www.leafly.com/brands/{0}'.format(brandSlug)
        else:
            result['url'] = ''
        return result

    def _get_menu_item_prices(self, json_data):
        result = {}
        quantity = self._get_first_or_empty(try_get_list(json_data, 'packageDisplayUnit'))
        price = self._get_first_or_empty(try_get_list(json_data, 'packagePrice'))

        if quantity and price:
            result['price'] = price
            result['quantity'] = quantity
        return result

    def _get_first_or_empty(self, lst):
        return lst[0] if len(lst) > 0  else ''
