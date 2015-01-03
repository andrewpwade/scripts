#!/usr/bin/env python
"""
Monitors your external IP as reported by jsonip.com and provides a
desktop notification when it changes.

Requires gem 'terminal-notifier' (sudo gem install terminal-notifier --no-ri --no-rdoc)

This can be run as a background job by creating file ~/Library/LaunchAgents/com.whatever.osx.mon_ext_ip.plist with contents:

<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC -//Apple Computer//DTD PLIST 1.0//EN http://www.apple.com/DTDs/PropertyList-1.0.dtd >
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>com.andrew.osx.test</string>
    <key>Program</key>
    <string>/Users/andrew/bin/monitor_ext_ip.py</string>
    <key>KeepAlive</key>
    <true/>
  </dict>
</plist>

and running:

  launchctl load ~/Library/LaunchAgents/com.whatever.osx.mon_ext_ip.plist
"""
import logging
import os
import re
import requests
import socket
import subprocess
import time

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log = logging.getLogger(os.path.basename(__file__))

def run(*args, **kwargs):
    log.debug("running: {}".format(args))
    out = subprocess.check_output(args, **kwargs)
    if out:
        log.debug("output of {}: {}".format(args, out.split("\n")))
    return out

def get_rdns(ip):
    try:
        log.debug("resolving rDNS for {}".format(ip))
        return socket.gethostbyaddr(ip)[0]
    except socket.error:
        return ""

def get_external_ip():
    try:
        log.debug("fetching IP from jsonip.com")
        req = requests.get("http://jsonip.com")
        ip = req.json()['ip']
        log.debug("external ip: {}".format(ip))
        return ip
    except (ValueError, requests.exceptions.RequestException):
        log.exception("Error getting IP")
        return ""

def get_default_iface():
    out = run("route", "-n", "get", "default")
    m = re.search('^\s+interface: (.+)$', out, re.MULTILINE)
    if not m or not m.group(1):
        return ""
    return m.group(1)

def notify(msg):
    run("terminal-notifier", "-message", "", "-title", "Ext IP","-subtitle", msg)

def main():
    verbose = "VERBOSE" in os.environ
    log.setLevel(logging.DEBUG if verbose else logging.INFO)

    FETCH_INTERVAL = 60
    prev_ext_ip = ""
    ext_ip = get_external_ip()
    default_gw = get_default_iface()
    prev_default_gw = ""
    last_fetch = 0.0

    while True:
        time_since = int(time.time()-last_fetch)
        default_gw = get_default_iface()
        if (not last_fetch) or (time_since > FETCH_INTERVAL) or (prev_default_gw and default_gw != prev_default_gw):
            log.info("Fetching external IP...")
            ext_ip = get_external_ip()
            log.debug("external ip reported as: %s", ext_ip)
            if not ext_ip:
                time.sleep(1)
                continue
            hostname = get_rdns(ext_ip)
            last_fetch = time.time()

        if prev_ext_ip and prev_ext_ip != ext_ip:
            message = "{} ({})".format(ext_ip, default_gw)
            log.info("External IP: %s", message)
            notify(message)            
            notify(message)

        prev_ext_ip = ext_ip
        prev_default_gw = default_gw
        time.sleep(1)

if __name__ == '__main__':
    main()
