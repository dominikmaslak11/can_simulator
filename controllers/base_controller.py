class BaseController:
    def __init__(self, app):
        self.app = app

    def log(self, msg):
        self.app.log(msg)
