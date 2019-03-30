# Code originally downloaded from Scrapehero tutorial here: https://www.scrapehero.com/how-to-scrape-tripadvisor/
# and github repository here: https://gist.github.com/scrapehero/1c425fdf290144cd4c7c635587feb459
# modified for python 3 syntax, xpath adjustment, to include pandas to avoid byte/string errors with original cvs Dictwriter, and to page through @ 1000 listings
#!/usr/bin/env python
from datetime import datetime
from time import time
from lxml import html,etree
import requests,re
import os,sys
import unicodecsv as csv
import argparse
import pandas as pd

def parse(locality,checkin_date,checkout_date,sort):
    checkIn = checkin_date.strftime("%Y/%m/%d")
    checkOut = checkout_date.strftime("%Y/%m/%d")
    print("Scraper Inititated for Locality:%s"%locality)
    # TA rendering the autocomplete list using this API
    print("Finding search result page URL")
    geo_url = 'https://www.tripadvisor.com/TypeAheadJson?action=API&startTime='+str(int(time()))+'&uiOrigin=GEOSCOPE&source=GEOSCOPE&interleaved=true&types=geo,theme_park&neighborhood_geos=true&link_type=hotel&details=true&max=12&injectNeighborhoods=true&query='+locality
    api_response  = requests.get(geo_url, verify=False).json()
    #getting the TA url for th equery from the autocomplete response
    url_from_autocomplete = "http://www.tripadvisor.com"+api_response['results'][0]['url']
    print('URL found %s'%url_from_autocomplete)
    geo = api_response['results'][0]['value']   
    #Formating date for writing to file 
    
    date = checkin_date.strftime("%Y_%m_%d")+"_"+checkout_date.strftime("%Y_%m_%d")
    #form data to get the hotels list from TA for the selected date
    form_data = {'changeSet': 'TRAVEL_INFO',
            'showSnippets': 'false',
            'staydates':date,
            'uguests': '2',
            'sortOrder':sort
    }
    #Referrer is necessary to get the correct response from TA if not provided they will redirect to home page
    headers = {
                            'Accept': 'text/javascript, text/html, application/xml, text/xml, */*',
                            'Accept-Encoding': 'gzip,deflate',
                            'Accept-Language': 'en-US,en;q=0.5',
                            'Cache-Control': 'no-cache',
                            'Connection': 'keep-alive',
                            'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
                            'Host': 'www.tripadvisor.com',
                            'Pragma': 'no-cache',
                            'Referer': url_from_autocomplete,
                            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:28.0) Gecko/20100101 Firefox/28.0',
                            'X-Requested-With': 'XMLHttpRequest'
                        }
    cookies=  {"SetCurrency":"USD"}
    print("Downloading search results page")

    npages=[""] #,"oa30","oa60","oa90","oa120"]
    for i in range(1,34):
        npages.append(f'oa{30*i}')
    hotel_data = []
    for page in npages:
        mL = url_from_autocomplete.split("/")
        mstr = mL[-1]
        lastL= mstr.split("-")
        lastL.insert(2,page)
        mL[-1]='-'.join(lastL)
        this_url = "/".join(mL)
        
        page_response  = requests.post(url = this_url,data=form_data,headers = headers, cookies = cookies, verify=False)
        print("----------------------------------Parsing results "+this_url)
        parser = html.fromstring(page_response.text)
        #hotel_lists = parser.xpath('//div[contains(@class,"listItem")]//div[contains(@class,"listing collapsed")]')
        hotel_lists = parser.xpath("//div[contains(concat(' ',normalize-space(@class),' '),' listItem ')]//div[contains(concat(' ',normalize-space(@class),' '),' listing collapsed ')]")
    
        if not hotel_lists:
            #hotel_lists = parser.xpath('//div[contains(@class,"listItem")]//div[@class="listing "]')
            hotel_lists = parser.xpath("//div[contains(concat(' ',normalize-space(@class),' '),' listItem ')]//div[contains(concat(' ',normalize-space(@class),' '),' listing ')]")
        for hotel in hotel_lists:
            XPATH_HOTEL_LINK = './/a[contains(@class,"property_title")]/@href'
            XPATH_REVIEWS  = './/a[@class="review_count"]//text()'
            XPATH_RANK = './/div[@class="popRanking"]//text()'
            # XPATH_RATING = './/span[contains(@class,"rating")]/@alt'
            XPATH_RATING = './/a[contains(@class,"ui_bubble_rating")]/@alt'
            XPATH_HOTEL_NAME = './/a[contains(@class,"property_title")]//text()'
            XPATH_HOTEL_FEATURES = './/div[contains(@class,"common_hotel_icons_list")]//li//text()'
            XPATH_HOTEL_PRICE = './/div[contains(@data-sizegroup,"mini-meta-price")]/text()'
            XPATH_VIEW_DEALS = './/div[contains(@data-ajax-preserve,"viewDeals")]//text()' 
            XPATH_BOOKING_PROVIDER = './/div[contains(@data-sizegroup,"mini-meta-provider")]//text()'

            raw_booking_provider = hotel.xpath(XPATH_BOOKING_PROVIDER)
            raw_no_of_deals =  hotel.xpath(XPATH_VIEW_DEALS)
            raw_hotel_link = hotel.xpath(XPATH_HOTEL_LINK)
            raw_no_of_reviews = hotel.xpath(XPATH_REVIEWS)
            raw_rank = hotel.xpath(XPATH_RANK)
            raw_rating = hotel.xpath(XPATH_RATING)
            raw_hotel_name = hotel.xpath(XPATH_HOTEL_NAME)
            raw_hotel_features = hotel.xpath(XPATH_HOTEL_FEATURES)
            raw_hotel_price_per_night  = hotel.xpath(XPATH_HOTEL_PRICE)

            url = 'http://www.tripadvisor.com'+raw_hotel_link[0] if raw_hotel_link else  None
            reviews = ''.join(raw_no_of_reviews).replace("reviews","").replace(",","") if raw_no_of_reviews else 0 
            rank = ''.join(raw_rank) if raw_rank else None
            rating = ''.join(raw_rating).replace('of 5 bubbles','').replace('\n','') if raw_rating else None
            name = ''.join(raw_hotel_name).replace('\n','') if raw_hotel_name else None
            hotel_features = ','.join(raw_hotel_features)
            price_per_night = ''.join(raw_hotel_price_per_night).replace('\n','') if raw_hotel_price_per_night else None
            no_of_deals = re.findall("all\s+?(\d+)\s+?",''.join(raw_no_of_deals))
            booking_provider = ''.join(raw_booking_provider).replace('\n','') if raw_booking_provider else None

            if no_of_deals:
                no_of_deals = no_of_deals[0]
            else:
                no_of_deals = 0
            
            data = {
                    'hotel_name':name,
                    'url':url,
                    'locality':locality,
                    'reviews':reviews,
                    'tripadvisor_rating':rating,
                    'checkOut':checkOut,
                    'checkIn':checkIn,
                    'hotel_features':hotel_features,
                    'price_per_night':price_per_night,
                    'no_of_deals':no_of_deals,
                    'booking_provider':booking_provider

            }
            hotel_data.append(data)
        
    return hotel_data

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('checkin_date',help = 'Hotel Check In Date (Format: YYYY/MM/DD')
    parser.add_argument('checkout_date',help = 'Hotel Chek Out Date (Format: YYYY/MM/DD)')
    sortorder_help = """
    available sort orders are :\n
    priceLow - hotels with lowest price,
    distLow : Hotels located near to the search center,
    recommended: highest rated hotels based on traveler reviews,
    popularity :Most popular hotels as chosen by Tipadvisor users 
    """
    parser.add_argument('sort',help = sortorder_help,default ='popularity ')
    parser.add_argument('locality',help = 'Search Locality')
    args = parser.parse_args()
    locality = args.locality
    checkin_date = datetime.strptime(args.checkin_date,"%Y/%m/%d")
    checkout_date = datetime.strptime(args.checkout_date,"%Y/%m/%d")
    sort= args.sort
    checkIn = checkin_date.strftime("%Y/%m/%d")
    checkOut = checkout_date.strftime("%Y/%m/%d")
    today = datetime.now()
   
    if today<datetime.strptime(checkIn,"%Y/%m/%d") and datetime.strptime(checkIn,"%Y/%m/%d")<datetime.strptime(checkOut,"%Y/%m/%d"):
        data = parse(locality,checkin_date,checkout_date,sort)
        print("Writing to output file "+locality+"_data.csv")
        print(f'data length is {len(data)}')
        hdf = pd.DataFrame(data)
        hdf.to_csv(locality+"_data.csv", index = False)
        # alldf = pd.concat([alldf, hdf], ignore_index=True)
        
    #checking whether the entered date is already passed
    elif today>datetime.strptime(checkIn,"%Y/%m/%d") or today>datetime.strptime(checkOut,"%Y/%m/%d"):
        print("Invalid Checkin date: Please enter a valid checkin and checkout dates,entered date is already passed")
    
    elif datetime.strptime(checkIn,"%Y/%m/%d")>datetime.strptime(checkOut,"%Y/%m/%d"):
        print("Invalid Checkin date: CheckIn date must be less than checkOut date")
    

   