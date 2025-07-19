import csv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from github import Github
import time
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

# === Funzione helper per mesi -> anni e mesi ===
def mesi_in_anni_mesi(mesi):
    anni = mesi // 12
    mesi_residui = mesi % 12
    parti = []
    if anni > 0:
        parti.append(f"{anni} anno{'i' if anni > 1 else ''}")
    if mesi_residui > 0:
        parti.append(f"{mesi_residui} mese{'i' if mesi_residui > 1 else ''}")
    return " e ".join(parti) if parti else "0 mesi"

# === ESTRAZIONE DATI DA BORSA ITALIANA ===
def estrai_dati(isin):
    url = f"https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/{isin}.html"
    driver.get(url)
    time.sleep(5)

    try:
        prezzo_live_xpath = '//*[@id="fullcontainer"]/main/section/div[4]/div[1]/article/div/div/div[2]/div/span[1]/strong'
        prezzo_chiusura_xpath = '//*[@id="fullcontainer"]/main/section/div[4]/div[5]/article/div/div[2]/div[1]/table/tbody/tr[1]/td[2]/span'
        cedola_semestrale_xpath = '//*[@id="fullcontainer"]/main/section/div[4]/div[8]/div/article/div/div[2]/div[2]/table/tbody/tr[9]/td[2]/span'
        cedola_annua_xpath = '//*[@id="fullcontainer"]/main/section/div[4]/div[8]/div/article/div/div[2]/div[2]/table/tbody/tr[10]/td[2]/span'
        scadenza_xpath = '//*[@id="fullcontainer"]/main/section/div[4]/div[8]/div/article/div/div[2]/div[2]/table/tbody/tr[5]/td[2]/span'
        nazione_xpath = '//*[@id="fullcontainer"]/main/section/div[4]/div[8]/div/article/div/div[2]/div[1]/table/tbody/tr[2]/td[2]/span'

        # Prezzo: live o chiusura
        try:
            prezzo = float(driver.find_element(By.XPATH, prezzo_live_xpath).text.replace(",", "."))
        except:
            prezzo = float(driver.find_element(By.XPATH, prezzo_chiusura_xpath).text.replace(",", "."))

        # Cedola: prima semestrale, se non c'è usa annua
        try:
            cedola_str = driver.find_element(By.XPATH, cedola_semestrale_xpath).text.strip().replace(",", ".").replace("%", "")
            cedola = float(cedola_str)
            tipo_cedola = "Semestrale"
        except:
            try:
                cedola_str = driver.find_element(By.XPATH, cedola_annua_xpath).text.strip().replace(",", ".").replace("%", "")
                cedola = float(cedola_str)
                tipo_cedola = "Annua"
            except:
                print(f"❌ Cedola non trovata (né semestrale né annua) per ISIN {isin}")
                return None, None, None, None, None

        # Scadenza
        scadenza_text = driver.find_element(By.XPATH, scadenza_xpath).text.strip()
        if len(scadenza_text.split("/")[-1]) == 2:
            scadenza_data = datetime.strptime(scadenza_text, "%d/%m/%y")
        else:
            scadenza_data = datetime.strptime(scadenza_text, "%d/%m/%Y")

        # Nazione
        nazione = driver.find_element(By.XPATH, nazione_xpath).text.strip()

        return prezzo, cedola, tipo_cedola, scadenza_data, nazione

    except Exception as e:
        print(f"❌ Errore per ISIN {isin}: {e}")
        return None, None, None, None, None

# === CALCOLI ===
def calcoli(isin, prezzo, cedola, tipo_cedola, scadenza_data, nazione):
    oggi = datetime.now()
    mesi_alla_scadenza = (scadenza_data.year - oggi.year) * 12 + scadenza_data.month - oggi.month
    n_cedole = mesi_alla_scadenza // 6 if tipo_cedola == "Semestrale" else mesi_alla_scadenza // 12
    totale_cedole = cedola * n_cedole
    rendimento_totale = ((totale_cedole + 100 - prezzo) / prezzo) * 100
    anni_alla_scadenza = mesi_alla_scadenza / 12
    rendimento_annuo = rendimento_totale / anni_alla_scadenza if anni_alla_scadenza > 0 else 0

    # Cedola annua su prezzo % (sempre calcolata come annua)
    cedola_annua = cedola * 2 if tipo_cedola == "Semestrale" else cedola
    cedola_annua_su_prezzo = (cedola_annua / prezzo) * 100

    tempo_alla_scadenza_legibile = mesi_in_anni_mesi(mesi_alla_scadenza)

    return [
        isin,
        round(prezzo, 2),
        round(cedola, 2),
        tipo_cedola,
        round(cedola_annua_su_prezzo, 2),
        scadenza_data.strftime("%d/%m/%Y"),
        tempo_alla_scadenza_legibile,
        mesi_alla_scadenza,  # <-- Colonna che vuoi rendere invisibile nel frontend
        round(rendimento_totale, 2),
        round(rendimento_annuo, 2),
        nazione
    ]

# === ESTRAZIONE E CALCOLO ===
dati_finali = [["ISIN", "Prezzo", "Cedola", "Tipo Cedola", "Cedola Annua % su Prezzo", "Data di Scadenza", "Tempo alla Scadenza", "Mesi alla Scadenza", "Rendimento Totale Lordo %", "Rendimento lordo Annuo %", "Nazione"]]

for isin in ISIN_LIST:
    print(f"🔎 Elaborazione {isin}...")
    prezzo, cedola, tipo_cedola, scadenza, nazione = estrai_dati(isin)
    if prezzo is not None:
        dati_finali.append(calcoli(isin, prezzo, cedola, tipo_cedola, scadenza, nazione))

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
