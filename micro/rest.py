# -*- coding: utf-8 -*

from flask import Flask
from flask import Request
from flask import request
from flask import send_file
from flask import abort
from flask import redirect
from flask import make_response
from flask import jsonify

from flask_cors import CORS

from gunicorn.app.base import Application, Config
from gunicorn import glogging
from gunicorn.workers import sync

from . import config

import gunicorn
import logging
import json
import os
import jwt
import re

SECRET_KEY = os.getenv("SECRET_KEY")
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER")
CORS_ENABLE = os.getenv("CORS_ENABLE", "FALSE").upper() == "TRUE"
PORT = int(os.getenv("PORT") or "3000")
ADDRESS = os.getenv("ADDRESS") or "0.0.0.0"
WORKERS = int(os.getenv("WORKERS") or 1)
TIMEOUT = int(os.getenv("TIMEOUT") or 30)

class HttpRequest(Request):

    def __init__(self, params, environ, token, user):
        super(HttpRequest, self).__init__(environ)
        self.params = params
        self.token = token
        self.user = user

class HttpResponse:

    def __init__(self, abort):
        self.abort = abort

class HttpServer(Application):

    def __init__(self):

        self.app = Flask(__name__)
        self.route_counter = 0

        if UPLOAD_FOLDER is not None:
            self.app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
            logging.info("upload folder: %s", UPLOAD_FOLDER)

        if CORS_ENABLE:
            self.cors = CORS(self.app)
            logging.info("CORS enabled")

        self.usage = None
        self.callable = None
        self.prog = None
        self.running = False
    
    def api(self, method, endpoint, handle_api):
        
        logging.debug("config route %s %s", method, endpoint)
            
        #@self.app.route(endpoint, methods=[method])
        def handle(**params):
            try:
                method = request.method
                if not method:
                    raise Exception({"message":"forbidden, error method","status":403})
                    
                token = None
                user = {}

                if SECRET_KEY is not None:
                    endpoint = method + ' ' + request.url

                    headers = request.headers
                    logging.debug("headers: %s", dict(headers))
                    
                    token = request.args.get("token")
                    
                    if 'Authorization' in headers:

                        data = headers['Authorization'].split(' ')
                        logging.debug("Authorization: %s", data)

                        if data[0] != "Bearer":
                            raise Exception({"message":"forbidden, error authorization","status":403})
                        
                        token = data[1]

                    elif token is None:
                        raise Exception({"message":"forbidden, error headers","status":403})                    

                    logging.debug("token: %s", token)
                    
                    user = jwt.decode(token, SECRET_KEY, algorithms="HS256")  

                    logging.debug("JWT: %s", user)

                    allow = [scope for scope in user['scopes'] if re.match(scope['pattern'],endpoint)]
                    if not allow:
                        raise Exception({"message":"forbidden, error scope","status":403})                  

                res = handle_api(HttpRequest(params, request.environ, token, user))

                res_type = type(res)
                if res_type == dict or res_type == list:
                    return json.dumps(res)

                return res

            except Exception as ex:
                logging.error(ex)

                error = ex.args[0]

                if type(error) == str:
                    status = 500
                    message = error
                else:
                    status = error.get('status', 500)
                    message = error.get('message')

                error_json = jsonify(message=message, status=status)

                return abort( make_response(error_json, status) )

        unique_name = f"handle_{self.route_counter}"
        self.route_counter += 1
        self.app.add_url_rule(endpoint, unique_name, handle, methods=[method])

    def get(self, endpoint):
        def decorator(handle_api_get):
            self.api("GET", endpoint, handle_api_get)
        return decorator

    def post(self, endpoint):
        def decorator(handle_api_post):
            self.api("POST", endpoint, handle_api_post)
        return decorator

    def put(self, endpoint):
        def decorator(handle_api_put):
            self.api("PUT", endpoint, handle_api_put)
        return decorator

    def delete(self, endpoint):
        def decorator(handle_api_delete):
            self.api("DELETE", endpoint, handle_api_delete)
        return decorator

    def patch(self, endpoint):
        def decorator(handle):
            self.api("PATCH", endpoint, handle)
        return decorator
    
    def run(self, address=ADDRESS, port=PORT, workers=WORKERS, timeout=TIMEOUT):

        if not self.running:

            self.running = True

            self.cfg = Config()

            self.cfg.set("worker_class", "gunicorn.workers.sync.SyncWorker")
            self.cfg.set("workers", workers)
            self.cfg.set("threads", workers)
            self.cfg.set("bind", f"{address}:{port}")
            self.cfg.set("timeout", timeout)

            Application.run(self)
        
    load = lambda self:self.app
        

server = HttpServer()

app = server.app

filters = server.app.jinja_env.filters

def api(method, endpoint):
    def decorator(handle_api):
        server.api(method, endpoint, handle_api)
        server.run(ADDRESS, PORT, WORKERS, TIMEOUT)

    return decorator

def run(address="127.0.0.1"):
    server.run(address, PORT, WORKERS, TIMEOUT)
