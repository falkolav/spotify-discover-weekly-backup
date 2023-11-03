import logging
import azure.functions as func
import requests as r
import base64
import os

logging.basicConfig(level=logging.INFO)

app = func.FunctionApp()

client_id = os.environ["CLIENT_ID"]
client_secret = os.environ["CLIENT_SECRET"]
refresh_token = os.environ["REFRESH_TOKEN"]
spotify_id = os.environ["SPOTIFY_ID"]
backup_playlist_id = os.environ["BACKUP_PLAYLIST_ID"]
user_id = os.environ["USER_ID"]
discover_weekly_playlist_id = ""

auth_token = client_id + ':' + client_secret
auth_token_bytes = auth_token.encode('utf-8')
auth_token_b64 = base64.b64encode(auth_token_bytes).decode("utf-8")


def get_access_token_using_refresh_token(refresh_token:str = refresh_token) -> str:
    """
    Returns an access token using a refresh token.
    """
    headers = {
    "Authorization": f"Basic {auth_token_b64}",
    'Content-Type': 'application/x-www-form-urlencoded'
    }

    headers = {
    "Authorization": f"Basic ZThkZWUxNmEwNGYxNGZmMmJmYmVkMmNmYTQ4ZTgzZDY6NTcyMDE4YzA3NmE0NGRlMDgxYTBlZTY2MWQ5NDdmYjQ=",
    'Content-Type': 'application/x-www-form-urlencoded'
    }

    payload = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': client_id
    }

    response = r.post("https://accounts.spotify.com/api/token", headers=headers, data=payload)
    return response.json()['access_token']

def get_trackids_from_playlist(playlist_id:str = discover_weekly_playlist_id, access_token:str = None) -> list:
    """
    Returns a list of track ids from a playlist.
    """
    if access_token is None:
        access_token = get_access_token_using_refresh_token()

    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = r.get(f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?fields=items.track.uri&limit=50", headers=headers)
    tracks = response.json()['items']
    track_ids = []
    for track in tracks:
        track_ids.append(track['track']['uri'])
    return track_ids

def get_current_users_id(access_token:str = None) -> str:
    if access_token is None:
        access_token = get_access_token_using_refresh_token()

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    response = r.get("https://api.spotify.com/v1/me", headers=headers)
    user_id = response.json()['id']
    return user_id


def get_discover_weekly_playlist_id(user_id:str = user_id, access_token:str = None) -> str:
    """
    Returns the discover weekly playlist id.
    """
    if access_token is None:
        access_token = get_access_token_using_refresh_token()

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    response = r.get(f"https://api.spotify.com/v1/search?q=Discover+Weekly&type=playlist&owner=Spotify", headers=headers)
    discover_weekly_playlist_id = response.json()['playlists']['items'][0]['id']
    return discover_weekly_playlist_id


def check_if_track_is_in_playlist(track_id:str, playlist_id:str = backup_playlist_id, access_token:str = None) -> bool:
    if access_token is None:
        access_token = get_access_token_using_refresh_token()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    offset = 0
    limit = 50
    
    while True:
        response = r.get(f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?fields=items.track.uri&limit={limit}&offset={offset}", headers=headers)
        tracks = response.json()['items']

        if not tracks:
            break

        for track in tracks:
            if track_id == track['track']['uri']:
                return True
        
        offset += limit

    return False

def insert_track_in_playlist(playlist_id:str = backup_playlist_id, track_id:str = None, access_token:str = None) -> None:
    """
    Inserts track in a playlist.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    if check_if_track_is_in_playlist(track_id, playlist_id, access_token):
        logging.info(f"{track_id} is already in playlist.")
        return f"{track_id} is already in playlist."
    
    payload = {
        "uris": [track_id]
    }
    response = r.post(f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks", headers=headers, json=payload)
    
    if response:
        logging.info(f"Successfully added {track_id} to playlist.")
        return response.json()


@app.schedule(schedule="0 0 6 * * 1", arg_name="myTimer", use_monitor=False) 
def timer_trigger(myTimer: func.TimerRequest) -> None:
    logging.info("Starting script.")

    logging.info("Getting access token.")
    access_token = get_access_token_using_refresh_token()
    
    logging.info("Getting access token.")
    user_id = get_current_users_id(access_token=access_token)
    
    logging.info("Getting discover weekly playlist id.")
    discover_weekly_playlist_id = get_discover_weekly_playlist_id(user_id=user_id, access_token=access_token)
    
    logging.info("Getting discover weekly playlist track ids.")
    discover_weekly_track_ids = get_trackids_from_playlist(access_token=access_token, playlist_id=discover_weekly_playlist_id)
    
    logging.info("Inserting tracks into backup playlist.")
    for track_id in discover_weekly_track_ids:
        insert_track_in_playlist(playlist_id=backup_playlist_id, track_id=track_id,access_token=access_token)