# -*- coding: utf-8 -*-

import urllib, urllib2, re, math, datetime, os, time
import xbmc, xbmcgui, xbmcaddon

### Script constants
ADDON        = xbmcaddon.Addon()
ADDONNAME    = ADDON.getAddonInfo('name')
ADDONID      = ADDON.getAddonInfo('id')
ADDONVERSION = ADDON.getAddonInfo('version')
CWD          = ADDON.getAddonInfo('path').decode("utf-8")
RESOURCE     = xbmc.translatePath( os.path.join( CWD, 'resources', 'lib' ).encode("utf-8") ).decode("utf-8")

sys.path.append(RESOURCE)

from utilities import *

WEATHER_URL      = 'https://yandex.ru/pogoda/%s'
SEARCH_URL       = 'https://yandex.ru/pogoda/search?request=%s'

WEATHER_WINDOW   = xbmcgui.Window(12600)

#socket.setdefaulttimeout(10)

def log(txt):
    if isinstance (txt,str):
        txt = txt.decode("utf-8")
    message = u'%s: %s' % (ADDONID, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)

def set_property(name, value):
    WEATHER_WINDOW.setProperty(name, value)

def refresh_locations():
    locations = 0
    for count in range(1, 6):
        loc_name = ADDON.getSetting('Location%s' % count)
        if loc_name:
            locations += 1
        set_property('Location%s' % count, loc_name)
    set_property('Locations', str(locations))
    log('available locations: %s' % str(locations))

### обработка местоположения

def location(loc):
    items  = []
    locs   = []
    locids = []
    log('searching for location: %s' % loc)
    query = get_loc_http(loc)
    #log('location data: %s' % query)

    rep = re.compile('<li class="place-list__item">.+?<a .+? href="/pogoda/(.+?)">(.+?)</a></li>').findall(query)
    if len(rep) > 0:
        for arr in rep:
            #print 'Массив 0: %s, 1: %s' % (arr[0], arr[1])
            items.append(arr[1])
            locs.append(arr[1])
            locids.append(arr[0])

    return items, locs, locids


def get_loc_http(search):
    url = SEARCH_URL % urllib.quote(search)
    log('getting Loc Http: %s' % url)

    try:
        req = urllib2.urlopen(url)
        response = req.read()
        #print 'response: %s' % response
        req.close()
    except:
        return
    return response

# - end -

# обработка погоды

def forecast(loc,locid):
    log('weather location: %s' % locid)
    retry = 0
    while (retry < 6) and (not MONITOR.abortRequested()):
        query = get_weather_http(locid)
        if query:
            retry = 6
        else:
            retry += 1
            xbmc.sleep(10000)
            log('weather download failed')
    #log('forecast data: %s' % query)
    if query:
        data = parse_page(query)
        if data:
            set_properties(data,loc)
        else:
            clear()
    else:
        clear()

def get_weather_http(locid):
    url = WEATHER_URL % locid
    try:
        req = urllib2.urlopen(url)
        response = req.read()
        req.close()
    except:
        return
    return response

