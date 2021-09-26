import pytest
import requests
import json
import dataclasses
from datetime import datetime


@dataclasses.dataclass()
class User:
    user_pool_id: str
    username: str
    email: str
    password: str
    nickname: str


class UserProvider:
    def __init__(self, awscli):
        self.pool = {}
        self.awscli = awscli

    def provide(self, base_url, email, password):
        if email in self.pool:
            return self.pool[email]

        server_config = json.loads(requests.get(base_url + '/config').content)
        user_pool_id = server_config['aws']['cognito']['userPoolId']
        uid = datetime.now().strftime("%Y%m%d%H%M%S%f")
        nickname = f'nickname_{uid}'
        self.awscli.CognitoIdentity.admin_create_user(user_pool_id, email, email, nickname)
        self.awscli.CognitoIdentity.admin_set_user_password(user_pool_id, email, password)
        user = User(user_pool_id=user_pool_id, username=email, email=email, password=password, nickname=nickname)
        self.pool[email] = user
        return user

    def remove_all(self):
        for user in self.pool.values():
            self.awscli.CognitoIdentity.admin_delete_user(user.user_pool_id, user.username)


@pytest.fixture(scope="session")
def user_provider(awscli):
    user_provider = UserProvider(awscli)
    yield user_provider
    user_provider.remove_all()


@pytest.fixture
def registered_user(base_url, user_provider):
    email = 'tsutomu.yasui+asobann-test@gmail.com'
    password = '123Abc@!$'
    user = user_provider.provide(base_url, email, password)
    return user
