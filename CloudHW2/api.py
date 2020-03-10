from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sqlite3


class ServiceHandler(BaseHTTPRequestHandler):
    # sets basic headers for the server
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/json')
        # reads the length of the Headers
        length = int(self.headers['Content-Length'])
        # reads the contents of the request
        content = self.rfile.read(length)
        temp = str(content).strip('b\'')
        self.end_headers()
        return temp

    def error_404(self):
        error = "NOT FOUND!"
        self.wfile.write(bytes(error, 'utf-8'))
        self.send_response(404)

    def do_GET(self):
        # defining all the headers
        self.send_response(200)
        self.send_header('Content-type', 'text/json')
        self.end_headers()

    def do_POST(self):
        temp = self._set_headers()
        print(temp)

    def do_PUT(self):
        temp = self._set_headers()
        print(temp)

    def do_DELETE(self):
        temp = self._set_headers()
        print(temp)

    def do_PATCH(self):
        temp = self._set_headers()
        print(temp)


# to do:
# baza de date
# get:
# get board, get all boards, get board based on name/date??
# post:
# create board
# put:
# update board, tick board
# delete:
# delete board

# to do daca sunt spartan:
# same shit cu ruleset-uri
# update board unde pui content dintr-un board mai mic in el

conn = sqlite3.connect('gol.db')
c = conn.cursor()
c.execute("CREATE TABLE boards (id int primary key, name text, content text, created_at date, updated_at date)")
c.execute("CREATE TABLE rules (id int primary key, name text, behavior text, created_at date, updated_at date)")
conn.commit()

# We can also close the connection if we are done with it.
# Just be sure any changes have been committed or they will be lost.
conn.close()

server = HTTPServer(('127.0.0.1', 8080), ServiceHandler)
server.serve_forever()
