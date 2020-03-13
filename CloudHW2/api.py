from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sqlite3

size_limit = 100
tick_limit = 1000


def is_json(myjson):
    try:
        json.loads(myjson)
    except ValueError:
        return False
    return True


def try_parse_int(s, val=None):
    try:
        return int(s)
    except ValueError:
        return val
    except TypeError:
        return val


def zeros_table(w, h):
    s = "["
    for i in range(h):
        s += "["
        line = ""
        for j in range(w):
            line += "0,"
        line = line.rstrip(",")
        s += line + "],"
    s = s.rstrip(",")
    s += "]"
    return s


def gol_tick(con, beh):
    m = [-1, 0, 1]
    new_board = con.copy()
    for i in range(len(con)):
        for j in range(len(con[0])):
            neighbours = 0
            for x in m:
                for y in m:
                    if 0 <= i + x < len(con) and 0 <= j + y < len(con[0]) and not (x == 0 and y == 0):
                        if con[i + x][j + y] == 1:
                            neighbours += 1
            if con[i][j] == 0:
                new_board[i][j] = beh[0][neighbours]
            elif con[i][j] == 1:
                new_board[i][j] = beh[1][neighbours]
    return new_board


def verify_board(bs):
    bs = json.loads(bs)
    if type(bs) != list:
        return False
    if len(bs) == 0:
        return False
    w = len(bs[0])
    for i in bs:
        if type(i) != list:
            return False
        elif len(i) != w:
            return False
        for j in i:
            if try_parse_int(j) != 0 and try_parse_int(j) != 1:
                return False
    return True


def verify_behavior(rs):
    rs = json.loads(rs)
    if type(rs) != list:
        return False
    if len(rs) != 2:
        return False
    for i in rs:
        if type(i) != list:
            return False
        elif len(i) != 9:
            return False
        for j in i:
            if try_parse_int(j) not in [0, 1]:
                return False
    return True


class Database:
    array_keys = ["content", "behavior"]

    def __init__(self):
        self.conn = sqlite3.connect('gol.db')

    def create_tables(self):
        c = self.conn.cursor()
        c.execute(
            "CREATE TABLE rules (id integer primary key autoincrement, name text unique, behavior text, created_at date, updated_at date)")
        c.execute(
            "CREATE TABLE boards (id integer primary key autoincrement, name text unique, content text, id_rules integer, created_at date, updated_at date, FOREIGN KEY(id_rules) REFERENCES rules(id))")
        c.execute("INSERT INTO rules(name,behavior,created_at,updated_at) values('default','[[0,0,0,1,0,0,0,0,0],[0,0,1,1,0,0,0,0,0]]',date('now'),date('now'))")
        self.conn.commit()

    def drop_tables(self):
        c = self.conn.cursor()
        c.execute("DROP TABLE boards")
        c.execute("DROP TABLE rules")
        self.conn.commit()

    def row_to_dict(self, row, keys):
        d = dict()
        for i in range(len(row)):
            if keys[i] in self.array_keys:
                d[keys[i]] = json.loads(row[i])
            else:
                d[keys[i]] = row[i]
        return d

    def get_boards(self, params):
        c = self.conn.cursor()
        if try_parse_int(params['desc']) == 1:
            c.execute("SELECT * from (SELECT * from boards order by ? desc) limit 10 offset ?",
                      (params['criteria'], int(params['page']) * 10 - 10,))
        else:
            c.execute("SELECT * from (SELECT * from boards order by ?) limit 10 offset ?",
                      (params['criteria'], int(params['page']) * 10 - 10,))
        rows = c.fetchall()
        return list(
            map(lambda x: self.row_to_dict(x, ["id", "name", "content", "id_rules", "created_at", "updated_at"]), rows))

    def get_rulesets(self, params):
        c = self.conn.cursor()
        c.execute("SELECT * from (SELECT * from rules order by id) limit 10 offset ?",
                  (int(params['page']) * 10 - 10,))
        rows = c.fetchall()
        return list(
            map(lambda x: self.row_to_dict(x, ["id", "name", "behavior", "created_at", "updated_at"]), rows))

    def get_board(self, params):
        c = self.conn.cursor()
        if 'id' in params.keys():
            c.execute(
                "SELECT id as id, name as name, content as content, id_rules as id_rules, created_at as created_at, updated_at as updated_at from boards where id = ?",
                (params['id'],))
        elif 'name' in params.keys():
            c.execute(
                "SELECT id as id, name as name, content as content, id_rules as id_rules, created_at as created_at, updated_at as updated_at from boards where name = ?",
                (params['name'],))
        rows = c.fetchall()
        if len(rows) > 0:
            return list(
                map(lambda x: self.row_to_dict(x, ["id", "name", "content", "id_rules", "created_at", "updated_at"]),
                    rows))[0]
        return rows

    def get_ruleset(self, params):
        c = self.conn.cursor()
        if 'id' in params.keys():
            c.execute(
                "SELECT * from rules where id = ?",
                (params['id'],))
        elif 'name' in params.keys():
            c.execute(
                "SELECT * from rules where name = ?", (params['name'],))
        rows = c.fetchall()
        if len(rows) > 0:
            return list(
                map(lambda x: self.row_to_dict(x, ["id", "name", "behavior", "created_at", "updated_at"]),
                    rows))[0]
        return rows

    def create_board(self, params):
        c = self.conn.cursor()
        c.execute(
            "INSERT into boards(name, content, id_rules, created_at, updated_at) values(?,?,?,date('now'),date('now'))",
            (params['name'], params['board'], params['id_rules']))
        self.conn.commit()

    def create_ruleset(self, params):
        c = self.conn.cursor()
        c.execute("INSERT into rules(name,behavior,created_at,updated_at) values(?,?,date('now'),date('now'))",
                  (params['name'], params['behavior']))
        self.conn.commit()

    def update_board(self, params):
        c = self.conn.cursor()
        c.execute("UPDATE boards set content = ?, updated_at = date('now') where id = ?",
                  (params['board'], params['id']))
        self.conn.commit()

    def update_rules(self, params):
        c = self.conn.cursor()
        c.execute("UPDATE boards set id_rules = ?, updated_at = date('now') where id = ?",
                  (params['id_rules'], params['id']))
        self.conn.commit()

    def update_name(self, params):
        c = self.conn.cursor()
        c.execute("UPDATE boards set name = ?, updated_at = date('now') where id = ?",
                  (params['name'], params['id']))
        self.conn.commit()

    def delete_board(self, params):
        c = self.conn.cursor()
        if 'id' in params.keys():
            c.execute("DELETE from boards where id = ?", (params['id'],))
        elif 'name' in params.keys():
            c.execute("DELETE from boards where name = ?", (params['name'],))
        self.conn.commit()

    def delete_ruleset(self, params):
        c = self.conn.cursor()
        if 'id' in params.keys():
            c.execute("DELETE from rules where id = ?", (params['id'],))
        elif 'name' in params.keys():
            c.execute("DELETE from rules where name = ?", (params['name'],))
        self.conn.commit()


