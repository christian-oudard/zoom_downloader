import requests
from pprint import pprint
import importlib.util
from pathlib import Path
import jwt
from datetime import date, datetime, timedelta
import time
from dateutil import tz, parser
import sys
import os.path


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
    print('Getting recordings for the past 6 months.')
    url = base_url + recordings.format(user_id=user_id)
    meetings_data = []

    range_size = 30
    for i in range(0, 6):
        end_date = date.today() - timedelta(days=i*range_size)
        start_date = end_date - timedelta(days=range_size - 1)
        end_date = end_date.strftime('%Y-%m-%d')
        start_date = start_date.strftime('%Y-%m-%d')
        print(f'Requesting recordings from {start_date} to {end_date}')

        params = {
            'from': start_date,
            'to': end_date,
            'page_size': 300,
        }
        response = requests.get(
            url,
            headers=zoom_request_headers(),
            params=params,
        )

        recordings_data = response.json()
        print('Got {} meetings.'.format(len(recordings_data['meetings'])))
        meetings_data.extend(recordings_data['meetings'])

    total_count = sum(
        1
        for meeting in meetings_data
        for recording in meeting['recording_files']
    )

    print()
    print(f'Downloading {total_count} recordings.')

    # Download recordings.
    for meeting in meetings_data:
        for recording in meeting['recording_files']:
            start_time = parser.parse(recording['recording_start'])
            start_time = convert_utc_to_local(start_time)
            start_time = start_time.strftime('%Y-%m-%d_%H%M%S')

            file_type = recording['file_type'].lower()
            url = recording['download_url']
            filename = f'{start_time}.{file_type}'
            filename = filename.replace(':', '')
            download_file(url, filename, recording['file_size'])


def sizeof_fmt(num, suffix='B'):
    """https://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size"""
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
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


def download_file(url, local_filename, file_size):
    if os.path.exists(local_filename):
        print(f'{local_filename} already exists.')
        return

    file_size = sizeof_fmt(file_size)
    print(f'Downloading {local_filename} ({file_size})', end=' ... ')
    sys.stdout.flush()

    token = get_jwt_token()

    with requests.get(url, stream=True, params={'access_token': token}) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    print('Done')


def convert_utc_to_local(t):
    assert t.tzinfo == tz.tzutc()
    return t.astimezone(tz.tzlocal())


if __name__ == '__main__':
    main()
