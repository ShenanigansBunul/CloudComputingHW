from http.server import BaseHTTPRequestHandler, HTTPServer
from os import curdir, sep
import aiohttp
import cgi
import base64
import asyncio
import json
import threading
import timeit
import urllib.request
import gspread
from oauth2client.service_account import ServiceAccountCredentials

config = dict()
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('sheets.json', scope)
client = gspread.authorize(creds)

logs = dict()
logs['sheets'] = []
logs['imgur'] = []
logs['mojang'] = []


def get_image_html(id):
    return '''<p><a href="https://imgur.com/''' + id + '''">
<img border="0" alt="W3Schools" src="https://i.imgur.com/''' + id + '''.png">
</a>
</p>'''


def get_index(ids):
    page = '''<html>
<head></head>
<body><form action="/index.html" method="post">
<label for="quantity">Cate skin-uri sa fie uploadate:</label>
<input type="number" id="quantity" name="quantity" min="0" max="500">
<input type="submit">
</form>'''
    for i in ids:
        page = page + get_image_html(i)
    page = page + "</body></html>"
    return page


def get_times(k):
    f = float(logs[k][0]['time'])
    timesum = 0
    count = 0
    s = 0
    for i in logs[k]:
        if float(i['time']) < f:
            f = i['time']
        if float(i['time']) > s:
            s = i['time']
        timesum = timesum + float(i['time'])
        count += 1
    if count == 0:
        return -1, -1, -1
    f = round(f, 3)
    s = round(s, 3)
    avg = round(timesum / count, 3)
    return f, avg, s


def get_metrics():
    page = '''<html>
    <head></head>
    <body>'''

    if len(logs['sheets']) == 0:
        page = page + "Nu exista metrici inca."
    else:
        for i in logs.keys():
            f, a, s = get_times(i)
            page = page + '''<p>''' + i + '''</p>
    <ul>
    <li>Response (fastest): ''' + str(f) + ''' s</li>
    <li>Response (avg): ''' + str(a) + ''' s</li>
    <li>Response (slowest): ''' + str(s) + ''' s</li>
    </ul>'''

    page = page + "</body></html>"
    return page


def get_logs():
    page = '''<html>
    <head></head>
    <body>'''

    if len(logs['sheets']) == 0:
        page = page + "Nu exista log-uri inca."
    else:
        for i in logs.keys():
            page = page + '''<p>''' + i + '''</p>'''
            for j in logs[i]:
                page = page + '''<p>Request: ''' + str(j['request']) + '''</p><p>Timp: ''' + str(
                    j['time']) + '''</p><p>Raspuns: ''' + str(j['response']) + '''</p>'''

    page = page + "</body></html>"
    return page


def format_sheet_results(s):
    usernames = []
    uuids = []
    for d in s:
        for key, value in d.items():
            if value != '':
                if key == 'Usernames':
                    usernames.append(value)
                elif key == 'UUIDs':
                    uuids.append(value)
    return usernames, uuids


def read_from_sheet():
    t1 = timeit.default_timer()
    sheet = client.open('Names').sheet1
    result = format_sheet_results(sheet.get_all_records())
    t2 = timeit.default_timer()
    logs['sheets'].append(
        {'request': {'file': 'Names', 'sheet': 'sheet1'}, 'time': abs(t2 - t1), 'response': sheet.get_all_records()})
    return result


async def mc_user_to_uuid_f(session, username, uuids):
    t1 = timeit.timeit()
    async with session.get('https://api.mojang.com/users/profiles/minecraft/' + username) as resp:
        # print(resp.status)
        result = await resp.text()
        t2 = timeit.default_timer()
        logs['mojang'].append(
            {'request': 'https://api.mojang.com/users/profiles/minecraft/' + username, 'time': abs(t2 - t1),
             'response': result})
        uuids.append(json.loads(result)["id"])


async def async_mc_user_to_uuid(u_list):
    uuids = []
    async with aiohttp.ClientSession() as session:
        coros = [mc_user_to_uuid_f(session, username, uuids) for username in u_list]
        await asyncio.gather(*coros)
    return uuids


