import openpyxl
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time
import csv
from github import Github
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# === CONFIG ===
EXCEL_FILE = "Fromule calcolatore rendimenti Bond copia.xlsx"
CSV_FILE = "prezzi_completi.csv"
import os
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

REPO_NAME = "LindorMore/dati_titoli_stato"
COMMIT_MESSAGE = f"Aggiornamento automatico {datetime.now().isoformat()}"

# === CARICA EXCEL ===
workbook = openpyxl.load_workbook(EXCEL_FILE)
foglio = workbook.active

# === Estrai ISIN dalla riga 2 ===
isin_list = []
colonna = 2
while True:
    cella = foglio.cell(row=2, column=colonna)
    if cella.value is None:
        break
    isin_list.append((colonna, str(cella.value).strip()))
    colonna += 1

# === Configura Selenium ===
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
service = Service()
driver = webdriver.Chrome(service=service, options=options)

# === CSV HEADER ===
righe_csv = [["ISIN", "Prezzo", "Cedola Semestrale %", "Cedola Annua €", "Cedola Annua % su Prezzo", "Scadenza", "Mesi Residui", "Cedole Residue", "Totale Cedole Residue €", "Rendimento Totale %", "Rendimento Annuo %"]]

# === Estrai e Calcola ===
for col, isin in isin_list:
    try:
        url = f"https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/{isin}.html"
        driver.get(url)
        time.sleep(6)

        # Prezzo
        prezzo = float(driver.find_element(By.XPATH, '//*[@id="fullcontainer"]/main/section/div[4]/div[5]/article/div/div[2]/div[1]/table/tbody/tr[1]/td[2]/span').text.replace(',', '.'))

        # Cedola Semestrale %
        cedola_semestrale_pct = float(driver.find_element(By.XPATH, '//*[@id="fullcontainer"]/main/section/div[4]/div[8]/div/article/div/div[2]/div[2]/table/tbody/tr[9]/td[2]/span').text.replace(',', '.'))

        # Scadenza
        scadenza_txt = driver.find_element(By.XPATH, '//*[@id="fullcontainer"]/main/section/div[4]/div[8]/div/article/div/div[2]/div[2]/table/tbody/tr[5]/td[2]/span').text.strip()
        scadenza = datetime.strptime(scadenza_txt, "%d/%m/%Y").date()

        # Calcoli
        oggi = date.today()
        mesi_residui = (scadenza.year - oggi.year) * 12 + (scadenza.month - oggi.month)
        if scadenza.day < oggi.day:
            mesi_residui -= 1

        cedole_residue = mesi_residui // 6
        cedola_annua_euro = (cedola_semestrale_pct * 2)
        cedola_totale_residua = cedola_semestrale_pct * cedole_residue
        rendimento_totale = ((cedola_totale_residua + 100 - prezzo) / prezzo) * 100
        rendimento_annuo = rendimento_totale / (mesi_residui / 12) if mesi_residui > 0 else 0
        cedola_pct_sul_prezzo = (cedola_annua_euro / prezzo) * 100

        righe_csv.append([
            isin,
            round(prezzo, 3),
            round(cedola_semestrale_pct, 3),
            round(cedola_annua_euro, 3),
            round(cedola_pct_sul_prezzo, 3),
            scadenza.strftime("%Y-%m-%d"),
            mesi_residui,
            cedole_residue,
            round(cedola_totale_residua, 3),
            round(rendimento_totale, 3),
            round(rendimento_annuo, 3)
        ])

        print(f"✅ {isin}: Prezzo {prezzo}, Cedola {cedola_semestrale_pct}%")

    except Exception as e:
        print(f"❌ Errore per {isin}: {e}")

driver.quit()

# === Salva CSV ===
with open(CSV_FILE, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(righe_csv)

# === Carica su GitHub ===
g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)
with open(CSV_FILE, "r") as f:
    content = f.read()
    try:
        file_github = repo.get_contents(CSV_FILE)
        repo.update_file(CSV_FILE, COMMIT_MESSAGE, content, file_github.sha)
        print("🔁 File aggiornato su GitHub.")
    except:
        repo.create_file(CSV_FILE, COMMIT_MESSAGE, content)
        print("🆕 File caricato su GitHub.")
