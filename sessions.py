#!/bin/env python3

import argparse
import os
import phpserialize
import re
import sys
import json

import uaxtractor


TLD_PATTERN = re.compile(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|[^.]+)\.(.*)')
IP_ADDRESS_PATTERN = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')

sessions = []
requests = []
virtual_sessions = {}
crawler_ids = {}
final_sessions = []


def get_tld(hostname: str) -> str:
    return TLD_PATTERN.match(hostname).group(2)


def is_ip_address(hostname: str) -> bool:
    return IP_ADDRESS_PATTERN.match(hostname) is not None


def get_crawler_id(session) -> str:
    hostname = session['history'][len(session['history']) - 1]['host']
    if hostname is None or hostname == '':
        hostname = session['history'][len(session['history']) - 1]['address']
    if type(hostname) != str:
        print(session, file=sys.stderr)
    if is_ip_address(hostname):
        p = hostname.rfind('.')
        tld = hostname[:p]
    else:
        tld = get_tld(hostname)
    # version = session['uax']['software']['name'] + '/' + session['uax']['software']['version']
    return f'{tld}#{session["useragent"]}'


def get_bot_session_id(session) -> str:
    cid = get_crawler_id(session)
    for sess_id, sess in virtual_sessions.items():
        if get_crawler_id(sess) == cid:
            for nr, req in sess['history'].items():
                if abs(req['timestamp'] - session['history'][len(session['history']) - 1]['timestamp']) < 60 * 60:
                    return sess_id
    return session['sess_id']


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('sess_dir', type=str)
    args = parser.parse_args()
    for filename in os.listdir(args.sess_dir):
        if not filename.startswith('sess_'):
            continue
        with open(f'{args.sess_dir}/{filename}', 'rb') as f:
            sess_id = filename[5:]
            session = phpserialize.loads(f.read(), decode_strings=True)
            session['uax'] = uaxtractor.parse_user_agent(session['useragent'])
            session['sess_id'] = sess_id
            sessions.append(session)
            for nr, req in session['history'].items():
                req['session'] = sess_id
                req['req_nr'] = nr
                requests.append(req)

    sessions.sort(key=lambda s: s['last'])
    requests.sort(key=lambda r: r['timestamp'])

    for sess in sessions:
        sess_id = sess['sess_id']
        if sess['uax']['category'] in ('crawler', 'preview'):
            cid = get_crawler_id(sess)
            if cid not in crawler_ids:
                crawler_ids[cid] = sess_id
                virtual_sessions[sess_id] = sess
            else:
                v_sess = virtual_sessions[crawler_ids[cid]]
                v_sess['visits'] += sess['visits']
                v_sess['last'] = max(v_sess['last'], sess['last'])
                for nr, req in sess['history'].items():
                    v_sess['history'][len(v_sess['history'])] = req
        elif sess['visits'] == 1:
            bsid = get_bot_session_id(sess)
            if bsid in virtual_sessions:
                v_sess = virtual_sessions[bsid]
                v_sess['visits'] += sess['visits']
                v_sess['last'] = max(v_sess['last'], sess['last'])
                for nr, req in sess['history'].items():
                    v_sess['history'][len(v_sess['history'])] = req
            else:
                virtual_sessions[sess_id] = sess
        else:
            virtual_sessions[sess_id] = sess

    for sess_id, sess in virtual_sessions.items():
        history = []
        for nr, req in sess['history'].items():
            history.append(req)
        history.sort(key=lambda r: r['timestamp'])
        sess['history'] = history

    for sess_id, sess in virtual_sessions.items():
        final_sessions.append(sess)

    final_sessions.sort(key=lambda s: s['last'])

    print(json.dumps(final_sessions))

    #for sess in final_sessions:
    #    creation = datetime.datetime.utcfromtimestamp(sess['creation'])
    #    last = datetime.datetime.utcfromtimestamp(sess['last'])
    #    print(f'{sess["sess_id"]} '
    #          f'{creation.strftime("%Y-%m-%d (%H:%M)")}  {last.strftime("%Y-%m-%d (%H:%M)")}'
    #          f'{sess["visits"]:4} {sess["user"] if "user" in sess else "-":8} '
    #          f'{sess["uax"]["category"]:10} '
    #          f'{(sess["uax"]["os"]["name"] or "-") + " " + (sess["uax"]["os"]["version"] or ""):16} '
    #          f'{(sess["uax"]["browser"]["name"] or "-") + " " + (sess["uax"]["browser"]["version"] or ""):20} '
    #          f'{(sess["uax"]["software"]["name"] or "-") + " " + (sess["uax"]["software"]["version"] or ""):32} '
    #          f'{sess["history"][-1]["host"]} ({sess["history"][-1]["address"]}) ')
