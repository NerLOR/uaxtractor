#!/bin/env python3

import argparse
import re
import json

BROWSER_PATTERN = re.compile(r'([A-Za-z0-9]+)/((\d+)(\.\d+)+)')

WIN_VER = {
    'Windows ME': 'ME',
    'Win16': '3.11',
    'Windows 95': '95',
    'Win95': '95',
    'Windows_95': '95',
    'Windows 98': '98',
    'Win98': '98',
    'Windows NT 5.0': '2000',
    'Windows 2000': '2000',
    'Windows NT 5.1': 'XP',
    'Windows XP': 'XP',
    'Windows NT 5.2': 'Server 2003',
    'Windows NT 6.0': 'Vista',
    'Windows NT 6.1': '7',
    'Windows NT 6.2': '8',
    'Windows NT 6.3': '8',
    'Windows NT 10.0': '10'
}

obj = {
    'category': 'other',  # other, browser, crawler, preview, bot
    'device': {
        'type': None,
        'brand': None,
        'name': None,
        'version': None,
        'mobile': None
    },
    'os': {
        'family': None,
        'name': None,
        'version': None
    },
    'browser': {
        'name': None,
        'version': None,
        'fullversion': None,
        'engine': None
    },
    'software': {
        'name': None,
        'version': None,
        'libname': None,
        'libversion': None
    }
}


def parse_parenthesis(data: str):
    dev = [part.strip() for part in data.split(';')]
    if dev[0] == 'Windows':
        for d in dev:
            if d != 'Windows' and d.startswith('Windows'):
                dev[0] = d
                break
    if dev[0].startswith('Windows'):
        obj['device']['type'] = 'desktop'
        obj['device']['mobile'] = False
        obj['os']['family'] = 'windows'
        obj['os']['name'] = 'Windows'
        obj['os']['version'] = WIN_VER[dev[0]]
    elif dev[0] == 'X11':
        obj['device']['type'] = 'desktop',
        obj['device']['mobile'] = False
        obj['os']['family'] = 'linux'
        if 'Ubuntu' in dev:
            obj['os']['name'] = 'Ubuntu'
    elif dev[0] == 'Linux' and dev[1].startswith('Android'):
        obj['device']['type'] = 'smartphone'
        obj['device']['mobile'] = True
        obj['device']['name'] = dev[2]
        obj['os']['family'] = 'android'
        obj['os']['name'] = 'Android'
        ver = dev[1][8:]
        obj['os']['version'] = ver[:ver.find('.')]
    elif dev[0] == 'Macintosh':
        obj['device']['type'] = 'desktop'
        obj['device']['mobile'] = False
        obj['os']['family'] = 'macos'
        obj['os']['name'] = 'macOS'
        obj['os']['version'] = None
    elif dev[0] == 'iPhone':
        obj['device']['type'] = 'smartphone'
        obj['device']['mobile'] = True
        obj['os']['family'] = 'ios'
        obj['os']['name'] = 'iOS'
        obj['os']['version'] = None
        # TODO
    elif dev[0] == 'compatible':
        p1 = dev[1].find('/')
        if p1 >= 0:
            obj['software']['name'] = dev[1][:p1]
            obj['software']['version'] = dev[1][p1 + 1:]
        else:
            obj['software']['name'] = dev[1]
        if obj['software']['name'] in ('Googlebot', 'DuckDuckGo-Favicons-Bot') or 'crawler' in obj['software']['name'].lower():
            obj['category'] = 'crawler'
        elif obj['software']['name'] in ('Discordbot'):
            obj['category'] = 'preview'
        else:
            obj['category'] = 'bot'
    if obj['os']['family'] == 'windows':
        for d in dev:
            if d.startswith('Trident/'):
                obj['browser']['name'] = 'Internet Explorer'
                obj['browser']['engine'] = 'trident'
            elif d.startswith('rv:'):
                obj['browser']['version'] = d[3:d.find('.')]
                obj['browser']['fullversion'] = d[3:]


def parse_browser(data: str):
    brs = {}
    last = None
    n = 0
    for m in BROWSER_PATTERN.finditer(data):
        browser = m.group(1)
        fullversion = m.group(2)
        version = m.group(3)
        if browser == 'Mozilla':
            continue
        n += 1
        if n > 1:
            brs[browser] = {'fullversion': fullversion, 'version': version}
            last = browser

    name = None
    idx = None

    if 'Safari' in brs and 'Chrome' not in brs:
        name = 'Safari'
        idx = 'Safari'
    elif 'Chrome' in brs:
        name = 'Chrome'
        idx = 'Chrome'

    if name == 'Chrome' and last not in ('Chrome', 'Safari'):
        idx = last
        if last in ('Edge', 'Edg'):
            name = 'Edge'
        elif last == 'OPR':
            name = 'Opera'
        else:
            name = last

    if name:
        obj['browser']['name'] = name
        br = brs[idx]
        obj['browser']['fullversion'] = br['fullversion']
        obj['browser']['version'] = br['version']


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('ua_string', type=str)
    args = parser.parse_args()
    ua = args.ua_string

    if ua.startswith('Mozilla/'):
        obj['category'] = 'browser'
        p2 = 0
        while True:
            p1 = ua.find('(', p2)
            if p1 < 0:
                break
            p2 = ua.find(')', p1)
            parse_parenthesis(ua[p1 + 1:p2])
        parse_browser(ua)

    elif ua.startswith('Lynx/'):
        obj['software']['name'] = 'lynx'
        obj['software']['version'] = ua[5:ua.find(' ')]
    elif ua.startswith('Python-urllib/'):
        obj['software']['name'] = 'python'
        obj['software']['version'] = None
        obj['software']['libname'] = 'urllib'
        obj['software']['libversion'] = ua[14:]
    elif ua.startswith('Python/'):
        obj['software']['name'] = 'python'
        p1 = ua.find(' ')
        p2 = ua.find('/', p1)
        obj['software']['version'] = ua[7:p1]
        obj['software']['libname'] = ua[p1:p2]
        obj['software']['libversion'] = ua[p2 + 1:]
    elif ua.startswith('WhatsApp/'):
        obj['category'] = 'preview'
        obj['software']['name'] = 'whatsapp'
        obj['software']['version'] = ua[9:ua.find(' ')]
    elif ua.startswith('curl/'):
        obj['software']['name'] = 'curl'
        obj['software']['version'] = ua[5:]
    elif ua.startswith('libwww-perl/'):
        obj['software']['name'] = 'perl'
        obj['software']['libname'] = 'libwww'
        obj['software']['libversion'] = ua[12:]
    elif ua.startswith('python-requests'):
        obj['software']['name'] = 'python'
        obj['software']['libname'] = 'requests'
        obj['software']['libversion'] = ua[16:]
    else:
        obj['category'] = 'other'

    print(json.dumps(obj))