def parse_page(query):
    #print 'data: %s' % query
    data  = {}
    # текущая температура
    rep = re.search('<div class="current-weather__thermometer current-weather__thermometer_type_now">(.+?\d+).+?</div>', query)
    if rep:
        data['Current.Temperature'] = rep.group(1).replace("−", "-")
    # описание погоды
    rep = re.search('<span class="current-weather__comment">(.+?)</span>', query)
    if rep:
        data['Current.Condition'] = rep.group(1)
    # иконка
    rep = re.search('<i class="icon icon_size_48 icon_thumb_(.+?)" aria-hidden="true" data-width="48"></i>', query)
    if rep:
        data['Current.Icon'] = rep.group(1)
    # восход закат
    rep = re.search('<div class="current-weather__info-row"><span class="current-weather__info-label">Восход: </span>(.+?)<span class="current-weather__info-label current-weather__info-label_type_sunset">Закат: </span>(.+?)</div>', query)
    if rep:
        data['Current.Sunrise'] = rep.group(1)
        data['Current.Sunset'] = rep.group(2)
    # скорость ветра
    rep = re.search('<span class="wind-speed">(.+?) м/с</span>', query)
    if rep:
        speed = str(float(rep.group(1).replace(',','.'))*3.6)
        data['Current.Wind'] = speed
    else:
        data['Current.Wind'] = '0'
    # направление ветра
    rep = re.search('<div class="current-weather__info-row current-weather__info-row_type_wind">.+?<i class="icon icon_size_12 icon_wind_(.+?) icon_wind"', query)
    if rep:
        data['Current.WindDirection'] = rep.group(1)
    else:
        data['Current.WindDirection'] = ''
    # влажность
    rep = re.search('<span class="current-weather__info-label">Влажность: </span>(.+?)%</div>', query)
    if rep:
        data['Current.Humidity'] = rep.group(1)
    # давление
    rep = re.search('<span class="current-weather__info-label">Давление: </span>(.+?) мм рт. ст.</div>', query)
    if rep:
        data['Current.Pressure'] = rep.group(1)

    # погода на 10 дней включая сегодняшний
    rep = re.compile('<li class="forecast-brief__item day-anchor i-bem" .+?><.+?><span class="forecast-brief__item-day-name">(.+?)</span><span class="forecast-brief__item-day">(\d+?).+?</span></div><.+?><i class="icon icon_thumb_(.+?) icon_size_30" aria-hidden="true" data-width="30"></i><div class="forecast-brief__item-comment">(.+?)</div><div class="forecast-brief__item-temp-day" title="Максимальная температура днём">(.+?)</div></div><div class="forecast-brief__item-temp-night .+?" title="Минимальная температура ночью">(.+?)</div></li>').findall(query)
    if len(rep) > 0:
        now = datetime.date.today()
        for count, item in enumerate(rep):
            if count in range (1, 10):
                num = count - 1
                delta = datetime.timedelta(days=count)
                date = (now+delta).strftime("%d.%m")
                data['Day%i.Title'       % num] = item[0]
                data['Day%i.Date'        % num] = date
                data['Day%i.OutlookIcon' % num] = item[2]
                data['Day%i.Outlook'     % num] = item[3]
                data['Day%i.HighTemp'    % num] = item[4].replace("−", "-")
                data['Day%i.LowTemp'     % num] = item[5].replace("−", "-")

    return data

def clear():
    set_property('Current.Condition'     , 'N/A')
    set_property('Current.Temperature'   , '0')
    set_property('Current.Wind'          , '0')
    set_property('Current.WindDirection' , 'N/A')
    set_property('Current.Humidity'      , '0')
    set_property('Current.FeelsLike'     , '0')
    set_property('Current.UVIndex'       , '0')
    set_property('Current.DewPoint'      , '0')
    set_property('Current.OutlookIcon'   , 'na.png')
    set_property('Current.FanartCode'    , 'na')
    for count in range (0, 9):
        set_property('Day%i.Title'       % count, 'N/A')
        set_property('Day%i.HighTemp'    % count, '0')
        set_property('Day%i.LowTemp'     % count, '0')
        set_property('Day%i.Outlook'     % count, 'N/A')
        set_property('Day%i.OutlookIcon' % count, 'na.png')
        set_property('Day%i.FanartCode'  % count, 'na')
    for count in range (1, 10):
        set_property('Daily%i.Title'       % count, 'N/A')
        set_property('Daily%i.HighTemp'    % count, '0')
        set_property('Daily%i.LowTemp'     % count, '0')
        set_property('Daily%i.Outlook'     % count, 'N/A')
        set_property('Daily%i.OutlookIcon' % count, 'na.png')
        set_property('Daily%i.FanartCode'  % count, 'na')


