"""
Publie le catalogue "Plateforme" sur Zelty via Selenium.
Usage : python zelty_publish_catalog.py --login <EMAIL> --password <MDP>
"""

import argparse
import os
import sys
import time

XPATH_KEBAB   = '/html/body/div[1]/div[2]/div/div[2]/div/div/div[2]/div/div[2]/div/table/tbody/tr[2]/td[4]/div/div/div/div/div/button/button/span/svg/path'
XPATH_PUBLISH = '/html/body/div[3]/div/div[1]/div/ul/li[2]/label/span'

XPATH_CHECKBOXES = [
    '/html/body/div[5]/div/div[2]/div/div[2]/div/div/div[1]/div/div[1]/button/span/div[1]/input',
    '/html/body/div[5]/div/div[2]/div/div[2]/div/div/div[2]/div/div[1]/button/span/div[1]/input',
    '/html/body/div[5]/div/div[2]/div/div[2]/div/div/div[3]/div/div[1]/button/span/div[1]/input',
]
XPATH_CONFIRM = '/html/body/div[5]/div/div[2]/div/div[3]/div/button[2]/span'

CATALOG_URL = 'https://app.zelty.fr/catalogs?page=1&per_page=25'
LOGIN_URL   = 'https://bo.zelty.fr/login'


def get_driver(headless: bool):
    import subprocess
    for pkg in ('selenium',):
        try:
            __import__(pkg)
        except ImportError:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg, '-q'])

    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    options = Options()
    if headless:
        options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    return webdriver.Chrome(options=options)


def login(driver, login_email: str, password: str):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    print(f"Connexion sur {LOGIN_URL}...")
    driver.get(LOGIN_URL)
    time.sleep(2)

    print(f"  URL actuelle : {driver.current_url}")
    wait = WebDriverWait(driver, 15)

    email_field = wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/form/div[1]/input')))
    email_field.send_keys(login_email)
    print("  Email saisi.")

    pwd_field = driver.find_element(By.XPATH, '/html/body/div[1]/form/div[2]/input')
    pwd_field.send_keys(password)
    print("  Mot de passe saisi.")

    driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
    print("  Formulaire soumis, attente de la redirection...")

    wait.until(EC.url_contains('/home'))
    print(f"  Connecté. URL : {driver.current_url}")


def publish_catalog(driver):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    print(f"Navigation vers {CATALOG_URL}...")
    driver.get(CATALOG_URL)

    wait = WebDriverWait(driver, 15)
    time.sleep(3)

    print(f"  URL actuelle : {driver.current_url}")
    print(f"  Titre page   : {driver.title}")

    # Dump les lignes du tableau pour identifier la position de "Plateforme"
    rows = driver.find_elements(By.CSS_SELECTOR, 'table tbody tr')
    print(f"  Lignes tableau ({len(rows)}) :")
    for i, row in enumerate(rows, 1):
        print(f"    tr[{i}] : {row.text[:80]!r}")

    # Dump tous les boutons de la page
    buttons = driver.find_elements(By.TAG_NAME, 'button')
    print(f"  Boutons trouvés ({len(buttons)}) :")
    for i, btn in enumerate(buttons, 1):
        cls = (btn.get_attribute('class') or '')[:60]
        print(f"    btn[{i}] text={btn.text!r:20} class={cls!r}")

    print("  Recherche de la ligne 'Plateforme'...")
    rows = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'table tbody tr')))
    plateforme_row = None
    for row in rows:
        if 'Plateforme' in row.text:
            plateforme_row = row
            break
    if plateforme_row is None:
        raise RuntimeError("Catalogue 'Plateforme' introuvable dans le tableau")
    print("  Ligne trouvée.")

    print("  Clic sur le menu ⋮ du catalogue Plateforme...")
    kebab = plateforme_row.find_element(By.CSS_SELECTOR, 'button.z-dropdown__action')
    driver.execute_script("arguments[0].click();", kebab)
    time.sleep(0.5)

    print("  Clic sur l'option de publication...")
    publish_btn = wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_PUBLISH)))
    publish_btn.click()
    time.sleep(1)

    print("  Cochage des 3 cases...")
    for i, xpath in enumerate(XPATH_CHECKBOXES, 1):
        cb = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
        if not cb.is_selected():
            driver.execute_script("arguments[0].click();", cb)
        print(f"    Case {i} cochée.")
    time.sleep(0.3)

    print("  Clic sur le bouton de confirmation...")
    confirm = wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_CONFIRM)))
    confirm.click()
    time.sleep(1)

    print("  Catalogue publié.")


def main():
    parser = argparse.ArgumentParser(description='Publie le catalogue Plateforme sur Zelty')
    parser.add_argument('--login',    default=os.environ.get('ZELTY_LOGIN'),    help='Email de connexion')
    parser.add_argument('--password', default=os.environ.get('ZELTY_PASSWORD'), help='Mot de passe')
    parser.add_argument('--headless', action='store_true', default=True,        help='Mode headless (défaut: True)')
    parser.add_argument('--no-headless', dest='headless', action='store_false', help='Désactiver le mode headless')
    args = parser.parse_args()

    if not args.login or not args.password:
        print("ERREUR : --login et --password requis (ou variables ZELTY_LOGIN / ZELTY_PASSWORD)", file=sys.stderr)
        sys.exit(1)

    driver = get_driver(headless=args.headless)
    try:
        login(driver, args.login, args.password)
        publish_catalog(driver)
    finally:
        driver.quit()

    print("\nTerminé.")


if __name__ == '__main__':
    main()
