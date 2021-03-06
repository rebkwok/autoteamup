import calendar
from datetime import datetime
import logging
from multiprocessing import Process
import os

from flask import Flask, render_template, request
from flask_wtf import FlaskForm, RecaptchaField
from flask_wtf.csrf import CSRFProtect
from selenium.webdriver import Chrome, ChromeOptions
from wtforms import StringField, PasswordField, SelectField
from wtforms.validators import DataRequired

from autobook import Autobooker, LoginException


DEBUG = os.environ.get("DEBUG", False)
SECRET_KEY = os.environ['SECRET_KEY']
RECAPTCHA_PUBLIC_KEY = os.environ['RECAPTCHA_PUBLIC_KEY']
RECAPTCHA_PRIVATE_KEY = os.environ['RECAPTCHA_PRIVATE_KEY']

app = Flask(
    __name__,
    static_url_path='',
    static_folder='static',
    template_folder='templates'
)
app.config.from_object(__name__)
app.testing = DEBUG
csrf = CSRFProtect(app)



logging.basicConfig(level="INFO", format="%(asctime)s:%(levelname)s: %(message)s")


class LoginForm(FlaskForm):
    username = StringField('Username (email)', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    month = SelectField('Month', coerce=int)
    recaptcha = RecaptchaField()


def get_driver():
    chrome_options = ChromeOptions()
    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    driver = Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), chrome_options=chrome_options)
    return driver


def get_next_3_months():
    today = datetime.today()
    return [
        (today.month + i, calendar.month_name[today.month + i]) for i in range(3)
    ]


def _book_classes(username, password, month, all_class_urls):
    autobooker = Autobooker(username, password, browser=get_driver())
    autobooker.book_classes(month, all_class_urls)


@app.route('/', methods=['GET', 'POST'])
def book_home():
    form = LoginForm()
    form.month.choices = get_next_3_months()
    context = {}
    if form.validate_on_submit():
        # do the booking
        username = form.username.data
        password = form.password.data
        autobooker = Autobooker(username, password, browser=get_driver())
        month = form.month.data
        month_string = calendar.month_name[month]
        try:
            class_urls = autobooker.find_classes(month=month)
            if "submit_check" in request.form:
                context = {"action": "check", "classes": class_urls, "month": month_string}
            else:
                if class_urls.get("not_booked"):
                    booking_process = Process(  # Create a daemonic process with heavy "my_func"
                        target=_book_classes,
                        args=(username, password, month, class_urls),
                        daemon=True
                    )
                    booking_process.start()
                context = {"action": "book", "classes": class_urls, "month": month_string}
            return render_template("completed.html", **context)
        except Exception as e:
            if isinstance(e, LoginException):
                context = {"login_error": True}
            else:
                context = {"unknown_error": True}
            logging.error(str(e))
    context["form"] = form
    return render_template("home.html", **context)


if __name__ == "__main__":
    app.run()
