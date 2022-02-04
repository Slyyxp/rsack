
<p align="center">
  <img src="https://ptpimg.me/5502wc.gif">
</p>

# Installation
```
pip install rsack
```
# To Do
- [ ] Refactor Download() to allow artist batching  
- [ ] Genie support

## Example Usage
```
rsack --bugs --url "https://music.bugs.co.kr/album/4070269"
rsack -b -u "https://music.bugs.co.kr/album/4070269"
```

# Command Usage
Command  | Description  | Example
------------- | ------------- | -------------
-u, --url | URL  | `https://music.bugs.co.kr/album/20343816`, `https://music.bugs.co.kr/artist/80327433`
-b, --bugs | Specify Bugs Webstore | No additional parameters
-cfg, --config | Re-creates config file | No additional parameters

# Settings.ini
Key  | Description  | Example
------------- | ------------- | -------------
username | Email used for sign-in  | `Slyyxp@protonmail.com`
password | Password | Password123
threads | Number of simultaenous downloads | `2`
path | Download path | `C:\Users\Slyyxp\Desktop`
lyrics | Lyrics type (Timed/Untimed) | `T` `N`
