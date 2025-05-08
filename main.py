# -*- coding: utf-8 -*-
"""
Created on Sun May  4 16:34:17 2025

@author: JTS
"""

from pyscript import fetch

import pyodide

from urllib.request import urlopen
from bs4 import BeautifulSoup, Tag, NavigableString

import datetime as da
from numpy.polynomial import Polynomial as Poly
import numpy as np

# Async utility

# async def asasync(iterable): 
#     for i in iterable: 
#         yield i

KEY = ['temp', 'dew-point', 'rel-humid', 'precip']


class UrlCache: 
    def __init__(self): 
        self.cache = dict()
    # async def get_url(self, url): 
    #     return await fetch(url).text()
    def __call__(self, url): 
        if url not in self.cache.keys(): 
            # with urlopen(url) as page: 
            #     self.cache[url] = page.read().decode('utf-8')
            self.cache[url] = pyodide.http.open_url(url).read()
        return self.cache[url]
    def uncache(self, url): 
        return self.cache.pop(url)
    def size(self): 
        return len(self.cache)

GET = UrlCache()

def getd_temp(date, station = 888, dynamic = True): 
    url = (
        "https://corsproxy.io/?url=https://climate.weather.gc.ca/climate_data/daily_data_e.html?"
        f"StationID={station}&Prov=BC&urlExtension=_e.html&Month={date.month}"
        f"&Year={date.year}&optProxType=city"
    )
    
    fissue = False
    
    soup = BeautifulSoup(GET(url), 'html.parser')
    table = soup.find('tbody')
    try: 
        row = table.findChildren('tr')[date.day - 1]
    except AttributeError: # Too far back in time
        raise RuntimeError("Attempted to retrieve data from a timestep too far"
                           " back in time. ")
    except IndexError: 
        fissue = True
    else: 
        try: 
            assert row.findChild().findChild().findChild().contents[0].isdecimal()
        except (AssertionError, AttributeError): # Past the end of the table
            fissue = True
    
    if fissue: 
        if dynamic: 
            GET.uncache(url)
            print('Changing to dynamic scraping. ')
            return getd_temp(date, station = station, dynamic = False)
        else: 
            raise RuntimeError("Attempted to retrieve data from a timestep too"
                               " far forward in time. ")
    
    cell = row.findChildren('td')[2]
    if isinstance(cell.contents[0], NavigableString): 
        return float(cell.contents[0])
    elif isinstance(cell.contents[0], Tag): 
        # print(cell.findChild().findChild().contents[0])
        return getd_temp(date - da.timedelta(1), station = station)

# async def async_getd_temp(date, station = 888, dynamic = True): 
#     return getd_temp(date, station = station, dynamic = dynamic)

def havg_pred(date, station = 888, r = 5, retvar = False): 
    c = date
    data = []
    for i in range(1, r + 1): 
        try: 
            data.append(getd_temp(c - da.timedelta(365 * i)))
        except RuntimeError: 
            pass
    
    if retvar: 
        return (sum(data) / len(data), max(data) - min(data))
    else: 
        return sum(data) / len(data)

class FittingQuad: 
    def __init__(self, p, t): 
        self.quad = p
        self.today = t
    def __call__(self, day): 
        return self.quad((day - self.today).days)
    def weight(self, day): 
        x = (day - self.today).days
        return np.exp((- x ** 2) / 600)

class QuadFit: 
    def __init__(self): 
        self.cache = dict()
    def __call__(self, station = 888, memory = 144): 
        if (da.date.today(), station, memory) not in self.cache.keys(): 
            today = da.date.today()
            # diff = (date - today).days
            diff = memory
            # ys = await [getd_temp(today - da.timedelta(i)) 
            #             async for i in asasync(range(1, diff + 1))]
            ys = [getd_temp(today - da.timedelta(i)) 
                  for i in range(1, diff + 1)]
            ys.reverse()
            xs = [-1-diff + i for i in range(1, diff + 1)]
            
            quad, res = Poly.fit(xs, ys, 2, full = True)
            res = res[0]
            self.cache[(da.date.today(), station, memory)] = FittingQuad(quad, today)
        return self.cache[(da.date.today(), station, memory)]
    def size(self): 
        return len(self.cache)

quadfit = QuadFit()

def qavg_pred(date, station = 888, r = 5, memory = 144): 
    havg, var = havg_pred(date, station = station, r = r, retvar = True)
    q = quadfit(station = station, memory = memory)
    quad = q(date)
    gauss = q.weight(date)
    w = 5 / var
    return (havg * w / (w + gauss)) + (quad * gauss / (w + gauss))


GETH_TEMP_CACHE = {}

