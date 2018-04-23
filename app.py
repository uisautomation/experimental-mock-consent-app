import logging
import os

from flask import (
    Flask, request, render_template, redirect, jsonify,
    session as flask_session
)
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient


LOG = logging.getLogger()
logging.basicConfig(level=logging.INFO)

CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
SCOPES = ['hydra.consent']

TOKEN_ENDPOINT = os.environ.get('TOKEN_ENDPOINT')
CONSENT_ENDPOINT = os.environ.get('CONSENT_ENDPOINT')

app = Flask(__name__)
app.secret_key = 'super-secret'


@app.route('/')
def index():
    return 'This is the consent app'


@app.route('/healthz')
def healthz():
    return jsonify({'status': 'ok'})


@app.route('/logout')
def logout():
    if 'subject' in flask_session:
        del flask_session['subject']
        return jsonify({'message': 'logged out'})
    return jsonify({'message': 'no user logged in'})


@app.route('/consent', methods=['GET'])
def consent_get():
    # Handle GET-requests to the consent endpoint. These are initiated when the
    # User Agent (UA) navigates to the token request URL and Hydra redirects them
    # here. We are passed an id for the consent request in the query string
    # which we should validate, examine and accept or reject as we see fit.
    #
    # If no user interaction is needed to accept/reject the request, we
    # immediately do so and redirect the UA back to Hydra by means of the
    # redirect URI Hydra gives us. No interaction is needed if the user is
    # logged in or the "prompt:none" scope is requested and there is no current
    # logged in user.
    #
    # If user interaction *is* needed, we render a simple login form which will
    # POST its content back to the '/consent' endpoint. This is handled by
    # consent_post() below.

    session = get_session()

    error = request.args.get('error')
    error_description = request.args.get('error_description')
    if error is not None:
        return render_template('error.html', error=error, error_description=error_description)

    consent_id = request.args.get('consent')
    if consent_id is None:
        return render_template(
            'error.html',
            error='no consent id',
            error_description='No consent ID was given for the request')

    r = session.get(CONSENT_ENDPOINT + consent_id)
    r.raise_for_status()
    consent = r.json()

    # Note: flask.session does not support .get()
    try:
        subject = flask_session['subject']
    except KeyError:
        subject = None

    if 'prompt:none' in consent['requestedScopes'] and subject is None:
        return _reject_request(session, consent, 'user not logged in')

    if subject is not None:
        return _accept_request(session, consent, subject)

    return render_template('consent.html', consent=consent)


@app.route('/consent', methods=['POST'])
def consent_post():
    # Handle POST requests to the consent endpoint. These are initiated after
    # user interaction with the form rendered by consent_get(). The form
    # provides us with the current Hydra consent id and the scheme and
    # identifier for the user which should be logged in.
    #
    # We take the scheme and identifier from the form and use them to construct
    # a subject for the consent request which we immediately grant.

    session = get_session()

    consent_id = request.args.get('consent')
    if consent_id is None:
        return 'no consent id'

    r = session.get(CONSENT_ENDPOINT + consent_id)
    r.raise_for_status()
    consent = r.json()

    scheme = request.form['scheme']
    identifier = request.form['identifier']

    subject = ':'.join([scheme, identifier])
    flask_session['subject'] = subject

    return _accept_request(session, consent, subject)


def _accept_request(session, consent, subject):
    session.patch(
        CONSENT_ENDPOINT + consent['id'] + '/accept', json={
            'grantScopes': consent['requestedScopes'],
            'subject': subject,
        })

    return redirect(consent['redirectUrl'])


def _reject_request(session, consent, reason):
    session.patch(
        CONSENT_ENDPOINT + consent['id'] + '/reject', json={
            'reason': reason,
        })

    return redirect(consent['redirectUrl'])


def get_session():
    LOG.info('Fetching initial token')
    client = BackendApplicationClient(client_id=CLIENT_ID)
    session = OAuth2Session(client=client)
    access_token = session.fetch_token(
        timeout=1, token_url=TOKEN_ENDPOINT,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scope=SCOPES,
        verify=False)
    LOG.info('Got access token: %r', access_token)

    return session
