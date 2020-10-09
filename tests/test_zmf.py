import requests
import requests_mock

session = requests.Session()
adapter = requests_mock.Adapter()
session.mount('mock://', adapter)

adapter.register_uri('GET', 'mock://test.com', text='data')

#TODO: https://www.nerdwallet.com/blog/engineering/5-pytest-best-practices/
#TODO: https://docs.pytest.org/en/stable/goodpractices.html
def test_zmf():
    assert True