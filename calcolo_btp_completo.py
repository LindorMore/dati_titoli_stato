import csv
from datetime import datetime
from dateutil.relativedelta import relativedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from github import Github
import time
import os

# === CONFIG ===
ISIN_LIST = [
    "XS1968706876", "XS2908645265", "XS2010034692", "XS2579372643", "XS2556596146",
    "XS2326495185", "XS2542485117", "XS2461554145", "XS2589483395", "XS2531612944",
    "XS2524021153", "XS2495153375", "XS2471728562", "XS2529012780", "XS2484910359",
    "XS2571924070", "XS2443898862", "XS2559388018", "XS2603734561", "XS2408549718",
    "XS2584043806", "XS2750332295", "XS2653571346", "XS2477081269", "XS2762232649",
    "XS2648579118", "XS2799193866", "XS2835377534", "XS2847422414", "XS2845805272",
    "XS2804567319", "XS2827515446", "XS2798664550", "XS2819564531", "XS2763580264",
    "XS2805221911", "XS2826890666", "XS2814699613", "XS2836125474", "XS2759780036",
    "XS2814592567", "XS2830991027", "XS2831049387", "XS2762821134", "XS2819622655",
    "XS2836339480", "XS2738468249", "XS2762397001", "XS2831002854", "XS2830999970",
    "XS2763202922", "XS2805018820", "XS2836452580", "XS2759457269", "XS2851747831",
    "XS2831161875", "XS2854407528", "XS2854785866", "XS2831072865", "XS2854445678",
    "XS2854492793", "XS2854205314", "XS2854374767", "XS2854755372", "XS2854784489",
    "XS2854578822", "XS2854493429", "XS2854601856", "XS2854759944", "XS2854466727",
    "XS2854785593", "XS2854582022", "XS2854817056", "XS2854527922", "XS2854748138",
    "XS2854648906", "XS2854647116", "XS2854791889", "XS2854620987", "XS2854662486"
]
CSV_FILE = "dati_btp.csv"
GITHUB_TOKEN = os.environ["MY_GITHUB_TOKEN"]
REPO_NAME = "LindorMore/dati_titoli_stato"
COMMIT_MESSAGE = f"Aggiornamento {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

# === SELENIUM ===
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=options)

def estrai_dati(isin):
    url = f"https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/{isin}.html"
    driver.get(url)
    time.sleep(6)

    try:
        prezzo_xpath = '//*[@id="fullcontainer"]/main/section/div[4]/div[1]/article/div/div/div[2]/div/span[1]/strong'
        prezzo_chiusura_xpath = '//*[@id="fullcontainer"]/main/section/div[4]/div[5]/article/div/div[2]/div[1]/table/tbody/tr[1]/td[2]/span'
        cedola_xpath = '//*[@id="fullcontainer"]/main/section/div[4]/div[8]/div/article/div/div[2]/div[2]/table/tbody/tr[9]/td[2]/span'
        scadenza_xpath = '//*[@id="fullcontainer"]/main/section/div[4]/div[8]/div/article/div/div[2]/div[2]/table/tbody/tr[5]/td[2]/span'
        nazione_xpath = '//*[@id="fullcontainer"]/main/section/div[4]/div[8]/div/article/div/div[2]/div[1]/table/tbody/tr[2]/td[2]/span'

        try:
            prezzo_raw = driver.find_element(By.XPATH, prezzo_xpath).text.strip().replace(",", ".")
            prezzo = float(prezzo_raw) if prezzo_raw else float(driver.find_element(By.XPATH, prezzo_chiusura_xpath).text.strip().replace(",", "."))
        except:
            prezzo = float(driver.find_element(By.XPATH, prezzo_chiusura_xpath).text.strip().replace(",", "."))

        cedola_raw = driver.find_element(By.XPATH, cedola_xpath).text.strip().replace(",", ".").replace("%", "")
        if not cedola_raw:
            raise ValueError("Cedola mancante")
        cedola_semestrale = float(cedola_raw)

        scadenza_text = driver.find_element(By.XPATH, scadenza_xpath).text.strip()
        scadenza_data = datetime.strptime(scadenza_text, "%d/%m/%Y") if len(scadenza_text.split("/")[-1]) == 4 else datetime.strptime(scadenza_text, "%d/%m/%y")

        nazione = driver.find_element(By.XPATH, nazione_xpath).text.strip()

        return prezzo, cedola_semestrale, scadenza_data, nazione

    except Exception as e:
        print(f"❌ Errore per ISIN {isin}: {e}")
        return None, None, None, None

def calcoli(isin, prezzo, cedola_semestrale, scadenza_data, nazione):
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
        round(rendimento_annuo, 2),
        nazione
    ]

# === ESTRAZIONE E CALCOLO ===
dati_finali = [["ISIN", "Prezzo", "Cedola Semestrale Lorda", "Cedola Annua Lorda %", "Data di Scadenza", "Mesi alla Scadenza", "Rendimento Totale Lordo %", "Rendimento lordo Annuo %", "Nazione"]]

for isin in ISIN_LIST:
    print(f"🔎 Elaborazione {isin}...")
    prezzo, cedola, scadenza, nazione = estrai_dati(isin)
    if prezzo and cedola and scadenza:
        dati_finali.append(calcoli(isin, prezzo, cedola, scadenza, nazione))

driver.quit()

# === CSV ===
with open(CSV_FILE, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(dati_finali)

print("✅ File CSV generato.")

# === GITHUB ===
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

