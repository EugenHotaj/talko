"""A simple Flask web server.

This server handles communicating with the backend servers, most importantly
translating between HTTP/1.1 requests to our custom RPC protocol.
""" 

from datetime import datetime
import os

import flask
import json
from talko import client


def main(data_address, broadcast_address):
    backend_client = client.Client(data_address, broadcast_address)

    app = flask.Flask(__name__)

    @app.route('/')
    @app.route('/home')
    @app.route('/index')
    def home():
        user_id = int(flask.request.args.get('user_id'))
        return flask.render_template(
                'home.html', client=backend_client, user_id=user_id)


    def _user_avatar_text(user_name):
        return ''.join([split[0] for split in user_name.split(' ')])


    @app.context_processor
    def chat_avatar_text():

        def _fn(chat, user_id):
            if len(chat['users']) > 2:
                return f'+{len(chat["users"]) - 1}'
            user_id = int(user_id)
            other = [u for u in chat['users'] if u['user_id'] != user_id][0]
            return _user_avatar_text(other['user_name'])

        return dict(chat_avatar_text=_fn)


    @app.context_processor
    def user_avatar_text():

        def _fn(user):
            return _user_avatar_text(user['user_name'])

        return dict(user_avatar_text=_fn)


    @app.context_processor
    def title():

        def _fn(chat, user_id):
            if len(chat['users']) > 2:
                return chat['title']
            user_id = int(user_id)
            other = [u for u in chat['users'] if u['user_id'] != user_id][0]
            return other['user_name']

        return dict(title=_fn)


    @app.template_filter('date')
    def timestamp_to_date(timestamp):
        timestamp /= 1000
        dt = datetime.fromtimestamp(timestamp)
        return datetime.strftime(dt, '%B %d')


    @app.template_filter('datetime')
    def timestamp_to_datetime(timestamp):
        timestamp /= 1000
        dt = datetime.fromtimestamp(timestamp)
        return datetime.strftime(dt, '%B %d | %I:%M %p')


    app.run(debug=True)
