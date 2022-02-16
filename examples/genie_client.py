from rsack.clients import genie

client = genie.Client() # Initialize client object
client.auth(username="", password="") # Authorize user

album = client.get_album(82525503) # Make call for album information using album UID
artist = client.get_artist(80006273) # Make call for artist information using artist UID
track = client.get_stream_meta(95970973) # Make call for stream information using track UID

print(track)