class ServiceHandler(BaseHTTPRequestHandler):
    status_dict = {404: 'Not Found', 400: 'Bad Request', 201: 'Created', 200: 'OK'}

    def get_board(self, params):
        if 'id' in params.keys() or 'name' in params.keys() and None not in params.values():
            return db.get_board(params)
        else:
            return 400

    def get_ruleset(self, params):
        if 'id' in params.keys() or 'name' in params.keys() and None not in params.values():
            return db.get_ruleset(params)
        else:
            return 400

    def get_boards(self, params):
        if 'page' not in params.keys():
            params['page'] = 1
        if 'desc' not in params.keys():
            params['desc'] = 0
        if 'criteria' not in params.keys():
            params['criteria'] = "id"
        elif params['criteria'] not in ["name", "updated_at", "created_at", "content"]:
            params['criteria'] = "id"
        return db.get_boards(params)

    def get_rulesets(self, params):
        if 'page' not in params.keys():
            params['page'] = 1
        return db.get_rulesets(params)

    def create_board(self, params):
        if 'width' not in params.keys() or 'height' not in params.keys() or 'name' not in params.keys():
            return 400
        else:
            if type(try_parse_int(params['height'])) != int or type(try_parse_int(params['width'])) != int:
                return 400
            params['height'] = try_parse_int(params['height'])
            params['width'] = try_parse_int(params['width'])
            if not (0 < params['height'] <= size_limit and 0 < params['width'] <= size_limit):
                return 400
            params['board'] = zeros_table(params['width'], params['height'])
            if 'id_rules' not in params.keys():
                params['id_rules'] = 1
            db.create_board(params)
        return 201

    def create_ruleset(self, params):
        if 'name' not in params.keys() or 'behavior' not in params.keys():
            return 400
        else:
            if not verify_behavior(params['behavior']):
                return 400
            else:
                db.create_ruleset(params)
        return 201

    def import_board(self, params):
        if 'board' not in params.keys() or 'name' not in params.keys():
            return 400
        else:
            if 'id_rules' not in params.keys():
                params['id_rules'] = 1
            if not is_json(params['board']):
                return 400
            else:
                if not verify_board(params['board']):
                    return 400
                else:
                    db.create_board(params)
        return 201

    def update_board(self, u_id, params):
        good_id = try_parse_int(u_id)
        if type(good_id) != int:
            return 400
        else:
            b = db.get_board({'id': good_id})
            if len(b) < 1:
                return 404
            else:
                params['id'] = good_id
                ok = [False, False, False]
                if 'name' in params.keys():
                    if params['name'] is not None:
                        ok[0] = True
                    else:
                        return 400
                if 'id_rules' in params.keys():
                    if type(try_parse_int(params['id_rules'])) == int:
                        ok[1] = True
                    else:
                        return 400
                if 'board' in params.keys():
                    if verify_board(params['board']):
                        ok[2] = True
                    else:
                        return 400
                if ok[0]:
                    db.update_name(params)
                if ok[1]:
                    db.update_rules(params)
                if ok[2]:
                    db.update_board(params)
        return 200

    def delete_board(self, params):
        if 'id' in params.keys() or 'name' in params.keys() and None not in params.values():
            if len(db.get_board(params)) > 0:
                db.delete_board(params)
            else:
                return 404
        else:
            return 400
        return 200

    def delete_ruleset(self, params):
        if 'id' in params.keys() or 'name' in params.keys() and None not in params.values():
            if len(db.get_ruleset(params)) > 0:
                db.delete_ruleset(params)
            else:
                return 404
        else:
            return 400
        return 200

    def update_cell(self, u_id, params):
        good_id = try_parse_int(u_id)
        if type(good_id) != int:
            return 400
        else:
            b = db.get_board({'id': good_id})
            if len(b) < 1:
                return 404
            else:
                if 'x' in params.keys() and 'y' in params.keys() and 'val' in params.keys():
                    if type(try_parse_int(params['x'])) == int and type(try_parse_int(params['y'])) and try_parse_int(
                            params['val']) in [0, 1]:
                        pass
                    else:
                        return 400
                else:
                    return 400
                new_b = b['content'].copy()
                if 0 <= try_parse_int(params['x']) < len(b['content']) and 0 <= try_parse_int(params['y']) < len(
                        b['content'][0]):
                    x_int = try_parse_int(params['x'])
                    y_int = try_parse_int(params['y'])
                    new_b[x_int][y_int] = try_parse_int(params['val'])
                else:
                    return 400
                params['board'] = json.dumps(new_b)
                params['id'] = good_id
                db.update_board(params)
        return 200

    def tick(self, params):
        b = []
        if 'id' in params.keys() or 'name' in params.keys() and None not in params.values():
            b = db.get_board(params)
        if len(b) < 1:
            return 404
        else:
            print(b['id_rules'])
            r = db.get_ruleset({'id': int(b['id_rules'])})
            if len(r) == 0:
                return 400
            else:
                con = b['content']
                beh = r['behavior']
                if 'count' not in params.keys():
                    params['count'] = 1
                params['count'] = try_parse_int(params['count'])
                if type(params['count']) != int:
                    return 400
                if not (0 < params['count'] <= tick_limit):
                    return 400
                for i in range(params['count']):
                    con = gol_tick(con, beh)
                db.update_board({'id': b['id'], 'board': json.dumps(con)})
                return 200

    def get_params(self, req):
        if req[0] != "/":
            return None, None
        else:
            req = req.split('?')
            par = dict()
            if len(req) > 1:
                for i in req[1].split("&"):
                    i = i.split('=')
                    if len(i) != 2:
                        return None, None
                    par[i[0]] = i[1]
            return req[0][1:], par

    def result_status(self, result):
        self.send_response(result)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        error = str(result) + ": " + self.status_dict[result]
        self.wfile.write(bytes(error, 'utf-8'))

    def do_GET(self):
        req, params = self.get_params(self.path)
        if req == "get_board":  # id OR name
            result = self.get_board(params)
        elif req == "get_ruleset":  # id OR name
            result = self.get_ruleset(params)
        elif req == "get_rulesets":
            result = self.get_rulesets(params)  # page
        elif req == "get_boards":  # criteria, page, desc (ALL OPTIONAL)
            result = self.get_boards(params)
        else:
            result = 400
        if not result:
            result = 404

        if type(result) == int:
            self.result_status(result)
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/json')
            self.end_headers()
            self.wfile.write(bytes(json.dumps(result), 'utf-8'))

    def do_POST(self):
        req, params = self.get_params(self.path)
        if req == "create_board":
            result = self.create_board(params)  # width, height, name (MANDATORY), id_rules (OPTIONAL)
        elif req == "create_ruleset":
            result = self.create_ruleset(params)  # name (MANDATORY), behavior (MANDATORY)
        elif req == "import_board":
            result = self.import_board(params)  # board, name (MANDATORY) id_rules (OPTIONAL)
        elif req == "tick":
            result = self.tick(params)  # id OR name, count (OPTIONAL)
        else:
            result = 400
        self.result_status(result)

    def do_PUT(self):
        req, params = self.get_params(self.path)
        req = req.rstrip("/")
        req = req.split("/")
        if len(req) != 2:
            result = 400
        else:
            if req[0] == "update_board":  # /id/ name, id_rules, board (ALL OPTIONAL)
                result = self.update_board(req[1], params)
            elif req[0] == "update_cell":  # /id/ x, y, val (ALL MANDATORY)
                result = self.update_cell(req[1], params)
            else:
                result = 400
        self.result_status(result)

    def do_DELETE(self):
        req, params = self.get_params(self.path)
        if req == "delete_board":
            result = self.delete_board(params)  # id OR name
        elif req == "delete_ruleset":
            result = self.delete_ruleset(params)  # id OR name
        else:
            result = 400
        self.result_status(result)


db = Database()
server = HTTPServer(('127.0.0.1', 8080), ServiceHandler)
server.serve_forever()
