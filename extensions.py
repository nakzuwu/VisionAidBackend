from authlib.integrations.flask_client import OAuth

oauth = OAuth()

def init_oauth(app):
    oauth.init_app(app)
    oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        api_base_url='https://www.googleapis.com/oauth2/v2/',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
