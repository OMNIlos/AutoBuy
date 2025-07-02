from selenium import webdriver
from selenium_gift_bot.auth import TelegramWebNavigator
from selenium_gift_bot.gift_logic import GiftBuyer

def main():
    driver = webdriver.Safari()
    driver.get('https://web.telegram.org')
    nav = TelegramWebNavigator(driver)
    nav.open_and_auth()
    nav.go_to_gift_menu()
    buyer = GiftBuyer(driver)
    buyer.buy_gift_if_profitable()

if __name__ == '__main__':
    main() 