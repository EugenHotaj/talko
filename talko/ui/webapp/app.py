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
        return flask.render_template('home.html', user_id=user_id)

    @app.route('/chats')
    def get_chats():
        user_id = int(flask.request.args.get('user_id'))
        return backend_client.get_chats(user_id)

    @app.route('/messages')
    def get_messages():
        user_id = int(flask.request.args.get('user_id'))
        chat_id = int(flask.request.args.get('chat_id'))
        return backend_client.get_messages(chat_id)

    @app.route('/messages', methods=['POST'])
    def insert_message():
        try:
            user_id = flask.request.form['user_id']
            chat_id = flask.request.form['chat_id']
            message_text = flask.request.form['message_text']
        except (TypeError, KeyError):
            return flask.abort(400)
        a = backend_client.insert_message(chat_id, user_id, message_text)
        messages = backend_client.get_messages(chat_id)['messages']
        return flask.render_template(
                'messages.html', user_id=int(user_id), messages=messages)
        

    app.run(debug=True)
