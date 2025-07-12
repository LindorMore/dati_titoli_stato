import csv
from datetime import datetime
from dateutil.relativedelta import relativedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from github import Github
import time

# === CONFIGURAZIONE ===
ISIN_LIST = ["IT0005496048", "IT0005514473", "IT0005530032"]
CSV_FILE = "dati_btp.csv"
import os
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
REPO_NAME = "LindorMore/dati_titoli_stato"
COMMIT_MESSAGE = f"Aggiornamento {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

# === SELENIUM ===
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=options)

# === FUNZIONE PER ESTRARRE I DATI DA BORSA ITALIANA ===
def estrai_dati(isin):
    url = f"https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/{isin}.html"
    driver.get(url)
    time.sleep(7)
    try:
        prezzo_xpath = '//*[@id="fullcontainer"]/main/section/div[4]/div[5]/article/div/div[2]/div[1]/table/tbody/tr[1]/td[2]/span'
        cedola_xpath = '//*[@id="fullcontainer"]/main/section/div[4]/div[8]/div/article/div/div[2]/div[2]/table/tbody/tr[9]/td[2]/span'
        scadenza_xpath = '//*[@id="fullcontainer"]/main/section/div[4]/div[8]/div/article/div/div[2]/div[2]/table/tbody/tr[5]/td[2]/span'

        prezzo = float(driver.find_element(By.XPATH, prezzo_xpath).text.replace(",", "."))
        cedola_str = driver.find_element(By.XPATH, cedola_xpath).text.strip().replace(",", ".").replace("%", "")
        cedola_semestrale = float(cedola_str) / 2
        scadenza_text = driver.find_element(By.XPATH, scadenza_xpath).text.strip()
        scadenza_data = datetime.strptime(scadenza_text, "%d/%m/%Y")

        return prezzo, cedola_semestrale, scadenza_data
    except Exception as e:
        print(f"❌ Errore per ISIN {isin}: {e}")
        return None, None, None

# === CALCOLI ===
def calcoli(isin, prezzo, cedola_semestrale, scadenza_data):
    oggi = datetime.now()
    mesi_alla_scadenza = (scadenza_data.year - oggi.year) * 12 + scadenza_data.month - oggi.month
    n_cedole = mesi_alla_scadenza // 6
    totale_cedole = cedola_semestrale * n_cedole
    rendimento_totale = ((totale_cedole + 100 - prezzo) / prezzo) * 100
    anni_alla_scadenza = mesi_alla_scadenza / 12
    rendimento_annuo = rendimento_totale / anni_alla_scadenza if anni_alla_scadenza > 0 else 0
    cedola_annua_su_prezzo = (cedola_semestrale * 2 / prezzo) * 100
    return [
        isin,
        round(prezzo, 2),
        round(cedola_semestrale, 2),
        round(cedola_annua_su_prezzo, 2),
        scadenza_data.strftime("%d/%m/%Y"),
        mesi_alla_scadenza,
        round(rendimento_totale, 2),
        round(rendimento_annuo, 2)
    ]

# === ESTRAZIONE ===
dati_finali = [["ISIN", "Prezzo", "Cedola Semestrale", "Cedola Annua %", "Scadenza", "Mesi Scadenza", "Rend. Totale %", "Rend. Annuo %"]]

for isin in ISIN_LIST:
    print(f"🔎 Elaborazione {isin}...")
    prezzo, cedola_semestrale, scadenza = estrai_dati(isin)
    if prezzo is not None:
        dati_finali.append(calcoli(isin, prezzo, cedola_semestrale, scadenza))

driver.quit()

# === SCRITTURA FILE CSV ===
with open(CSV_FILE, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(dati_finali)

print("✅ File CSV generato.")

# === UPLOAD SU GITHUB ===
g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)
with open(CSV_FILE, "r") as f:
    contenuto = f.read()
    try:
        file_esistente = repo.get_contents(CSV_FILE)
        repo.update_file(CSV_FILE, COMMIT_MESSAGE, contenuto, file_esistente.sha)
        print("🔁 File aggiornato su GitHub.")
    except:
        repo.create_file(CSV_FILE, COMMIT_MESSAGE, contenuto)
        print("🆕 File caricato su GitHub.")
