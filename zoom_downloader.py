import requests
from pprint import pprint
import importlib.util
from pathlib import Path
import jwt
from datetime import datetime
import time
from dateutil import tz, parser


# URLs.
base_url = 'https://api.zoom.us/v2'
user_profile = '/users/{user_email}'
recordings = '/users/{user_id}/recordings'


# Load config.
def _load_config():
    config_path = Path.home() / '.zoom_downloader_config.py'
    spec = importlib.util.spec_from_file_location('config', config_path)
    config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config)
    return config


config = _load_config()


def main():
    # Get user_id.
    url = base_url + user_profile.format(user_email=config.user_email)
    response = requests.get(url, headers=zoom_request_headers())
    profile_data = response.json()
    print('Logged in as {} {}'.format(profile_data['first_name'], profile_data['last_name']))

    user_id = profile_data['id']

    # List recordings.
    url = base_url + recordings.format(user_id=user_id)
    response = requests.get(
        url,
        headers=zoom_request_headers(),
        params={
            'from': '1970-01-01',
            'page_size': 300,
        }
    )

    recordings_data = response.json()
    pprint(recordings_data)

    # Download recordings.
    for meeting in recordings_data['meetings']:
        for recording in meeting['recording_files']:
            start_time = parser.parse(recording['recording_start'])
            start_time = convert_utc_to_local(start_time)
            start_time = start_time.strftime('%Y-%m-%d_%H%M')

            file_type = recording['file_type'].lower()
            file_size = sizeof_fmt(recording['file_size'])
            url = recording['download_url']
            filename = f'{start_time}.{file_type}'
            filename = filename.replace(':', '')
            print(f'Downloading {filename} ({file_size})', end=' ... ')
            download_file(url, filename)
            print('Done')


def sizeof_fmt(num, suffix='B'):
    """https://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size"""
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.0f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Y', suffix)


def zoom_request_headers():
    token = get_jwt_token()
    return {
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}',
    }


def get_jwt_token(algorithm='HS256', expiration_seconds=30):
    headers = {
        'alg': algorithm,
        'typ': 'JWT',
    }
    now_ts = int(datetime.timestamp(datetime.now()))
    exp_ts = now_ts + expiration_seconds
    payload = {
        "iss": config.api_key,
        "exp": exp_ts,
    }
    token_bytes = jwt.encode(
        payload,
        config.api_secret,
        algorithm=algorithm,
        headers=headers,
    )
    return token_bytes.decode('utf8')


def download_file(url, local_filename):
    token = get_jwt_token()

    with requests.get(url, stream=True, params={'access_token': token}) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


def convert_utc_to_local(t):
    assert t.tzinfo == tz.tzutc()
    return t.astimezone(tz.tzlocal())


if __name__ == '__main__':
    main()
