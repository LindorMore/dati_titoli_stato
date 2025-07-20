import csv
from datetime import datetime
from dateutil.relativedelta import relativedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from github import Github
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os

# === CONFIG ===
ISIN_LIST = ["XS2571924070", "XS1837994794", "US900123BB58", "XS2201851685", "US77586TAE64","IT0005484552"]
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
wait = WebDriverWait(driver, 15)

# === ESTRAZIONE DATI DA BORSA ITALIANA ===
def estrai_dati(isin):
    url = f"https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/{isin}.html"
    driver.get(url)
    
    try:
        prezzo_live_xpath = '//*[@id="fullcontainer"]/main/section/div[4]/div[1]/article/div/div/div[2]/div/span[1]/strong'
        prezzo_chiusura_xpath = '//*[@id="fullcontainer"]/main/section/div[4]/div[5]/article/div/div[2]/div[1]/table/tbody/tr[1]/td[2]/span'
        cedola_semestrale_xpath = '//*[@id="fullcontainer"]/main/section/div[4]/div[8]/div/article/div/div[2]/div[2]/table/tbody/tr[9]/td[2]/span'
        cedola_annua_xpath = '//*[@id="fullcontainer"]/main/section/div[4]/div[8]/div/article/div/div[2]/div[2]/table/tbody/tr[10]/td[2]/span'
        scadenza_xpath = '//*[@id="fullcontainer"]/main/section/div[4]/div[8]/div/article/div/div[2]/div[2]/table/tbody/tr[5]/td[2]/span'
        nazione_xpath = '//*[@id="fullcontainer"]/main/section/div[4]/div[8]/div/article/div/div[2]/div[1]/table/tbody/tr[2]/td[2]/span'
        mercato_xpath = '//*[@id="fullcontainer"]/main/section/div[4]/div[8]/div/article/div/div[2]/div[1]/table/tbody/tr[10]/td[2]/span'
        valuta_xpath = '//*[@id="fullcontainer"]/main/section/div[4]/div[8]/div/article/div/div[2]/div[1]/table/tbody/tr[9]/td[2]/span'

        try:
            prezzo = float(driver.find_element(By.XPATH, prezzo_live_xpath).text.replace(",", "."))
        except:
            prezzo = float(driver.find_element(By.XPATH, prezzo_chiusura_xpath).text.replace(",", "."))

        cedola_semestrale = None
        cedola_annua = None
        
        try:
            cedola_testo = driver.find_element(By.XPATH, cedola_semestrale_xpath).text.strip()
            if cedola_testo != "":
                cedola_semestrale = float(cedola_testo.replace(",", ".").replace("%", ""))
        except:
            pass
        
        if cedola_semestrale is None:
            try:
                cedola_testo = driver.find_element(By.XPATH, cedola_annua_xpath).text.strip()
                if cedola_testo != "":
                    cedola_annua = float(cedola_testo.replace(",", ".").replace("%", ""))
            except:
                pass
        
        if cedola_semestrale is None and cedola_annua is None:
            raise Exception("Cedola non trovata (né semestrale né annua)")

        scadenza_text = driver.find_element(By.XPATH, scadenza_xpath).text.strip()
        if len(scadenza_text.split("/")[-1]) == 2:
            scadenza_data = datetime.strptime(scadenza_text, "%d/%m/%y")
        else:
            scadenza_data = datetime.strptime(scadenza_text, "%d/%m/%Y")

        nazione = driver.find_element(By.XPATH, nazione_xpath).text.strip()
        mercato = driver.find_element(By.XPATH, mercato_xpath).text.strip()
        valuta = driver.find_element(By.XPATH, valuta_xpath).text.strip()

        return prezzo, cedola_semestrale, cedola_annua, scadenza_data, nazione, mercato, valuta

    except Exception as e:
        print(f"❌ Errore per ISIN {isin}: {e}")
        return None, None, None, None, None, None, None

# === CALCOLI ===
def calcoli(isin, prezzo, cedola_semestrale, cedola_annua, scadenza_data, nazione, mercato, valuta):
    oggi = datetime.now()
    mesi_alla_scadenza = (scadenza_data.year - oggi.year) * 12 + scadenza_data.month - oggi.month
    n_cedole = mesi_alla_scadenza // 6
    if cedola_semestrale is not None:
        totale_cedole = cedola_semestrale * n_cedole
        cedola_tipo = "Semestrale"
        cedola_annua_su_prezzo = (cedola_semestrale * 2 / prezzo) * 100
    else:
        totale_cedole = cedola_annua
        cedola_tipo = "Annua"
        cedola_annua_su_prezzo = (cedola_annua / prezzo) * 100

    rendimento_totale = ((totale_cedole + 100 - prezzo) / prezzo) * 100
    anni_alla_scadenza = mesi_alla_scadenza / 12
    rendimento_annuo = rendimento_totale / anni_alla_scadenza if anni_alla_scadenza > 0 else 0

    anni = mesi_alla_scadenza // 12
    mesi = mesi_alla_scadenza % 12
    durata_str = ""
    if anni > 0:
        durata_str += f"{anni}"
    if mesi > 0:
        durata_str += f" {mesi}"
    if durata_str == "":
        durata_str = "0"

    return [
        isin,
        round(prezzo, 2),
        round(cedola_semestrale if cedola_semestrale is not None else 0, 2),
        round(cedola_annua_su_prezzo, 2),
        cedola_tipo,
        scadenza_data.strftime("%d/%m/%Y"),
        durata_str,
        round(rendimento_totale, 2),
        round(rendimento_annuo, 2),
        nazione,
        mercato,
        valuta
    ]

# === ESTRAZIONE E CALCOLO ===
dati_finali = [[
    "ISIN", "Prezzo", "Cedola Semestrale Lorda", "Cedola Annua Lorda %", "Tipo Cedola",
    "Data di Scadenza", "Durata (anni e mesi)", "Rendimento Totale Lordo %", "Rendimento lordo Annuo %",
    "Nazione", "Mercato", "Valuta"
]]

for isin in ISIN_LIST:
    print(f"🔎 Elaborazione {isin}...")
    prezzo, cedola_semestrale, cedola_annua, scadenza, nazione, mercato, valuta = estrai_dati(isin)
    if prezzo is not None:
        dati_finali.append(calcoli(isin, prezzo, cedola_semestrale, cedola_annua, scadenza, nazione, mercato, valuta))

driver.quit()

# === CSV ===
with open(CSV_FILE, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(dati_finali)

print("✅ File CSV generato.")

# === GITHUB UPLOAD ===
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
