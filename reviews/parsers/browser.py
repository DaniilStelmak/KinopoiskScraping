import os

os.environ["WDM_LOG"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def create_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--lang=ru-RU")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    service = Service(
        executable_path=ChromeDriverManager().install(),
        log_output=os.devnull,
    )

    driver = webdriver.Chrome(
        service=service,
        options=options,
    )
    return driver