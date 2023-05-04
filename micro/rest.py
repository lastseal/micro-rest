# -*- coding: utf-8 -*

from flask import Flask
from flask import Request
from flask import request
from flask import send_file
from flask import abort
from flask import redirect
from flask import make_response
from flask import jsonify

from gunicorn.app.base import Application, Config
from gunicorn import glogging
from gunicorn.workers import sync

from . import config

from typing import Optional


import gunicorn
import logging
import json
import os
import jwt
import re

SECRET_KEY = os.getenv("SECRET_KEY")
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER")

class HttpRequest(Request):

    def __init__(self, params, environ, token):
        super(HttpRequest, self).__init__(environ)
        self.params = params
        self.token = token

class HttpResponse:

    def __init__(self, abort):
        self.abort = abort

class HttpServer(Application):

    def __init__(self):

        self.app = Flask(__name__)

        if UPLOAD_FOLDER is not None:
            self.app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

        self.usage = None
        self.callable = None
        self.prog = None
        self.running = False
    
    def api(self, method, endpoint, handle_api):
        
        logging.debug("config route %s %s", method, endpoint)
            
        @self.app.route(endpoint, methods=[method])
        def handle(**params):
            try:
                method = request.method
                if not method:
                    raise Exception({"message":"forbidden, error method","status":403})
                    
                token = None

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
                    
                    de = jwt.decode(token, SECRET_KEY, algorithms="HS256")  

                    logging.debug("JWT: %s", de)

                    allow = [scope for scope in de['scopes'] if re.match(scope['pattern'],endpoint)]
                    if not allow:
                        raise Exception({"message":"forbidden, error scope","status":403})                  

                res = handle_api(HttpRequest(params, request.environ, token))

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

    def run(self, address, port, workers, timeout):

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
        

__singleton__ = HttpServer()

filters = __singleton__.jinja_env.filters

PORT = int(os.getenv("PORT") or "3000")
ADDRESS = os.getenv("ADDRESS") or "0.0.0.0"
WORKERS = int(os.getenv("WORKERS") or 1)
TIMEOUT = int(os.getenv("TIMEOUT") or 30)

def api(method, endpoint):
    def decorator(handle_api):
        __singleton__.api(method, endpoint, handle_api)
        __singleton__.run(ADDRESS, PORT, WORKERS, TIMEOUT)

    return decorator

def run(address="127.0.0.1"):
    __singleton__.run(address, PORT, WORKERS, TIMEOUT)
