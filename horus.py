import requests
from datetime import datetime
import re
from huepy import *
import time
import json
import configparser
import sys
import asyncio
import aiohttp

# TODO: aiohttp timeout

## Functions
def load_configuration():
    """ Loads the configurtion file """
    config = configparser.RawConfigParser()
    config.read(config_filename)
    print(info(f"Configuration: {config_filename}"))
    # :limit
    try:
        limit = int(config["PREFERENCES"]["limit"])
        if limit > 250:
            print(info("Limit: Above maximum! Reset to 250."))
        else:
            print(info(f"Limit: {limit}"))
    except:
        print(bad("Limit: Invalid value! Reset to 250."))
        limit = 250
    # :regex
    find_regex = config["PREFERENCES"]["find-regex"]
    if find_regex == "__default__":
        find_regex = r"(?!git)\b\w*[^@]\@[\w\d]*\.[a-z]*[:|,]\S+"
    print(info("REGEX: " + find_regex))
    # :ignore
    ignore_set = {string.strip() for string in config["PREFERENCES"]["ignore"].split(",")}
    print(info(f"Ignoring: {ignore_set}\n"))

    return (limit, find_regex, ignore_set)

def ignore(match):
    """ Checks & returns if a string or regex from the ignore-list is in the match """
    # for string in ignore_strings:
    #     if string in match:
    #         return True
    for string in ignore_set:
        if re.findall(string, match):
            return True
    return False

async def skip(key):
    """ Checks & returns wheter or not the paste has been checked before """
    global checked_keys
    if key in checked_keys:
        return True
    checked_keys.add(key)
    return False


async def fetch_latest_pastes(limit):
    """ Fetch & return the lastest pastes """
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://scrape.pastebin.com/api_scraping.php?limit={limit}') as response:
            pastes = await response.json()
    return pastes

async def get_paste_info(paste):
    """ Return the paste's data """
    data = {
        "scrape_url": paste["scrape_url"],
        "full_url": paste["full_url"],
        "date": str(datetime.fromtimestamp(int(paste['date']))),
        "key": paste['key'],
        "size": paste['size'],
        "expire": str(datetime.fromtimestamp(int(paste['expire']))),
        "title": paste['title'],
        "syntax": paste['syntax'],
        "user": paste['user'],
    }
    return data

async def fetch_paste_content(url, session):
    """  Fetch & return the paste's content """
    async with session.get(url) as response:
        return await response.text()

async def start():
    """ Where the magic happens """
    pastes = await fetch_latest_pastes(limit)
    async with aiohttp.ClientSession() as session:
        for paste in pastes:
            paste_data = await get_paste_info(paste)
            if not await skip(paste_data["key"]):
                paste_data["content"] = await fetch_paste_content(paste_data["scrape_url"], session)
                await parse_paste(paste_data)
                await asyncio.sleep(1)
    print(run("Restarting in 30 seconds..."))
    await asyncio.sleep(30)

async def parse_paste(paste_data):
    """ Parses the paste by filtering its content """
    matches = re.findall(find_regex, paste_data["content"])
    if matches:
        leaks = {match for match in matches if not ignore(match)}
        print(good(paste_data["scrape_url"]))
    else:
        print(bad(paste_data["scrape_url"]))

def has_access():
    """ Checks & returns if the IP has access to the API """
    response = requests.get("https://scrape.pastebin.com/api_scraping.php?").text
    if "NOT" in response:
        return False
    return True


## Globals
checked_keys = set()
config_filename = 'config.ini'
limit, find_regex, ignore_set = load_configuration()

## Main
if has_access():
    loop = asyncio.get_event_loop()
    while True:
        loop.run_until_complete(start())
else:
    print(bad("YOUR IP DOES NOT HAVE ACCESS"))
