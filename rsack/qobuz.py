from qobuz_dl.core import QobuzDL

from rsack.utils import Settings

class Download():
    def __init__(self, url):
        self.settings = Settings().Qobuz()
        self.url = url
        self._download()
        
    def _download(self):
        qobuz = QobuzDL(directory=self.settings['path'], quality=self.settings['quality'])
        qobuz.get_tokens()
        qobuz.initialize_client(email=self.settings['email'], pwd=self.settings['password'], app_id=qobuz.app_id, secrets=qobuz.secrets)
        qobuz.handle_url(self.url)
    