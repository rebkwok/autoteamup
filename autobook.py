from argparse import ArgumentParser
from datetime import datetime
import logging

from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

from time import sleep


class Autobooker:

    max_attempts = 3

    def __init__(self, email, password, browser=None):
        self.email = email
        self.password = password
        if browser is not None:
            self._browser = browser
        self.logged_in = False
        self.wait = None
        self.today = datetime.strftime(datetime.now(), "%Y-%m-%d")

    @property
    def browser(self):
        if self._browser is None:
            options = ChromeOptions()
            options.add_argument("headless")

            self._browser = Chrome(options=options)
        if self.wait is None:
            self.wait = WebDriverWait(self._browser, 10)
        return self._browser

    def login(self):
        logging.info("Logging in")
        browser = self.browser
        browser.get("https://goteamup.com/login/")

        login_form = browser.find_element(By.CLASS_NAME, 'processing-on-submit')
        login_username = browser.find_element(By.ID, 'id_email-email')
        login_username.send_keys(self.email)
        login_form.submit()

        login_password = browser.find_element(By.ID, 'id_login-password')
        login_password.send_keys(self.password)
        login_form = browser.find_element(By.CLASS_NAME, 'processing-on-submit')
        login_form.submit()
        self.logged_in = True
        logging.info("Logged in")

    def find_classes(self):
        if not self.logged_in:
            self.login()
        logging.info("Fetching schedule for %s", self.today)
        browser = self.browser
        browser.get(f"https://goteamup.com/p/1953481-freedom-of-flight-aerial/#!month-{self.today}")
        self.wait.until(expected_conditions.element_to_be_clickable((By.CLASS_NAME, "event-wrapper")))

        live_online_urls = {"booked": [], "not_booked": []}
        for attempt in range(1, self.max_attempts + 1):
            logging.info("Attempt %s / %s", attempt, self.max_attempts)
            events = browser.find_elements(By.CLASS_NAME, "event-wrapper")
            try:
                for event in events:
                    url = event.get_attribute("href")
                    if "live-online" in url:
                        if not event.find_elements_by_class_name("icon-circle-ok"):
                            live_online_urls["not_booked"].append(url)
                        else:
                            live_online_urls["booked"].append(url)
                logging.info("Succeeded on attempt %s / %s", attempt, self.max_attempts)
                break
            except StaleElementReferenceException:
                logging.warning("Exception encountered on attempt %s / %s", attempt, self.max_attempts)
                if attempt <= self.max_attempts:
                    logging.info("Sleeping for 1 second")
                    sleep(1)

        return live_online_urls

    def book_classes(self):
        if not self.logged_in:
            self.login()
        button_xpath_selector = (By.XPATH, "//*[contains(text(), 'Register for Single Class')]")
        browser = self.browser
        all_classes =  self.find_classes()
        book_urls =all_classes["not_booked"]
        for url in book_urls:
            browser.get(url)
            self.wait.until(expected_conditions.element_to_be_clickable(button_xpath_selector))
            button = browser.find_element(*button_xpath_selector)
            button.click()
            logging.info("Booked - %s", url)
        return {"new_booked": book_urls, "already_booked": all_classes["booked"]}


if __name__ == "__main__":
    logging.basicConfig(level="INFO", format="%(asctime)s:%(levelname)s: %(message)s")
    parser = ArgumentParser()
    parser.add_argument("--username", "-u")
    parser.add_argument("--password", "-p")
    args = parser.parse_args()
    Autobooker(args.username, args.password).book_classes()
