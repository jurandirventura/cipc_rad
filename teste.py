from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

# Abre a página do goole para teste do firefox

options = Options()

options.binary_location = "/snap/firefox/current/usr/lib/firefox/firefox"

service = Service("/snap/bin/geckodriver")

driver = webdriver.Firefox(
    service=service,
    options=options
)

driver.get("https://www.google.com")

print(driver.title)

input("ENTER para sair")

driver.quit()
