import os

import flask

app = flask.Flask(__name__)


@app.route('/')
def home():
    return flask.render_template('home.html')


if __name__ == '__main__':
    app.run(debug=True)
