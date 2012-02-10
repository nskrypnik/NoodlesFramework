"""
Base Selenium test methods
"""
import logging
import unittest
import urllib2
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException


class BaseTest(unittest.TestCase):
    def __init__(self, testname, kwargs=None):
        self.e = None
        self.driver = None
        self.method = None
        self.locator = None
        self.url_response = None
        self.testname = "self." + testname
        self.__dict__.update(kwargs)
        self.clean()
        setattr(self, self.method, eval(self.testname))
        super(BaseTest, self).__init__(self.method)

    def setUp(self):
        self.verificationErrors = []

    def tearDown(self):
        self.assertEqual([], self.verificationErrors)

    def clean(self):
        clean_list = ['"', "'", ":", "/", "\\", ".", ", ", "[", "]"]
        clean_method = []
        for letter in self.method:
            if clean_list.count(letter) < 1:
                clean_method.append(letter)
        self.method = ''.join(str(n) for n in clean_method)

    def open_location(self):
        """
        Equal target location with real location
        """
        try:
            self.assertEqual(self.test_location, self.selenium.get_location())
        except AssertionError, self.e:
            self.verificationErrors.append(str(self.e))

    def get_text(self):
        try:
            self.assertEqual(self.locator.split("=")[1],
                              self.selenium.get_text(self.locator))
        except AssertionError, self.e:
            self.verificationErrors.append(str(self.e))

    def assert_url_response(self):
        try:
            urllib2.urlopen(self.url_response)
        except AssertionError, self.e:
            self.verificationErrors.append(str(self.e))

    def verify_equal_find_element_by_css_selector_text(self):
        """
        If locator and text in selector not equal then this test mark as error
        """
        try:
            self.assertEqual(self.locator[0],
                              self.driver.find_element_by_css_selector(
                                                          self.locator[1]).text)
        except AssertionError as e:
            self.driver.get_screenshot_as_file(
                                    "tests/reports/%s_FALSE.png" % self.method)
            self.verificationErrors.append(str(e))

    def assert_equal_find_element_by_css_selector_attr_text(self):
        """
        If locator and attribute text in selector not equal
        then set this test as failure
        """
        self.assertEqual(self.locator[0],
                         self.driver.find_element_by_css_selector(
                             self.locator[1]).get_attribute(self.locator[2]))

    def assert_true_element_by_name(self):
        """
        If element not found by name then make then set this test as failure
        """
        self.assertTrue(self.is_element_present(By.NAME, self.locator))

    def is_element_present(self, how, what):
        try:
            self.driver.find_element(by=how, value=what)
        except NoSuchElementException, self.e:
            self.driver.get_screenshot_as_file(
                                    "tests/reports/%s_FALSE.png" % self.method)
            return False
        return True

    def is_text_present(self):
        try:
            self.failUnless(self.selenium.is_text_present(self.locator))
        except AssertionError, self.e:
            self.verificationErrors.append(str(self.e))
