import requests
import requests_mock

session = requests.Session()
adapter = requests_mock.Adapter()
session.mount('mock://', adapter)

adapter.register_uri('GET', 'mock://test.com', text='data')

def test_zmf():
    assert True