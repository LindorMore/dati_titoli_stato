import csv
from datetime import datetime
from dateutil.relativedelta import relativedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from github import Github
import time
import os

# === CONFIG ===
ISIN_LIST = ["XS2571924070", "XS1837994794", "US900123BB58", "XS2201851685", "US77586TAE64",
    "XS2999564581", "US900123AT75", "XS2908633683", "XS2756521303", "XS2485249523",
    "XS1968706876", "XS2908645265", "XS3021378388", "US465410CC03", "XS2109813142",
    "US445545AF36", "XS2330514899", "XS2364200514", "XS2571923007", "XS2258400162",
    "US465410BZ07", "XS1892127470", "XS1768074319", "XS2434896010", "XS2829810923",
    "US900123AL40", "XS2770921315", "XS1313004928", "XS2999552909", "XS2201851172",
    "XS2434895806", "XS1970549561", "XS2756521212", "XS2689948078", "XS2330503694",
    "GB00BN65R313", "GB00B84Z9V04", "XS2890436087", "XS3021378032", "GB00B3KJDS62",
    "XS2571922884", "XS2109812508", "XS2434895988", "XS2908644615", "XS2829209720",
    "XS2971937672", "XS2485248806", "XS2027596530", "XS2770920937", "US900123CJ75",
    "US857524AE20", "US465410CA47", "XS2259191430", "US465410BG26", "XS2364199757",
    "GB00BTHH2R79", "XS2178857954", "XS2434393968", "GR0138012787", "IT0005611741",
    "IT0005534141", "IT0005217390", "US465410BY32", "US731011AU68", "XS2999533271",
    "XS1768067297", "XS2971936948", "GR0138014809", "XS2181689659", "GR0138013793",
    "IT0005480980", "GR0138011771", "IT0005398406", "IT0005441883", "XS2890435600",
    "IT0005363111", "FR0010870956", "XS2538441598", "IT0005273013", "GR0138018842",
    "XS1960361720", "ES00000128E2", "IT0005425233", "XS2680932907", "FR0013154028",
    "FR001400OHF4", "IT0005162828", "IT0005083057", "GR0138010765", "XS2586944147",
    "BE0000340498", "BE0000343526", "XS2262211076", "FR001400FTH3", "ES0000012H58",
    "FR0010171975", "IT0005631608", "XS2746103014", "IT0005530032", "ES0000012M93",
    "FR0014004J31", "IT0004923998", "BE0000361700", "IT0005438004", "BE0000358672",
    "FR0013404969", "GR0138017836", "FR0013480613", "US857524AD47", "BE0000355645",
    "FR0014001NN8", "XS2210006339", "GR0138007738", "BE0000353624", "ES0000012K46",
    "XS1619568139", "XS2234571771", "XS1508566558", "FR001400NEF3", "XS3063879442",
    "XS2922764191", "FR0013257524", "IT0005635583", "IT0005421703", "XS2013678086",
    "BE0000348574", "ES0000012G00", "PTOTE3OE0025", "BE0000338476", "IT0004532559",
    "GR0138009759", "ES0000012B47", "FR0011461037", "IT0005377152", "FR0014002JM6",
    "IT0005582421", "ES00000128C6", "GB00BYZW3G56", "FR001400CMX2", "GR0138005716",
    "IT0005442097", "XS2689949399", "ES0000012K95", "ES00000126D8", "BE0000331406",
    "GR0138006722", "NO0012440397", "IT0004286966", "XS1892141620", "PTOTECOE0037",
    "GR0138015814", "ES00000124H4", "NO0010757925", "NO0010930522", "XS2610236445",
    "BE0000359688", "GR0138008744", "XS2161992511", "IT0005321325", "ES0000012J07",
    "SI0002104121", "FR0013515806", "FR0010773192", "NO0010875230", "BE0000364738",
    "IT0005496770", "ES0000012O75", "ES00000121S7", "AT0000A0U299", "GB00B16NNR78",
    "ES0000012G42", "IT0005596470", "AT0000A1PEF7", "PTOTEBOE0020", "NO0010844079",
    "AT0000A1XML2", "FI4000566294", "BE0000320292", "BE0000350596", "GR0133010232",
    "AT0000A33SK7", "IT0005433195", "FR0013234333", "ES00000120N0", "FR0014009O62",
    "GR0128017747", "XS2716887844", "AT0000A2QQB6", "FR0010371401", "PTOTEPOE0032",
    "ES0000012L60", "IT0003934657", "AT0000A2Y8G4", "IT0005177909", "IE00080U68D3",
    "AT0000A2EJ08", "IT0005402117", "FI4000242870", "NO0010786288", "AT0000A1K9F1",
    "FI4000480488", "BE0000356650", "NO0010821598", "IT0005648149", "PTOTE4OE0008",
    "XS1346201889", "FI4000586284", "IT0005631590", "GR0133009226", "BE0000336454",
    "GR0133011248", "FI4000517677", "SI0002103677", "FR0013154044", "ES0000012I24",
    "AT0000A0VRQ6", "IE00BH3SQB22", "IT0005607970", "GR0133008210", "XS1420357318",
    "XS2975276143", "AT0000A2KQ43", "FI4000046545", "BE0000344532", "IT0005358806",
    "IE00BV8C9186", "FI4000440557", "XS3063879368", "PTOTEZOE0014", "ES0000012932",
    "IT0005584856", "IT0005508590", "IE000GVLBXU6", "XS2259191273", "IT0003535157",
    "IE00BMQ5JM72", "NL00150012X2", "AT0000A3D3Q8", "GR0124041758", "IT0005560948",
    "XS2746102479", "IT0005466351", "FR0010070060", "XS2536817484", "XS2434895558",
    "FR001400QMF9", "GR0128016731", "ES0000012P33", "IT0005544082", "NL0015614579",
    "FI4000546528", "XS2753429047", "PTOTE5OE0007", "NL0010721999", "ES0000012E69",
    "FR0013313582", "XS2579483319", "GR0124040743", "GR0133007204", "BE0000363722",
    "IT0005634800", "ES0000012O67", "DE000BU2D012", "IT0005240350", "NL0015001RG8",
    "IT000551"]
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

