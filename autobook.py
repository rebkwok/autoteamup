from argparse import ArgumentParser
import calendar
from datetime import datetime
import logging

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

from time import sleep


class LoginException(Exception):
    pass


class Autobooker:

    max_attempts = 3

    def __init__(self, email, password, browser=None):
        self.email = email
        self.password = password
        if browser is not None:
            self._browser = browser
        else:
            self._browser = None
        self.logged_in = False
        self.wait = None
        self.date_format = "%Y-%m-%d"

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

        self.wait.until(expected_conditions.element_to_be_clickable((By.ID, 'id_email-email')))
        login_form = browser.find_element(By.CLASS_NAME, 'processing-on-submit')
        login_username = browser.find_element(By.ID, 'id_email-email')
        login_username.send_keys(self.email)
        login_form.submit()

        self.wait.until(expected_conditions.element_to_be_clickable((By.ID, 'id_login-password')))
        login_password = browser.find_element(By.ID, 'id_login-password')
        login_password.send_keys(self.password)
        login_form = browser.find_element(By.CLASS_NAME, 'processing-on-submit')
        login_form.submit()

        if "dashboard" in browser.current_url:
            self.logged_in = True
            logging.info("Logged in")
        else:
            logging.error("Failed to log in")
            raise LoginException("Failed to log in")

    def find_classes(self, month=None):
        live_online_urls = {"booked": [], "not_booked": []}

        if not self.logged_in:
            self.login()
        today = datetime.today()
        if month and month != today.month:
            date_to_fetch = datetime(year=today.year, month=month, day=1)
        else:
            date_to_fetch = today
        month_to_fetch = calendar.month_name[date_to_fetch.month]
        date_string = datetime.strftime(date_to_fetch, self.date_format)
        logging.info("Fetching schedule for %s", month_to_fetch)
        browser = self.browser
        browser.get(f"https://goteamup.com/p/1953481-freedom-of-flight-aerial/#!month-{date_string}")

        try:
            self.wait.until(expected_conditions.element_to_be_clickable((By.CLASS_NAME, "event-wrapper")))
        except TimeoutException:
            logging.info("No classes scheduled in %s", month_to_fetch)
            return live_online_urls

        for attempt in range(1, self.max_attempts + 1):
            logging.info("Attempt %s / %s", attempt, self.max_attempts)
            events = browser.find_elements(By.CLASS_NAME, "event-wrapper")
            try:
                for event in events:
                    url = event.get_attribute("href")
                    if "live-online" in url:
                        if not event.find_elements_by_class_name("icon-circle-ok"):
                            if url not in live_online_urls["not_booked"]:
                                live_online_urls["not_booked"].append(url)
                        else:
                            if url not in live_online_urls["booked"]:
                                live_online_urls["booked"].append(url)
                logging.info("Succeeded on attempt %s / %s", attempt, self.max_attempts)
                refetch_events = browser.find_elements(By.CLASS_NAME, "event-wrapper")
                logging.info(f"original = {len(events)}, refetched = {len(refetch_events)}")
                break
            except StaleElementReferenceException:
                logging.warning("Exception encountered on attempt %s / %s", attempt, self.max_attempts)
                if attempt <= self.max_attempts:
                    logging.info("Sleeping for 1 second")
                    sleep(1)

        return live_online_urls

    def book_classes(self, month=None, all_class_urls=None):
        if not self.logged_in:
            self.login()
        button_xpath_selector = (By.XPATH, "//*[contains(text(), 'Register for Single Class')]")
        browser = self.browser
        if all_class_urls is None:
            all_class_urls = self.find_classes(month)
        book_urls = all_class_urls["not_booked"]
        logging.info("Urls to follow: %s", book_urls)

        for url in book_urls:
            browser.get(url)
            self.wait.until(expected_conditions.element_to_be_clickable(button_xpath_selector))
            button = browser.find_element(*button_xpath_selector)
            button.click()
            logging.info("Booked - %s", url)
        return {"new_booked": book_urls, "already_booked": all_class_urls["booked"]}


if __name__ == "__main__":
    logging.basicConfig(level="INFO", format="%(asctime)s:%(levelname)s: %(message)s")
    parser = ArgumentParser()
    parser.add_argument("username")
    parser.add_argument("password")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--month", "-m", type=int, help="Month (numerical format) e.g. for June enter 6")
    args = parser.parse_args()
    autobooker = Autobooker(args.username, args.password)
    if args.dry_run:
        found_classes = autobooker.find_classes(month=args.month)
        logging.info("Found: %s", found_classes)
    else:
        autobooker.book_classes(month=args.month)