def set_properties(data,loc):
    set_property('Current.Location'          , loc)
    set_property('Current.Condition'         , data['Current.Condition'])
    set_property('Current.Temperature'       , data['Current.Temperature'])
    set_property('Current.UVIndex'           , '')
    set_property('Current.OutlookIcon'       , '%s.png' % get_icons(data['Current.Icon']))
    set_property('Current.FanartCode'        , get_icons(data['Current.Icon']))
    set_property('Current.Wind'              , data['Current.Wind'])

    if (data['Current.WindDirection']):
        set_property('Current.WindDirection' , data['Current.WindDirection'])
    else:
        set_property('Current.WindDirection' , '')

    set_property('Current.WindChill'         , '')
    set_property('Current.Humidity'          , data['Current.Humidity'])
    set_property('Current.Visibility'        , '')
    set_property('Current.Pressure'          , data['Current.Pressure'] + ' Pa')

    if (data['Current.Wind']):
        set_property('Current.FeelsLike'     , feelslike(int(data['Current.Temperature']), int(round(float(data['Current.Wind']) + 0.5))))
    else:
        set_property('Current.FeelsLike'     , '')

    if (data['Current.Temperature']) and (data['Current.Humidity']):
        set_property('Current.DewPoint'      , dewpoint(int(data['Current.Temperature']), int(data['Current.Humidity'])))
    else:
        set_property('Current.DewPoint'      , '')


    ftime   = xbmc.getRegion('time').replace(":%S","").replace("%H%H","%H")
    sunrise = time.strptime(data['Current.Sunrise'], "%H:%M")
    sunset  = time.strptime(data['Current.Sunset'], "%H:%M")
    set_property('Today.Sunrise'             , time.strftime(ftime, sunrise))
    set_property('Today.Sunset'              , time.strftime(ftime, sunset))


    for count in range (0, 9):
        set_property('Day%i.Title'           % count, DAYS[data['Day%i.Title' % count]])
        set_property('Day%i.HighTemp'        % count, data['Day%i.HighTemp'   % count])
        set_property('Day%i.LowTemp'         % count, data['Day%i.LowTemp'    % count])
        set_property('Day%i.Outlook'         % count, data['Day%i.Outlook'    % count])
        set_property('Day%i.OutlookIcon'     % count, '%s.png' % get_icons(data['Day%i.OutlookIcon' % count]))
        set_property('Day%i.FanartCode'      % count, get_icons(data['Day%i.OutlookIcon' % count]))

        set_property('Daily.%i.ShortDay'        % (count + 1), DAYS[data['Day%i.Title'  % count]])
        set_property('Daily.%i.LongDay'         % (count + 1), LDAYS[data['Day%i.Title' % count]])
        set_property('Daily.%i.ShortDate'       % (count + 1), data['Day%i.Date'        % count])
        set_property('Daily.%i.HighTemperature' % (count + 1), TEMP(int(data['Day%i.HighTemp' % count])) + TEMPUNIT)
        set_property('Daily.%i.LowTemperature'  % (count + 1), TEMP(int(data['Day%i.LowTemp'  % count])) + TEMPUNIT)
        set_property('Daily.%i.Outlook'         % (count + 1), data['Day%i.Outlook'     % count])
        set_property('Daily.%i.OutlookIcon'     % (count + 1), '%s.png' % get_icons(data['Day%i.OutlookIcon' % count]))
        set_property('Daily.%i.FanartCode'      % (count + 1), get_icons(data['Day%i.OutlookIcon' % count]))

# - end -

class MyMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)


log('version %s started: %s' % (ADDONVERSION, sys.argv))

MONITOR = MyMonitor()
set_property('Forecast.IsFetched' , '')
set_property('Current.IsFetched'  , 'true')
set_property('Today.IsFetched'    , 'true')
set_property('Daily.IsFetched'    , 'true')
set_property('Weekend.IsFetched'  , '')
set_property('36Hour.IsFetched'   , '')
set_property('Hourly.IsFetched'   , '')
set_property('Alerts.IsFetched'   , '')
set_property('Map.IsFetched'      , '')
set_property('WeatherProvider'    , ADDONNAME)
set_property('WeatherProviderLogo', xbmc.translatePath(os.path.join(CWD, 'resources', 'banner.png')))

if sys.argv[1].startswith('Location'):
    keyboard = xbmc.Keyboard('', xbmc.getLocalizedString(14024), False)
    keyboard.doModal()
    if (keyboard.isConfirmed() and keyboard.getText()):
        text = keyboard.getText()
        items, locs, locids = location(text)
        dialog = xbmcgui.Dialog()
        if locs != []:
            selected = dialog.select(xbmc.getLocalizedString(396), items)
            if selected != -1:
                ADDON.setSetting(sys.argv[1], locs[selected])
                ADDON.setSetting(sys.argv[1] + 'id', locids[selected])
                log('selected location: %s' % locs[selected])
        else:
            log('no locations found')
            dialog.ok(ADDONNAME, xbmc.getLocalizedString(284))
else:
    location = ADDON.getSetting('Location%s' % sys.argv[1])
    locationid = ADDON.getSetting('Location%sid' % sys.argv[1])
    if (not locationid) and (sys.argv[1] != '1'):
        location = ADDON.getSetting('Location1')
        locationid = ADDON.getSetting('Location1id')
        log('trying location 1 instead')
    if locationid:
        forecast(location, locationid)
    else:
        log('empty location id')
        clear()
    refresh_locations()

log('finished')