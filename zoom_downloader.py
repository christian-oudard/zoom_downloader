import requests
from pprint import pprint

user_email = 'a@b.com'
token = ''

# URLs.
base_url = 'https://api.zoom.us/v2'
user_profile = '/users/{user_email}'
recordings = '/users/{user_id}/recordings'

# User authentication.
# api_key = ''
# TODO JWT:
# import jwt
# from datetime import datetime, timedelta

# def get_jwt_token(expiration=30):
#     header = {
#       "alg": "HS256",
#       "typ": "JWT",
#     }
#     ts = {
#       "iss": "API_KEY",
#       "exp": int(datetime.timestamp(datetime.now() + timedelta(seconds=expiration))),
#     }
#     # jwt.encode({'some': 'payload'}, 'secret', algorithm='HS256', headers={'kid': ''})



headers = {
    'Accept': 'application/json',
    'Authorization': f'Bearer {token}',
}

# Get user_id.
url = base_url + user_profile.format(user_email=user_email)
response = requests.get(url, headers=headers)
profile_data = response.json()
print('Logged in as {} {}'.format(profile_data['first_name'], profile_data['last_name']))

user_id = profile_data['id']

# List recordings.
url = base_url + recordings.format(user_id=user_id)
response = requests.get(
    url,
    headers=headers,
    params={
        'from': '1970-01-01',
        'page_size': 300,
    }
)

recordings_data = response.json()
pprint(recordings_data)

download_urls = []
for meeting in recordings_data['meetings']:
    meeting_id = meeting['id']
    for recording in meeting['recording_files']:
        download_urls.append(recording['download_url'])

# Download recordings.
def download_file(url, local_filename):
    with requests.get(url, stream=True, params={'access_token': token}) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

# for i, url in enumerate(download_urls):
#     download_file(url, 'video{}.mp4'.format(i))
