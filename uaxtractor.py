#!/bin/env python3

from typing import Dict
import argparse
import re
import json

BROWSER_PATTERN = re.compile(r'([A-Za-z0-9]+)/((\d+)(\.\d+)*)')
MACOS_PATTERN = re.compile(r'Mac OS X (\d+)_(\d+)_(\d+)')
IOS_PATTERN = re.compile(r'iPhone OS (\d+)_(\d+)')

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


def _parse_parenthesis(data: str, obj: Dict) -> Dict:
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
        if dev[0] in WIN_VER:
            obj['os']['name'] = 'Windows'
            obj['os']['version'] = WIN_VER[dev[0]]
        else:
            obj['os']['name'] = dev[0]
    elif dev[0] == 'X11':
        obj['device']['type'] = 'desktop',
        obj['device']['mobile'] = False
        obj['os']['family'] = 'linux'
        if 'Ubuntu' in dev:
            obj['os']['name'] = 'Ubuntu'
        elif 'Fedora' in dev:
            obj['os']['name'] = 'Fedora'
    elif dev[0] == 'Linux' and (dev[1].startswith('Android') or dev[2].startswith('Android')):
        obj['device']['type'] = 'smartphone'
        obj['device']['mobile'] = True
        if dev[1].startswith('Android'):
            d = dev[1]
        else:
            d = dev[2]
        # obj['device']['name'] = dev[2]
        obj['os']['family'] = 'android'
        obj['os']['name'] = 'Android'
        ver = d[8:]
        p = ver.find('.')
        if p == -1:
            obj['os']['version'] = ver
        else:
            obj['os']['version'] = ver[:ver.find('.')]
    elif dev[0].startswith('Android'):
        obj['device']['type'] = 'smartphone'
        obj['device']['mobile'] = True
        obj['os']['family'] = 'android'
        obj['os']['name'] = 'Android'
        ver = dev[0][8:]
        p = ver.find('.')
        if p == -1:
            obj['os']['version'] = ver
        else:
            obj['os']['version'] = ver[:ver.find('.')]
    elif dev[0] == 'Macintosh':
        obj['device']['type'] = 'desktop'
        obj['device']['mobile'] = False
        obj['os']['family'] = 'macos'
        obj['os']['name'] = 'macOS'
        for d in dev:
            m = MACOS_PATTERN.search(d)
            if m:
                obj['os']['version'] = m.group(1) + '.' + m.group(2)
                break
            else:
                obj['os']['version'] = None
    elif dev[0] == 'iPhone':
        obj['device']['type'] = 'smartphone'
        obj['device']['mobile'] = True
        obj['os']['family'] = 'ios'
        obj['os']['name'] = 'iOS'
        for d in dev:
            m = IOS_PATTERN.search(d)
            if m:
                obj['os']['version'] = m.group(1)
                break
            else:
                obj['os']['version'] = None
    elif dev[0] == 'compatible':
        p1 = dev[1].find('/')
        if dev[1].startswith('MSIE '):
            obj['device']['type'] = 'desktop'
            obj['device']['mobile'] = False
            obj['os']['family'] = 'windows'
            if dev[2] in WIN_VER:
                obj['os']['name'] = 'Windows'
                obj['os']['version'] = WIN_VER[dev[2]]
            else:
                obj['os']['name'] = WIN_VER[dev[2]]
            obj['browser']['name'] = 'Internet Explorer'
            v = dev[1][5:]
            obj['browser']['version'] = v[:v.find('.')]
            obj['browser']['fullversion'] = v
        elif p1 >= 0:
            obj['software']['name'] = dev[1][:p1]
            obj['software']['version'] = dev[1][p1 + 1:]
        else:
            obj['software']['name'] = dev[1]
        if obj['software']['name'] in ('Googlebot', 'DuckDuckGo-Favicons-Bot', 'Baiduspider', 'CensysInspect') or obj['software']['name'] and 'crawler' in obj['software']['name'].lower():
            obj['category'] = 'crawler'
        elif obj['software']['name'] and obj['software']['name'] in ('Discordbot'):
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

    return obj


