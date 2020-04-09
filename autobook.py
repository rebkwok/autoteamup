from argparse import ArgumentParser
from datetime import datetime
import logging

from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

from time import sleep


def book(email, password):
    options = ChromeOptions()
    options.add_argument("headless")
    browser = Chrome(options=options)

    wait = WebDriverWait(browser, 10)
    logging.info("Logging in")

    browser.get("https://goteamup.com/login/")

    login_form = browser.find_element(By.CLASS_NAME, 'processing-on-submit')
    login_username = browser.find_element(By.ID, 'id_email-email')
    login_username.send_keys(email)
    login_form.submit()

    login_password = browser.find_element(By.ID, 'id_login-password')
    login_password.send_keys(password)
    login_form = browser.find_element(By.CLASS_NAME, 'processing-on-submit')
    login_form.submit()
    logging.info("Logged in")

    date_string = datetime.strftime(datetime.now(), "%Y-%m-%d")
    logging.info("Fetching schedule for %s", date_string)
    browser.get(f"https://goteamup.com/p/1953481-freedom-of-flight-aerial/#!month-{date_string}")
    sleep(2)
    events = browser.find_elements(By.CLASS_NAME, "event-wrapper")
    book_urls = []
    for event in events:
        if not event.find_elements_by_class_name("icon-circle-ok"):
            book_urls.append(event.get_attribute("href"))

    book_urls = [url for url in book_urls if "live-online" in url]
    if not book_urls:
        logging.info("No unbooked classes found for this month")
    button_xpath_selector = (By.XPATH, "//*[contains(text(), 'Register for Single Class')]")
    for url in book_urls:
        browser.get(url)
        wait.until(expected_conditions.element_to_be_clickable(button_xpath_selector))
        button = browser.find_element(*button_xpath_selector)
        button.click()
        logging.info("Booked - %s", url)


if __name__ == "__main__":
    logging.basicConfig(level="INFO", format="%(asctime)s:%(levelname)s: %(message)s")
    parser = ArgumentParser()
    parser.add_argument("--username", "-u")
    parser.add_argument("--password", "-p")
    args = parser.parse_args()
    book(args.username, args.password)
