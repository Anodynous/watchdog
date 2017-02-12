#!/usr/bin/python3

import configparser
import requests
import re
import csv
from bs4 import BeautifulSoup
import pandas as pd
from pandas import DataFrame
import telepot
from urllib.request import urlopen  # Needed to get image to send using telepot. Couldn't get requests to work right

# Import config file
config = configparser.ConfigParser()
config.read('config.ini')

# Adding headers to mask our bot
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36'}

# Telegram subscribers
telegram_subs = config['TELEGRAM_USERS']['telegram_subs']

# Telegram API Token
telegram_token = config['TELEGRAM_TOKEN']['telepot_key']

def read_kulkurit():
    df = pd.read_csv('kulkurit.csv', header=None)
    return df

def read_viipuri():
    df = pd.read_csv('viipurin_pojat.csv', header=None)
    l = df.values.tolist()
    flatlist = sum(l, [])
    return flatlist

def compare_data(scraped, logged):
    new_dogs = []
    for dog in scraped:
        if dog not in logged:
            new_dogs.append(dog)
    return new_dogs

def write_kukurit(data):
    with open('kulkurit.csv', 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        for d in data:
            writer.writerow([d[0], d[1], d[2], d[3]])

def write_viipuri(data):
    with open('viipurin_pojat.csv', 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        for d in data:
            writer.writerow([d])

def scrape_kulkurit():
    url = 'http://kulkurit.fi/category/kotia-etsivat-kaikki/'    # Page to scrape
    resp = requests.get(url, allow_redirects=True, headers=headers)  # Making the request
    html = resp.text  # Strip out the HTML
    soup = BeautifulSoup(html, 'html.parser')
    second_link = False
    scraped_kulkurit = []
    for link in soup.findAll('a', href=True, title=re.compile(r'^Kotia etsivä koira:.*')):  # This line is critical. It all depends on the new dogs starting with "Kotia etsivä koira:", otherwise no links will be found by bs.
        if not second_link:     # Kulkurit always has two links for each dog, second containing timestamp
            name = link['href'][19:][:-1].title()
            href = link['href']
            picture = link.contents[1]['src']
            second_link = True
            continue
        if second_link:
            timestamp = link.contents[0]['datetime']
            second_link = False
            scraped_kulkurit.append((name, timestamp, picture, href))
    #write_kukurit(scraped_kulkurit)  # This will append all scraped data to kulkurit.csv. Delete file and uncomment line to start fresh.
    return(scraped_kulkurit)

def scrape_viipurinkoirat_males():
    url = 'http://viipurinkoirat.fi/pojat'    # Page to scrape
    resp = requests.get(url, allow_redirects=True, headers=headers)  # Making the request
    html = resp.text  # Strip out the HTML
    soup = BeautifulSoup(html, 'html.parser')
    tagged_values = soup.find_all("li", class_=re.compile(r'.*leaf menu.*'))
    values = [x.get_text() for x in tagged_values]
    return values

def doggoram_kulkurit(data):
    bot = telepot.Bot(telegram_token)
    image = urlopen(str(data[0][2]))
    message = data[0][0] + ' ' + data[0][3]
    for user in telegram_subs:
        bot.sendMessage(user, str(message))
        bot.sendPhoto(user, ('image.jpg', image))


def doggoram_viipuri(data):
    bot = telepot.Bot(telegram_token)
    message = data + '  http://viipurinkoirat.fi/' + str(data.lower())
    for user in telegram_subs:
        bot.sendMessage(user, str(message))

def main():
    try:
        """Kulkurit"""
        scraped_kulkurit = DataFrame(scrape_kulkurit())
        logged_kulkurit = read_kulkurit()
        scraped_names = scraped_kulkurit[scraped_kulkurit.columns[0]].tolist()
        logged_names = logged_kulkurit[logged_kulkurit.columns[0]].tolist()
        new_kulkurit = compare_data(scraped=scraped_names, logged=logged_names)
        if len(new_kulkurit) != 0:
            """ If new dogs are found, send info using telepot and add them to our database """
            for name in new_kulkurit:
                print('Kulkurit: ' + name)
                fulldata = scraped_kulkurit.loc[scraped_kulkurit[0] == name]
                fulldata = fulldata.values.tolist()
                doggoram_kulkurit(fulldata)  # Send info about the dog
                write_kukurit(fulldata)  # Write the new dog info to CSV database

        """Viipurinkoirat - Pojat"""
        scraped_viipuri = scrape_viipurinkoirat_males()
        logged_viipuri = read_viipuri()
        new_viipuri = compare_data(scraped=scraped_viipuri, logged=logged_viipuri)
        if len(new_viipuri) != 0:
            """ If new dogs are found, send info using telepot and add them to our database """
            for name in new_viipuri:
                print('Viipurinkoirat: ' + name)
                doggoram_viipuri(name)
                write_viipuri([name])
    except Exception as e:
        bot = telepot.Bot(telegram_token)
        bot.sendMessage(telegram_subs[0], str(e))
main()
