from __future__ import print_function
import base64
import json

from httmock import all_requests, HTTMock

import jira_context
from jira_context import JIRA

_save_cookies = getattr(jira_context, '_save_cookies')
_load_cookies = getattr(jira_context, '_load_cookies')


def _prompt(func, prompt):
    print(prompt)
    return 'user' if func == raw_input else 'pass'


def test_no_cookies(tmpdir, capsys):
    jira_context._prompt = _prompt
    JIRA.ABORTED_BY_USER = False
    JIRA.COOKIE_CACHE_FILE_PATH = str(tmpdir.join('.jira_session_json'))
    assert dict() == _load_cookies(JIRA.COOKIE_CACHE_FILE_PATH)

    @all_requests
    def response_content(url, request):
        assert 'user:pass' == base64.b64decode(request.headers['Authorization'].split(' ')[-1])
        if url.path.endswith('/serverInfo'):
            reply = dict(status_code=200, content='{"versionNumbers":[6,4,0]}')
        elif url.path.endswith('/session'):
            assert dict(username='user', password='pass') == json.loads(request.body)
            reply = dict(status_code=200, content='{}', headers={'Set-Cookie': 'JSESSIONID=ABC123;'})
        else:
            raise RuntimeError
        return reply

    with HTTMock(response_content):
        with JIRA() as j:
            assert j.ABORTED_BY_USER is False
            assert j.authentication_failed is False
            assert getattr(j, '_JIRA__authenticated_with_cookies') is False
            assert getattr(j, '_JIRA__authenticated_with_password') is True
            assert j._session.cookies.get_dict()

    assert dict(JSESSIONID='ABC123') == _load_cookies(JIRA.COOKIE_CACHE_FILE_PATH)
    stdout, stderr = capsys.readouterr()
    assert 'JIRA username: \nJIRA password: ' == stdout
    assert '' == stderr