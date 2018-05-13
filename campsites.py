#!/usr/bin/env python
import argparse
import copy
import requests
import smtplib

import urllib.request, urllib.parse, urllib.error
from urllib.parse import parse_qs
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from email.mime.multipart import MIMEMultipart
from mail_server import MailServer

PARKS_I_LIKE = {
    'yosemite': {
        '70925': 'UPPER PINES',
        '70928': 'LOWER PINES',
        '70927': 'NORTH PINES',
    },
    #'stanislaus': {
        #'73635': 'STANISLAUS',
    #},
    #'tuolomne meadows' : {
        #'70926': 'TUOLOMNE MEADOWS'
    #},
}

# Sets the search location to yosemite
LOCATION_PAYLOAD = {
    'currentMaximumWindow': '12',
    #'locationCriteria': 'yosemite',
    'locationCriteria': 'stanislaus',
    'interest': '',
    'locationPosition': '',
    'selectedLocationCriteria': '',
    'resetAllFilters':    'false',
    'filtersFormSubmitted': 'false',
    'glocIndex':    '0',
    #'googleLocations':  'Yosemite National Park, Yosemite Village, CA 95389, USA|-119.53832940000001|37.8651011||LOCALITY'
}

# Sets the search type to camping
CAMPING_PAYLOAD = {
    'resetAllFilters':  'false',
    'filtersFormSubmitted': 'true',
    'sortBy':   'RELEVANCE',
    'category': 'camping',
    'selectedState':    '',
    'selectedActivity': '',
    'selectedAgency':   '',
    'interest': 'camping',
    'usingCampingForm': 'true'
}

# Runs the actual search
SEARCH_PAYLOAD = {
    'resetAllFilters':   'false',
    'filtersFormSubmitted': 'true',
    'sortBy':   'RELEVANCE',
    'category': 'camping',
    'availability': 'all',
    'interest': 'camping',
    'usingCampingForm': 'false'
}


BASE_URL = "https://www.recreation.gov"
UNIF_SEARCH = "/unifSearch.do"
UNIF_RESULTS = "/unifSearchResults.do"


def sendRequest(payload, location):
    location_payload = LOCATION_PAYLOAD.copy()
    location_payload['locationCriteria'] = location
    with requests.Session() as s:
        s.get(BASE_URL + UNIF_RESULTS, verify=False) # Sets session cookie
        s.post(BASE_URL + UNIF_SEARCH, location_payload, verify=False)
        # Sets search type to camping
        s.post(BASE_URL + UNIF_SEARCH, CAMPING_PAYLOAD, verify=False)

        # Runs search on specified dates
        resp = s.post(BASE_URL + UNIF_SEARCH, payload, verify=False)
        if (resp.status_code != 200):
            raise Exception("failedRequest","ERROR, %d code received from %s".format(resp.status_code, BASE_URL + SEARCH_PATH))
        else:
            return resp.text

def findCampSites(args, location):
    payload = generatePayload(args['start_date'], args['end_date'])
    content_raw = sendRequest(payload, location)
    html = BeautifulSoup(content_raw, 'html.parser')
    sites = getSiteList(html, location)
    return sites

def getNextDay(date):
    date_object = datetime.strptime(date, "%Y-%m-%d")
    next_day = date_object + timedelta(days=1)
    return datetime.strftime(next_day, "%Y-%m-%d")

def formatDate(date):
    date_object = datetime.strptime(date, "%Y-%m-%d")
    date_formatted = datetime.strftime(date_object, "%a %b %d %Y")
    return date_formatted

def generatePayload(start, end):
    payload = copy.copy(SEARCH_PAYLOAD)
    payload['arrivalDate'] = formatDate(start)
    payload['departureDate'] = formatDate(end)
    return payload

def getSiteList(html, location):
    sites = html.findAll('div', {"class": "check_avail_panel"})
    results = []

    parks = PARKS_I_LIKE[location]
    for site in sites:
        if site.find('a', {'class': 'book_now'}):
            get_url = site.find('a', {'class': 'book_now'})['href']
            # Strip down to get query parameters
            get_query = get_url[get_url.find("?") + 1:] if get_url.find("?") >= 0 else get_url
            if get_query:
                get_params = parse_qs(get_query)
                siteId = get_params['parkId']
                if siteId and siteId[0] in parks:
                    results.append("%s, Booking Url: %s" % (parks[siteId[0]], BASE_URL + get_url))
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start_date", required=True, type=str, help="Start date [YYYY-MM-DD]")
    parser.add_argument("--end_date", type=str, help="End date [YYYY-MM-DD]")
    parser.add_argument("--send_email", action='store_true', default=False,
        help="Send an email notification when a site is found.")

    args = parser.parse_args()
    arg_dict = vars(args)
    if 'end_date' not in arg_dict or not arg_dict['end_date']:
        arg_dict['end_date'] = getNextDay(arg_dict['start_date'])

    if args.send_email:
        smtp = smtplib.SMTP('smtp.gmail.com', 587)
        with open('./email.txt', 'r') as f:
            email = dict(line.split('=') for line in f)
        email_server = MailServer(smtp, email['user'], email['password'])


    for location in PARKS_I_LIKE:
        sites = findCampSites(arg_dict, location)
        if sites:
            composed = []
            for site in sites:
                text = ((location.title() + ': ' + site + \
                    "&arrivalDate={}&departureDate={}" \
                    .format(
                            urllib.parse.quote_plus(formatDate(arg_dict['start_date'])),
                            urllib.parse.quote_plus(formatDate(arg_dict['end_date'])))))
                composed.append(text)
            print('\n'.join(composed))
            if args.send_email:
                email_server.SendEmail(email['user'], email['to'],
                    'Found a site at %s!' % location.title(),
                    '\n'.join(composed))