def geth_temp(date, station = 888, dynamic = True, feature = 0): # date is datetime
    
    if (date, station, feature) in GETH_TEMP_CACHE.keys(): 
        return GETH_TEMP_CACHE[(date, station, feature)]
    
    url = (
        "https://corsproxy.io/?url=https://climate.weather.gc.ca/climate_data/hourly_data_e.html?"
        f"StationID={station}&Month={date.month}&Day={date.day}&Year={date.year}"
    )
    
    fissue = False
    
    soup = BeautifulSoup(GET(url), 'html.parser')
    print(GET(url))
    table = soup.find('tbody')
    try: 
        row = table.findChildren('tr')[date.hour]
    except AttributeError: # Too far back in time
        print(date, table)
        raise RuntimeError("Attempted to retrieve data from a timestep too far"
                           " back in time. ")
    except IndexError: 
        fissue = True
    else: 
        try: 
            assert row.findChild().contents[0][2] == ':'
        except (AssertionError, AttributeError, IndexError): # Past the end of the table
            fissue = True
    
    if fissue: 
        if dynamic: 
            GET.uncache(url)
            print('Changing to dynamic scraping. ')
            return geth_temp(date, station = station, dynamic = False, feature = feature)
        else: 
            raise RuntimeError("Attempted to retrieve data from a timestep too"
                               " far forward in time. ")
    
    cell = row.findChildren('td')[feature] # THIS IS HOW YOU WIN THE TIME WAR
    # print(cell.contents, date, cell.contents == [])
    if cell.contents == []: 
        return geth_temp(date - da.timedelta(hours = 1), station = station, feature = feature)
    else: 
        if isinstance(cell.contents[0], NavigableString): 
            # Success. Finally. 
            if (date, station, feature) not in GETH_TEMP_CACHE.keys(): 
                GETH_TEMP_CACHE[(date, station, feature)] = float(cell.contents[0])

            print(float(cell.contents[0]))
            
            return float(cell.contents[0])
        elif isinstance(cell.contents[0], Tag): 
            # print(cell.findChild().findChild().contents[0])
            return geth_temp(date - da.timedelta(hours = 1), station = station, feature = feature)

def havgh_pred(date, station = 888, r = 3, retvar = False, feature = 0): 
    c = date
    data = []
    for i in range(1, r + 1): 
        try: 
            data.append(geth_temp(c - da.timedelta(365 * i), 
                                  feature = feature))
        except RuntimeError: 
            pass
    
    if retvar: 
        return (sum(data) / len(data), max(data) - min(data))
    else: 
        return sum(data) / len(data)

def hournow(): # Utility to get up to hours but no more. 
    now = da.datetime.today()
    return da.datetime(now.year, now.month, now.day, now.hour)

class FittingQuadh: 
    def __init__(self, p, t): 
        self.quad = p
        self.today = t
    def __call__(self, day): 
        return self.quad((day - self.today).seconds // 3600)
    def weight(self, day): 
        x = (day - self.today).seconds // 3600
        return np.exp((- x ** 2) / 60) # Note: 60 instead of 600 for hourly quads. 

class QuadFith: 
    def __init__(self): 
        self.cache = dict()
    def __call__(self, station = 888, memory = 10): 
        if (hournow(), station, memory) not in self.cache.keys(): 
            today = hournow()
            # diff = (date - today).days
            diff = memory
            # ys = await [getd_temp(today - da.timedelta(i)) 
            #             async for i in asasync(range(1, diff + 1))]
            ys = [geth_temp(today - da.timedelta(hours = i)) 
                  for i in range(1, diff + 1)]
            ys.reverse()
            xs = [-1-diff + i for i in range(1, diff + 1)]
            
            quad, res = Poly.fit(xs, ys, 2, full = True)
            res = res[0]
            self.cache[(hournow(), station, memory)] = FittingQuadh(quad, today)
        return self.cache[(hournow(), station, memory)]
    def size(self): 
        return len(self.cache)

quadfith = QuadFith()

def qavgh_pred(date, station = 888, r = 5, memory = 10): 
    # print('1')
    havg, var = havgh_pred(date, station = station, r = r, retvar = True)
    # print('2')
    q = quadfith(station = station, memory = memory)
    # print('3')
    quad = q(date)
    # print('4')
    gauss = q.weight(date)
    # print('5')
    w = 4 / var # Different proportionality constant. 
    return (havg * w / (w + gauss)) + (quad * gauss / (w + gauss))

def slavgh_pred(date, station = 888, r = 3, mem = 8, feature = 0): 
    havg, var = havgh_pred(date, station = station, r = r, retvar = True, 
                           feature = feature)
    # print('1')
    mems = []
    for i in range(1, mem + 1):
        try: 
            mems.append(geth_temp(date - da.timedelta(hours = i), 
                                  station = station, feature = feature))
        except RuntimeError: 
            pass
    
    # print('2')
    
    if mems == []: 
        mavg = None
    else: 
        mavg = sum(mems) / len(mems)
        
        havs = []
        for i in range(1, mem + 1): 
            havs.append(havgh_pred(date - da.timedelta(hours = i), 
                                   station = station, r = r, 
                                   feature = feature))
        # print('3')
        havgavg = sum(havs) / len(havs)
        if mavg is None: 
            dev = 0
        else: 
            dev = mavg - havgavg
        
        invw = var / 4
        m = (len(mems) ** 2) / (mem ** 2)
        # dev = 0 # Comment out. 
        return havg + (dev * m * invw)

# def quadfit(station = 888, memory = 144): 
#     today = da.date.today()
#     # diff = (date - today).days
#     diff = memory
#     ys = [getd_temp(today - da.timedelta(i)) for i in range(1, diff + 1)]
#     ys.reverse()
#     xs = [-1-diff + i for i in range(1, diff + 1)]
    
#     quad, res = Poly.fit(xs, ys, 2, full = True)
#     res = res[0]
#     return FittingQuad(quad, today)



import matplotlib.pyplot as plt
from pyscript import display

now = hournow()

realxs = [now - da.timedelta(hours = i) for i in range(1, 13)]
trealys = [geth_temp(t, feature = 0) for t in realxs]
print('1')
prealys = [slavgh_pred(t, feature = 3) for t in realxs]
print('2')

# predxs = [now + da.timedelta(hours = i) for i in range(24)]
# tpredys = [geth_temp(t, feature = 0) for t in predxs]
# print('3')
# ppredys = [slavgh_pred(t, feature = 3) for t in predxs]
# print('4')

# print(geth_temp(now - da.timedelta(hours = 10)))

figure, axes = plt.subplots(1, 2)

axes[0].plot(realxs, trealys)


