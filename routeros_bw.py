#!/usr/bin/env python3
"""
./routeros_bw.py <router_ip>

requires the 'requests' package

See https://wiki.mikrotik.com/wiki/Manual:IP/Accounting for how to
configure IP Accounting *AND* web access.

"""
import time
import curses
import requests
import ipaddress
import socket
import sys
from collections import defaultdict

ROUTER_HOSTNAME = sys.argv[1]


def get_stats():
    url = "http://%s/accounting/ip.cgi" % ROUTER_HOSTNAME
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.text.splitlines()
    data = [l.split() for l in data if l]
    # just [src, dst, bytes]
    data = [l[:2] + [float(l[2])] for l in data]
    # sum bytes by ip
    rv = defaultdict(int)
    for src, dst, bytes in data:
        rv[src] += bytes
        rv[dst] += bytes
    rv = {ip: bytes for ip, bytes in rv.items()
          if ipaddress.ip_address(ip).is_private}
    return dict(rv)


def main(print_fn, cb_end=None):
    hist = defaultdict(list)  # bits keyed by ip
    n = 0
    window = 3

    def output():
        for ip in sorted(hist, key=lambda x: socket.inet_aton(x)):
            h  = hist[ip]
            if sum(h) and len(h):
                avg_bps = sum(h) / len(h)
            else:
                avg_bps = 0
            print_fn("%s: %.0f kbps\n" % (ip, avg_bps / 1024))
        
    
    while True:
        n += 1
        data = get_stats()
        for ip, bits in data.items():
            hist[ip].append(bits)
            if n > window:
                hist[ip] = hist[ip][-window:]
        if n > window:
            n = 0
        output()
        if cb_end:
            cb_end()
        time.sleep(1)


def main_window(stdscr):
    def cb():
        stdscr.clear()

    def print_fn(s):
        stdscr.addstr(s)
        stdscr.refresh()

    main(print_fn=print_fn, cb_end=cb)

    stdscr.refresh()
    stdscr.getkey()


curses.wrapper(main_window)

