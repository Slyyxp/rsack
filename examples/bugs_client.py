from rsack.clients import bugs

client = bugs.Client() # Initialize client object
client.auth(username='', password='') # Authorize user

artist_response = client.get_meta(type='artist', id=80219706) # Make call for artist information using artist UID
album_response = client.get_meta(type='album', id=4071297) # Make call for album information using album UID
track_response = client.get_meta(type='track', id=6147328) # Make call for track information using track UID
