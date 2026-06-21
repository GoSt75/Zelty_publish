"""
Publie le catalogue "Plateforme" sur Zelty via Selenium.
Usage : python zelty_publish_catalog.py --login <EMAIL> --password <MDP>
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime

XPATH_KEBAB   = '/html/body/div[1]/div[2]/div/div[2]/div/div/div[2]/div/div[2]/div/table/tbody/tr[2]/td[4]/div/div/div/div/div/button/button/span/svg/path'
XPATH_PUBLISH = '/html/body/div[3]/div/div[1]/div/ul/li[2]/label/span'

XPATH_CHECKBOXES = [
    '/html/body/div[5]/div/div[2]/div/div[2]/div/div/div[1]/div/div[1]/button/span/div[1]/input',
    '/html/body/div[5]/div/div[2]/div/div[2]/div/div/div[2]/div/div[1]/button/span/div[1]/input',
    '/html/body/div[5]/div/div[2]/div/div[2]/div/div/div[3]/div/div[1]/button/span/div[1]/input',
]
XPATH_CONFIRM = '/html/body/div[5]/div/div[2]/div/div[3]/div/button[2]/span'

# bo.zelty.fr = back-office (login), app.zelty.fr = front catalogue
LOGIN_URL   = 'https://bo.zelty.fr/login'
CATALOG_URL = 'https://app.zelty.fr/catalogs?page=1&per_page=25'

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')


def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, f"zelty_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

    fmt = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s', datefmt='%H:%M:%S')

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(fmt)

    logging.basicConfig(level=logging.DEBUG, handlers=[file_handler, console_handler])
    logging.info(f"Log écrit dans : {log_file}")
    return log_file


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

    logging.info(f"[LOGIN] Navigation vers {LOGIN_URL}...")
    driver.get(LOGIN_URL)
    time.sleep(2)
    logging.info(f"[LOGIN] Page chargée — URL : {driver.current_url} | Titre : {driver.title!r}")

    wait = WebDriverWait(driver, 15)

    logging.info("[LOGIN] Attente du champ email...")
    email_field = wait.until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/form/div[1]/input')))
    email_field.click()
    email_field.clear()
    driver.execute_script("arguments[0].value = arguments[1];", email_field, login_email)
    email_field.send_keys(' ')
    email_field.send_keys('\b')  # backspace pour déclencher les events JS
    logging.info(f"[LOGIN] Email saisi ({login_email}).")
    time.sleep(0.5)

    pwd_field = wait.until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/form/div[2]/input')))
    pwd_field.click()
    pwd_field.clear()
    driver.execute_script("arguments[0].value = arguments[1];", pwd_field, password)
    pwd_field.send_keys(' ')
    pwd_field.send_keys('\b')
    logging.info("[LOGIN] Mot de passe saisi.")
    time.sleep(0.5)

    logging.info("[LOGIN] Clic sur le bouton de soumission...")
    driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
    logging.info(f"[LOGIN] Formulaire soumis — URL immédiate : {driver.current_url}")

    logging.info("[LOGIN] Attente de la redirection post-login...")
    wait.until(EC.url_changes(LOGIN_URL))
    logging.info(f"[LOGIN] Redirection détectée — URL : {driver.current_url} | Titre : {driver.title!r}")

    if 'login' in driver.current_url:
        raise RuntimeError(f"Echec du login — toujours sur : {driver.current_url}")

    time.sleep(2)
    bo_cookies = driver.get_cookies()
    logging.info(f"[LOGIN] Cookies bo.zelty.fr ({len(bo_cookies)}) : {[c['name'] for c in bo_cookies]}")

    # Zelty utilise un flux SSO : bo.zelty.fr/auth?redirectURL=<app_url> pose le token sur app.zelty.fr
    sso_url = f"https://bo.zelty.fr/auth?redirectURL={CATALOG_URL}"
    logging.info(f"[LOGIN] Flux SSO vers : {sso_url}")
    driver.get(sso_url)
    time.sleep(3)
    logging.info(f"[LOGIN] Après SSO — URL : {driver.current_url} | Titre : {driver.title!r}")

    if 'login' in driver.current_url or driver.current_url.startswith('https://bo.zelty.fr'):
        raise RuntimeError(f"SSO échoué — toujours sur bo : {driver.current_url}")


def publish_catalog(driver):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    # Le SSO dans login() nous a déjà amenés sur CATALOG_URL — on recharge pour être sûr
    logging.info(f"[CATALOG] Rechargement de {CATALOG_URL}...")
    driver.get(CATALOG_URL)

    wait = WebDriverWait(driver, 15)
    time.sleep(3)
    logging.info(f"[CATALOG] Page chargée — URL : {driver.current_url} | Titre : {driver.title!r}")

    if 'login' in driver.current_url or driver.current_url.startswith('https://bo.zelty.fr'):
        cookies = driver.get_cookies()
        raise RuntimeError(
            f"Session perdue après SSO — URL inattendue : {driver.current_url}\n"
            f"Cookies ({len(cookies)}) : {[c['name'] for c in cookies]}"
        )

    # Dump lignes tableau
    rows = driver.find_elements(By.CSS_SELECTOR, 'table tbody tr')
    logging.info(f"[CATALOG] Lignes tableau ({len(rows)}) :")
    for i, row in enumerate(rows, 1):
        logging.info(f"  tr[{i}] : {row.text[:80]!r}")

    # Dump boutons
    buttons = driver.find_elements(By.TAG_NAME, 'button')
    logging.info(f"[CATALOG] Boutons trouvés ({len(buttons)}) :")
    for i, btn in enumerate(buttons, 1):
        cls = (btn.get_attribute('class') or '')[:60]
        logging.info(f"  btn[{i}] text={btn.text!r:20} class={cls!r}")

    logging.info("[CATALOG] Recherche de la ligne 'Plateforme' dans le tableau...")
    rows = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'table tbody tr')))
    plateforme_row = None
    for i, row in enumerate(rows, 1):
        if 'Plateforme' in row.text:
            plateforme_row = row
            logging.info(f"[CATALOG] Ligne 'Plateforme' trouvée à tr[{i}] : {row.text[:80]!r}")
            break
    if plateforme_row is None:
        raise RuntimeError("Catalogue 'Plateforme' introuvable dans le tableau")

    logging.info("[CATALOG] Recherche du bouton menu ⋮ (kebab) dans td[4]...")
    action_cell = plateforme_row.find_element(By.CSS_SELECTOR, 'td:nth-child(4)')
    buttons_in_cell = action_cell.find_elements(By.TAG_NAME, 'button')
    logging.info(f"[CATALOG]   Boutons dans td[4] ({len(buttons_in_cell)}) : {[b.get_attribute('class') for b in buttons_in_cell]}")
    kebab = buttons_in_cell[0]
    logging.info(f"[CATALOG] Bouton kebab sélectionné — classe : {kebab.get_attribute('class')!r} | visible : {kebab.is_displayed()}")
    driver.execute_script("arguments[0].click();", kebab)
    logging.info("[CATALOG] Clic kebab effectué.")
    time.sleep(0.5)

    logging.info(f"[CATALOG] Attente de l'option de publication (XPATH={XPATH_PUBLISH})...")
    publish_btn = wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_PUBLISH)))
    logging.info(f"[CATALOG] Option publication trouvée — texte : {publish_btn.text!r}")
    publish_btn.click()
    logging.info("[CATALOG] Clic publication effectué.")
    time.sleep(1)

    logging.info(f"[CATALOG] Cochage des {len(XPATH_CHECKBOXES)} cases...")
    for i, xpath in enumerate(XPATH_CHECKBOXES, 1):
        cb = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
        already = cb.is_selected()
        if not already:
            driver.execute_script("arguments[0].click();", cb)
        logging.info(f"[CATALOG]   Case {i} — était cochée : {already} → cochée : {cb.is_selected()}")
    time.sleep(0.3)

    logging.info(f"[CATALOG] Attente du bouton de confirmation (XPATH={XPATH_CONFIRM})...")
    confirm = wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_CONFIRM)))
    logging.info(f"[CATALOG] Bouton confirmation trouvé — texte : {confirm.text!r}")
    confirm.click()
    logging.info("[CATALOG] Clic confirmation effectué.")
    time.sleep(1)

    logging.info("[CATALOG] Catalogue publié avec succès.")


def main():
    log_file = setup_logging()

    parser = argparse.ArgumentParser(description='Publie le catalogue Plateforme sur Zelty')
    parser.add_argument('--login',    default=os.environ.get('ZELTY_LOGIN'),    help='Email de connexion')
    parser.add_argument('--password', default=os.environ.get('ZELTY_PASSWORD'), help='Mot de passe')
    parser.add_argument('--headless', action='store_true', default=True,        help='Mode headless (défaut: True)')
    parser.add_argument('--no-headless', dest='headless', action='store_false', help='Désactiver le mode headless')
    args = parser.parse_args()

    if not args.login or not args.password:
        logging.error("--login et --password requis (ou variables ZELTY_LOGIN / ZELTY_PASSWORD)")
        sys.exit(1)

    driver = get_driver(headless=args.headless)
    try:
        login(driver, args.login, args.password)
        publish_catalog(driver)
    except Exception:
        logging.exception("Erreur fatale")
        raise
    finally:
        driver.quit()

    logging.info("Terminé.")


if __name__ == '__main__':
    main()
