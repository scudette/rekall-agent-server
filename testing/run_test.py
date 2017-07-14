import os
import time
import unittest

from selenium import webdriver
from selenium.common import exceptions
from selenium.webdriver.common.by import By

from rekall import session
from rekall_agent import agent


def Retryable(f):
    def wrapper(*args, **kwargs):
        for i in range(10):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                time.sleep(0.1)

        raise e

    return wrapper

DATA_PATH = os.path.join(os.path.dirname(__file__), "data")


def GetAgentClient():
    """Instantiates a client agent from the fixture."""
    config = """
__type__: Configuration
client:
  __type__: GAEClientPolicy
  labels:
  - All
  - Linux
  - GoogleCorp
  manifest_location:
    __type__: HTTPLocation
    base: http://127.0.0.1:8080/api/control
    path_prefix: /manifest
  writeback_path: /tmp/rekall_agent_test.json
"""
    fixture = open(os.path.join(DATA_PATH, "agent.local.json")).read()
    with open("/tmp/rekall_agent_test.json", "wb") as fd:
        fd.write(fixture)

    s = session.Session()
    s.SetParameter("agent_config_data", config)
    return agent.RekallAgent(session=s)

class RekallAgentServerTestSuite(unittest.TestCase):
    def setUp(self):
        self.driver = webdriver.Chrome()
        self.URL = "http://localhost:8080"
        self.client = GetAgentClient()
        self.client_id = self.client._config.client.client_id

    def login_as(self, username, is_admin=False):
        driver = self.driver
        driver.get(self.URL + '/default/logout');
        self.click(By.ID, 'logout')
        self.set_text_box(By.ID, "email", "test@example.com")
        self.click(By.ID, "admin")
        self.click(By.ID, "submit-login")

    @Retryable
    def set_text_box(self, type, name, value):
        driver = self.driver
        box = driver.find_element(type, name)
        box.clear()
        box.send_keys(value)

    @Retryable
    def select_option(self, name, option):
        driver = self.driver
        select = driver.find_element_by_name(name)
        for opt in select.find_elements_by_tag_name('option'):
            if opt.text == option:
                opt.click()
                return

        raise RuntimeError("Option Not found")

    @Retryable
    def find_element(self, type, name):
        return self.driver.find_element(type, name)

    @Retryable
    def click(self, selector, value):
        driver = self.driver
        return driver.find_element(selector, value).click()

    def add_user(self, username, resource, role):
        driver = self.driver
        self.click(By.LINK_TEXT, "USERS")
        self.click(By.ID, "add")
        self.set_text_box(By.NAME, "user", username)
        self.set_text_box(By.NAME, "resource", resource)
        self.select_option("role", role)
        self.click(By.ID, "submit")

    @Retryable
    def retrieve_token(self):
        token = self.driver.find_element_by_id("token").get_attribute("value")
        print token
        return token.split("=")[1]

    def get_token(self, resource):
        driver = self.driver
        self.click(By.LINK_TEXT, "API")
        self.click(By.ID, "mint")
        self.set_text_box(By.NAME, "resource", "/")
        self.click(By.ID, "get_mint")
        return self.retrieve_token()

    def test_initial_setup(self):
        self.login_as("admin@example.com", is_admin=True)
        # Can log into the applications and search for clients.
        self.add_user("test@example.com", "/", "Viewer")
        self.add_user("approver@example.com", "/", "Approver")
        self.root_token = self.get_token("/")
        self.click(By.CLASS_NAME, "close")

        print "Root token: %s" % self.root_token
        self.login_as("test@example.com")

        # Client enrols itself.
        self.client._startup()

        # Search for the client.
        self.set_text_box(By.NAME, "q", self.client_id)
        self.click(By.ID, "go")

        # Check that the client id is found in the search.
        self.find_element(By.XPATH, "//td[contains(., '%s')]" %
                          self.client_id)

        import pdb; pdb.set_trace()


    def tearDown(self):
        self.driver.close()

if __name__ == "__main__":
    unittest.main()