def _parse_browser(data: str, obj: Dict) -> Dict:
    brs = {}
    last = None
    n = 0
    for m in BROWSER_PATTERN.finditer(re.sub(r'\(.*?\)', '', data)):
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
    if 'Safari' in brs and 'Chrome' not in brs and 'CrMo' not in brs:
        if 'Version' in brs:
            name = 'Safari'
            idx = 'Safari'
            brs[idx]['fullversion'] = brs['Version']['fullversion']
            brs[idx]['version'] = brs['Version']['version']
    elif 'Chrome' in brs:
        name = 'Chrome'
        idx = 'Chrome'
    elif 'CrMo' in brs:
        name = 'Chrome'
        idx = 'CrMo'
    else:
        name = last
        idx = last

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

    return obj


def parse_user_agent(ua: str) -> Dict[str, str]:
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

    if type(ua) != str:
        obj['category'] = 'none'
        return obj

    if ua.startswith('Mozilla/'):
        obj['category'] = 'browser'
        p2 = 0
        while True:
            p1 = ua.find('(', p2)
            if p1 < 0:
                break
            p2 = ua.find(')', p1)
            obj = _parse_parenthesis(ua[p1 + 1:p2], obj)
        obj = _parse_browser(ua, obj)

    elif ua.startswith('Lynx/'):
        obj['software']['name'] = 'Lynx'
        obj['software']['version'] = ua[5:ua.find(' ')]
    elif ua.startswith('Python-urllib/'):
        obj['software']['name'] = 'Python'
        obj['software']['version'] = None
        obj['software']['libname'] = 'urllib'
        obj['software']['libversion'] = ua[14:]
    elif ua.startswith('Python/'):
        obj['software']['name'] = 'Python'
        p1 = ua.find(' ')
        p2 = ua.find('/', p1)
        obj['software']['version'] = ua[7:p1]
        obj['software']['libname'] = ua[p1:p2]
        obj['software']['libversion'] = ua[p2 + 1:]
    elif ua.startswith('WhatsApp/'):
        obj['category'] = 'preview'
        obj['software']['name'] = 'WhatsApp'
        obj['software']['version'] = ua[9:ua.find(' ')]
    elif ua.startswith('TelegramBot'):
        obj['category'] = 'preview'
        obj['software']['name'] = 'TelegramBot'
    elif ua.startswith('curl/'):
        obj['software']['name'] = 'curl'
        obj['software']['version'] = ua[5:]
    elif ua.startswith('libwww-perl/'):
        obj['software']['name'] = 'perl'
        obj['software']['libname'] = 'libwww'
        obj['software']['libversion'] = ua[12:]
    elif ua.startswith('python-requests'):
        obj['software']['name'] = 'Python'
        obj['software']['libname'] = 'requests'
        obj['software']['libversion'] = ua[16:]
    elif ua.startswith('Go-http-client/'):
        obj['software']['name'] = 'Go'
        obj['software']['libname'] = 'http-client'
        obj['software']['libversion'] = ua[15:]
    elif ua.startswith('Googlebot-Image/'):
        obj['category'] = 'crawler'
        obj['software']['name'] = 'Googlebot-Image'
        obj['software']['version'] = ua[16:]
    elif ua == 'Go http package':
        obj['software']['name'] = 'Go'
        obj['software']['libname'] = 'http package'
    elif ua == 'Microsoft Windows Network Diagnostics':
        obj['software']['name'] = ua
    elif ua.startswith('Java/'):
        obj['software']['name'] = 'Java'
        v = ua[5:]
        p = v.find('_')
        if p != -1:
            v = v[:p]
        obj['software']['version'] = v
    else:
        obj['category'] = 'other'

    if obj['software']['version'] == '':
        obj['software']['version'] = None
    if obj['software']['libversion'] == '':
        obj['software']['libversion'] = None

    return obj


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('ua_string', type=str)
    args = parser.parse_args()
    print(json.dumps(parse_user_agent(args.ua_string)))
