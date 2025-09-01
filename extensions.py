# extensions.py
from flask_mysqldb import MySQL

# from flask_login import LoginManager,
from flask_login import UserMixin

mysql = MySQL()
# login_manager = LoginManager()


class User(UserMixin):
    def __init__(self, id, username, name, password_hash):
        self.id = id
        self.username = username
        self.name = name
        self.password_hash = password_hash

    def get_id(self):
        return str(self.id)