# === ESTRAZIONE DATI DA BORSA ITALIANA ===
def estrai_dati(isin):
    url = f"https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/{isin}.html"
    driver.get(url)
    time.sleep(7)

    try:
        # XPaths aggiornati
        prezzo_live_xpath = '//*[@id="fullcontainer"]/main/section/div[4]/div[1]/article/div/div/div[2]/div/span[1]/strong'
        prezzo_chiusura_xpath = '//*[@id="fullcontainer"]/main/section/div[4]/div[5]/article/div/div[2]/div[1]/table/tbody/tr[1]/td[2]/span'
        cedola_xpath = '//*[@id="fullcontainer"]/main/section/div[4]/div[8]/div/article/div/div[2]/div[2]/table/tbody/tr[9]/td[2]/span'
        scadenza_xpath = '//*[@id="fullcontainer"]/main/section/div[4]/div[8]/div/article/div/div[2]/div[2]/table/tbody/tr[5]/td[2]/span'
        nazione_xpath = '//*[@id="fullcontainer"]/main/section/div[4]/div[8]/div/article/div/div[2]/div[1]/table/tbody/tr[2]/td[2]/span'

        # Prezzo: live o chiusura
        try:
            prezzo = float(driver.find_element(By.XPATH, prezzo_live_xpath).text.replace(",", "."))
        except:
            prezzo = float(driver.find_element(By.XPATH, prezzo_chiusura_xpath).text.replace(",", "."))

        # Cedola semestrale
        cedola_str = driver.find_element(By.XPATH, cedola_xpath).text.strip().replace(",", ".").replace("%", "")
        cedola_semestrale = float(cedola_str)

        # Scadenza
        scadenza_text = driver.find_element(By.XPATH, scadenza_xpath).text.strip()
        if len(scadenza_text.split("/")[-1]) == 2:
            scadenza_data = datetime.strptime(scadenza_text, "%d/%m/%y")
        else:
            scadenza_data = datetime.strptime(scadenza_text, "%d/%m/%Y")

        # Nazione
        nazione = driver.find_element(By.XPATH, nazione_xpath).text.strip()

        return prezzo, cedola_semestrale, scadenza_data, nazione

    except Exception as e:
        print(f"❌ Errore per ISIN {isin}: {e}")
        return None, None, None, None

# === CALCOLI ===
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
    prezzo, cedola_semestrale, scadenza, nazione = estrai_dati(isin)
    if prezzo is not None:
        dati_finali.append(calcoli(isin, prezzo, cedola_semestrale, scadenza, nazione))

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

