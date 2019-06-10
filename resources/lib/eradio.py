# -*- coding: utf-8 -*-

'''
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

from __future__ import absolute_import

import json
from functools import partial
from tulip import bookmarks, directory, client, cache, control
from tulip.compat import unicode, iteritems
from tulip.cleantitle import strip_accents


class Indexer:

    def __init__(self):

        self.list = []; self.data = []
        self.base_link = 'http://eradio.mobi'
        self.image_link = 'http://cdn.e-radio.gr/logos/{0}'
        self.all_link = 'http://eradio.mobi/cache/1/1/medialist.json'
        self.trending_link = 'http://eradio.mobi/cache/1/1/medialistTop_trending.json'
        self.popular_link = 'http://eradio.mobi/cache/1/1/medialist_top20.json'
        self.new_link = 'http://eradio.mobi/cache/1/1/medialist_new.json'
        self.categories_link = 'http://eradio.mobi/cache/1/1/categories.json'
        self.regions_link = 'http://eradio.mobi/cache/1/1/regions.json'
        self.category_link = 'http://eradio.mobi/cache/1/1/medialist_categoryID{0}.json'
        self.region_link = 'http://eradio.mobi/cache/1/1/medialist_regionID{0}.json'
        self.resolve_link = 'http://eradio.mobi/cache/1/1/media/{0}.json'

    def root(self):

        radios = [
            {
                'title': control.lang(32001),
                'action': 'radios',
                'url': self.all_link,
                'icon': 'all.png'
            }
            ,
            {
                'title': control.lang(32002),
                'action': 'bookmarks',
                'icon': 'bookmarks.png'
            }
            ,
            {
                'title': control.lang(32006),
                'action': 'search',
                'icon': 'search.png'
            }
            ,
            {
                'title': control.lang(32003),
                'action': 'radios',
                'url': self.trending_link,
                'icon': 'trending.png'
            }
            ,
            {
                'title': control.lang(32004),
                'action': 'radios',
                'url': self.popular_link,
                'icon': 'popular.png'
            }
            ,
            {
                'title': control.lang(32005),
                'action': 'radios',
                'url': self.new_link,
                'icon': 'new.png'
            }
        ]

        categories = cache.get(self.directory_list, 24, self.categories_link)

        if categories is None:
            return

        for i in categories:
            i.update({'icon': 'categories.png', 'action': 'radios'})

        regions = cache.get(self.directory_list, 24, self.regions_link)

        if regions is None:
            return

        for i in regions:
            i.update({'icon': 'regions.png', 'action': 'radios'})

        dev_picks_list = [{'title': control.lang(32503), 'action': 'dev_picks', 'icon': 'recommended.png'}]

        self.list = radios + dev_picks_list + categories + regions

        directory.add(self.list, content='files')

    def search(self):

        input_str = control.inputDialog()

        if not input_str:
            return

        items_list = [
            i for i in self.radios(self.all_link, return_listing=True) if strip_accents(input_str.lower()) in i['title'].lower()
        ]

        if not items_list:
            return

        control.sortmethods('title')

        del self.list

        directory.add(items_list, infotype='Music')

    def bookmarks(self):

        self.list = bookmarks.get()

        if self.list is None:
            return

        for i in self.list:

            bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
            bookmark['delbookmark'] = i['url']
            i.update({'cm': [{'title': 32502, 'query': {'action': 'deleteBookmark', 'url': json.dumps(bookmark)}}]})

        self.list = sorted(self.list, key=lambda k: k['title'].lower())

        directory.add(self.list, infotype='Music')

    def radios(self, url, return_listing=False):

        self.list = cache.get(self.radios_list, 1, url)

        if self.list is None:
            return

        for i in self.list:
            i.update({'action': 'play', 'isFolder': 'False'})

        if url == self.all_link:

            self.list.extend(cache.get(self._devpicks, 6))

        for i in self.list:

            bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
            bookmark['bookmark'] = i['url']
            i.update({'cm': [{'title': 32501, 'query': {'action': 'addBookmark', 'url': json.dumps(bookmark)}}]})

        control.sortmethods('title')

        if return_listing:
            return self.list
        else:
            directory.add(self.list, infotype='Music')

    def _devpicks(self):

        xml = client.request('http://alivegr.net/raw/radios.xml')

        items = client.parseDOM(xml, 'station', attrs={'enable': '1'})

        for item in items:

            name = unicode(client.parseDOM(item, 'name')[0])
            logo = client.parseDOM(item, 'logo')[0]
            url = client.parseDOM(item, 'url')[0]

            self.data.append({'title': name, 'image': logo, 'url': url, 'action': 'dev_play', 'isFolder': 'False'})

        return self.data

    def dev_picks(self):

        self.list = cache.get(self._devpicks, 6)

        if self.list is None:
            return

        for i in self.list:
            bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
            bookmark['bookmark'] = i['url']
            i.update({'cm': [{'title': 32501, 'query': {'action': 'addBookmark', 'url': json.dumps(bookmark)}}]})

        directory.add(self.list, infotype='Music')

    def play(self, url, do_not_resolve=False):

        if not do_not_resolve:

            resolved = self.resolve(url)
    
            if resolved is None:
                return
    
            title, url, image = resolved
    
            directory.resolve(url, {'title': title}, image)
            
        else:

            directory.resolve(url)

    def directory_list(self, url):

        try:

            self.list = []

            result = client.request(url, mobile=True)
            result = json.loads(result)

            if 'categories' in result:
                items = result['categories']
            elif 'countries' in result:
                items = result['countries']

        except:

            return

        for item in items:

            try:

                if 'categoryName' in item:
                    title = item['categoryName']
                elif 'regionName' in item:
                    title = item['regionName']
                title = client.replaceHTMLCodes(title)

                if 'categoryID' in item:
                    url = self.category_link.format(str(item['categoryID']))
                elif 'regionID' in item:
                    url = self.region_link.format(str(item['regionID']))
                url = client.replaceHTMLCodes(url)

                self.list.append({'title': title, 'url': url})

            except:

                pass

        return self.list

    def radios_list(self, url):

        try:

            result = client.request(url, mobile=True)
            result = json.loads(result)

            items = result['media']

        except:

            return

        for item in items:

            try:

                title = item['name'].strip()
                title = client.replaceHTMLCodes(title)

                url = str(item['stationID'])
                url = client.replaceHTMLCodes(url)

                image = item['logo']
                image = self.image_link.format(image)
                image = image.replace('/promo/', '/500/')

                if image.endswith('/nologo.png'):
                    image = '0'

                image = client.replaceHTMLCodes(image)

                self.list.append({'title': title, 'url': url, 'image': image})

            except:

                pass

        return self.list

    def resolve(self, url):

        try:

            url = self.resolve_link.format(url)

            result = client.request(url, mobile=True)
            result = json.loads(result)

            item = result['media'][0]

            url = item['mediaUrl'][0]['liveURL']

            if not url.startswith('http://'):
                url = '{0}{1}'.format('http://', url)

            url = client.replaceHTMLCodes(url)

            # url = client.request(url, output='geturl')

            title = item['name'].strip()
            title = client.replaceHTMLCodes(title)

            image = item['logo']
            image = self.image_link.format(image)
            image = image.replace('/promo/', '/500/')

            if image.endswith('/nologo.png'):
                image = '0'

            image = client.replaceHTMLCodes(image)

            return title, url, image

        except:

            pass
