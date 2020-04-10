import logging
import os

from flask import Flask, render_template, request
from flask_wtf import FlaskForm, RecaptchaField
from flask_wtf.csrf import CSRFProtect
from selenium.webdriver import Chrome, ChromeOptions
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired

from autobook import Autobooker


DEBUG = os.environ.get("DEBUG", False)
SECRET_KEY = os.environ['SECRET_KEY']
RECAPTCHA_PUBLIC_KEY = os.environ['RECAPTCHA_PUBLIC_KEY']
RECAPTCHA_PRIVATE_KEY = os.environ['RECAPTCHA_PRIVATE_KEY']

app = Flask(__name__)
app.config.from_object(__name__)
app.testing = DEBUG
csrf = CSRFProtect(app)

logging.basicConfig(level="INFO", format="%(asctime)s:%(levelname)s: %(message)s")


class LoginForm(FlaskForm):
    username = StringField('username', validators=[DataRequired()])
    password = PasswordField('password', validators=[DataRequired()])
    recaptcha = RecaptchaField()


def get_driver():
    chrome_options = ChromeOptions()
    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    driver = Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), chrome_options=chrome_options)
    return driver


@app.route('/', methods=['GET', 'POST'])
def book_home():
    form = LoginForm()
    if form.validate_on_submit():
        # do the booking
        autobooker = Autobooker(form.username.data, form.password.data, browser=get_driver())
        if "submit_check" in request.form:
            class_urls = autobooker.find_classes()
            context = {"action": "check", "classes": class_urls}
        else:
            class_urls = autobooker.book_classes()
            context = {"action": "book", "classes": class_urls}
        return render_template("completed.html", **context)
    return render_template("home.html", form=form)


if __name__ == "__main__":
    app.run()