async def uuid_to_skin_f(id, session):
    t1 = timeit.default_timer()
    async with session.get('https://sessionserver.mojang.com/session/minecraft/profile/' + id) as resp:
        result = await resp.text()
        t2 = timeit.default_timer()
        logs['mojang'].append(
            {'request': 'https://sessionserver.mojang.com/session/minecraft/profile/' + id, 'time': t2 - t1,
             'response': result})
        d1 = json.loads(result)
        if "error" not in d1.keys():
            d2 = d1['properties'][0]['value']
            d3 = base64.b64decode(d2)
            d4 = json.loads(d3)
            if "SKIN" in d4['textures']:
                d5 = d4["textures"]["SKIN"]["url"]
            else:
                d5 = 'https://i.imgur.com/QJQf76f.png'
            urllib.request.urlretrieve(d5,
                                       "cache//" + id + ".png")
        else:
            print("Skin for UUID " + id + " not found, using cache.")


async def async_uuid_to_skin(uu_list):
    async with aiohttp.ClientSession() as session:
        coros = [uuid_to_skin_f(id, session) for id in uu_list]
        await asyncio.gather(*coros)


async def imgur_upload_f(img, session, ids):
    f = open("cache//" + img + ".png", "rb")
    bina = f.read()
    f.close()
    t1 = timeit.default_timer()
    async with session.post('https://api.imgur.com/3/image', data={'image': bina, 'type': 'file'},
                            headers={'Authorization': 'Client-ID ' + config['imgur_client_id']}) as resp:
        # print(resp.status)
        result = await resp.text()
        t2 = timeit.default_timer()
        logs['imgur'].append(
            {'request': {'url': 'https://api.imgur.com/3/image', 'data': {'image': bina, 'type': 'file'},
                         'headers': {'Authorization': 'Client-ID ' + config['imgur_client_id']}},
             'time': abs(t2 - t1),
             'response': result})
        d1 = json.loads(result)
        if "id" in d1["data"]:
            d2 = d1["data"]["id"]
            ids.append(d2)
        else:
            print("Nu s-a putut uploada o imagine pe imgur:")
            print(d1)


async def async_imgur_upload(i_list):
    ids = []
    async with aiohttp.ClientSession() as session:
        coros = [imgur_upload_f(img, session, ids) for img in i_list]
        await asyncio.gather(*coros)
    return ids


class MyHandler(BaseHTTPRequestHandler):
    def _set_response(self, type):
        self.send_response(200)
        self.send_header('Content-type', type)
        self.end_headers()

    def handle_request(self, is_post):
        p_l = self.path.split("?")
        if p_l[0] == "/":
            p_l[0] = "/index.html"
        try:
            reply = False
            mime_type = None
            if p_l[0].endswith(".html"):
                mime_type = 'text/html'
                reply = True
            if p_l[0].endswith(".css"):
                mime_type = 'text/css'
                reply = True
            if reply:
                ids = []
                if is_post:
                    form = cgi.FieldStorage(fp=self.rfile,
                                            headers=self.headers,
                                            environ={'REQUEST_METHOD': 'POST'})
                    v = int(form["quantity"].value)
                    loop = asyncio.get_event_loop()
                    usernames, uuids = read_from_sheet()
                    uuids.extend(loop.run_until_complete(async_mc_user_to_uuid(usernames)))
                    uuids = uuids[:v]
                    loop.run_until_complete(async_uuid_to_skin(uuids))
                    ids = loop.run_until_complete(async_imgur_upload(uuids))

                # f = open(curdir + sep + p_l[0])
                # self._set_response(mime_type)
                # self.wfile.write(f.read().encode('utf-8'))
                # f.close()
                self._set_response(mime_type)
                if p_l[0] == "/index.html":
                    self.wfile.write(get_index(ids).encode('utf-8'))
                if p_l[0] == "/metrics.html":
                    self.wfile.write(get_metrics().encode('utf-8'))
                if p_l[0] == "/logs.html":
                    self.wfile.write(get_logs().encode('utf-8'))
        except IOError:
            self.send_error(404, 'File Not Found: %s' % self.path)

    def do_GET(self):
        self.handle_request(False)

    def do_POST(self):
        self.handle_request(True)


def run(server_class=HTTPServer, handler_class=MyHandler, port=8080):
    f = open(curdir + sep + "/config.txt")
    cfg = f.read()
    cfg = cfg.split('\n')
    for i in cfg:
        x = i.split(':')
        config[x[0]] = x[1]
    f.close()

    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()


if __name__ == '__main__':
    run()
