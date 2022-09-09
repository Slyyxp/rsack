![GitHub last commit](https://img.shields.io/github/last-commit/Slyyxp/rsack) ![GitHub repo size](https://img.shields.io/github/repo-size/Slyyxp/rsack) ![GitHub](https://img.shields.io/github/license/Slyyxp/rsack) ![PyPI - Downloads](https://img.shields.io/pypi/dm/rsack) ![GitHub closed issues](https://img.shields.io/github/issues-closed-raw/Slyyxp/rsack) ![GitHub issues](https://img.shields.io/github/issues-raw/Slyyxp/rsack)

[English](https://github.com/Slyyxp/rsack/blob/master/README.en.md)

# 설치방법
```bash
pip install rsack
```

## 다른 설치방법
```bash
git clone https://github.com/Slyyxp/rsack.git
cd rsack
python setup.py install
```

# 기능 소개
## 벅스
- FLAC16, 320kbps
- 실시간 가사
- 특정 아티스트의 음원 일괄 다운로드
- 상세한 태그
- 동시 다중 다운로드
- 문서화되지 않은 모바일 API를 활용하는 클라이언트

## 지니
- FLAC24, FLAC16, 320kbps
- 특정 아티스트의 음원 일괄 다운로드
- 실시간 가사
- 상세한 태그
- 동시 다중 다운로드
- 문서화되지 않은 모바일 API를 활용하는 클라이언트

# rsack_settings.ini
`rsack_settings.ini` 파일은 여러분이 지정한 폴더에 위치할 수 있습니다

# 위키
[명령 옵션 사용법](https://github.com/Slyyxp/rsack/wiki/Command-Usage)  
[설정 예제](https://github.com/Slyyxp/rsack/wiki/Configuration)  
[음원 사이트 계정 만드는 법](https://github.com/Slyyxp/rsack/wiki/Account-Creation)  

# API 데이터 가져오기
```python
from rsack.clients import bugs

client = bugs.Client() # 클라이언트 오브젝트 초기화
client.auth(username='', password='') # 음원 사이트 계정 인증

artist = client.get_artist(id=80219706) # 아티스트 UID를 사용해서 아티스트 정보를 가져옴
album = client.get_album(id=4071297) # 앨범 UID를 사용해서 앨범 정보를 가져옴
track = client.get_track(id=6147328) # 트랙 UID를 사용해서 트랙 정보를 가져옴
```
```python
from rsack.clients import genie

client = genie.Client() # 클라이언트 오브젝트 초기화
client.auth(username="", password="") # 음원 사이트 계정 인증

album = client.get_album(82525503) # 앨범 UID를 사용해서 앨범 정보를 가져옴
artist = client.get_artist(80006273) # 아티스트 UID를 사용해서 아티스트 정보를 가져옴
track = client.get_stream_meta(95970973) # 트랙 UID를 사용해서 스트리밍 정보를 가져옴
```
# 자주 묻는 질문
### 왜 다운로드 속도가 느린가요?
벅스와 지니의 서버는 한국에 위치해있기 때문에 아시아 외의 지역이라면 느릴 수 있습니다

## 벅스
### 뮤직 비디오를 다운로드할 수 있나요?
스트리밍이 불가능한 파일이라 안됩니다
### 24비트 하이 레졸루션 음원도 다운로드할 수 있나요?
현재 벅스는 24비트 음원을 스트리밍해주지 않습니다

## 지니
### 어떤 이용권을 사용해야 하나요?
KT 혜택에 보시면 24비트 음원 스트리밍이 가능한 이용권이 있습니다
https://product.kt.com/wDic/productDetail.do?ItemCode=1282
