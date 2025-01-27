import os
import re
import time
import glob
import tempfile
import shutil
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from tabula import read_pdf

from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

def setup_driver():
    """
    Configuramos Firefox en modo headless.
    """
    options = Options()
    options.headless = True

    profile = webdriver.FirefoxProfile()
    profile.set_preference("general.useragent.override", "MiAgent")

    options.profile = profile
    service = Service()  # Asume geckodriver en PATH
    driver = webdriver.Firefox(service=service, options=options)
    return driver

def extraer_tabla_c(pdf_file):
    """ Usa tabula para leer TODAS las tablas del PDF.
        Devuelve el DataFrame que contenga 
        “states” y “energy met” en sus columnas.
    """
    pdf_file = os.path.abspath(pdf_file)  # Convierte a ruta absoluta
    #print(f"pdf a transformar: {pdf_file}")
    dfs = read_pdf(pdf_file, pages="all", multiple_tables=True, lattice=True)
    if not dfs:
        return pd.DataFrame()

    for df in dfs:
        # Pasamos a minúsculas
        df.columns = [c.strip().lower() for c in df.columns]
        df.columns = [
            re.sub(r"\s+", " ", col).strip()  # Sustituye secuencias de whitespace (\n, \r, \t...) por espacio
            for col in df.columns
        ]
        
        col_names = df.columns.to_list()
        #df["energy shortage (mu)"] = df["energy shortage (mu)"].fillna(0)
        if "states" in col_names and "energy met" in " ".join(col_names):
            if "region" in df.columns:
                df["region"] = df["region"].replace("", float("nan"))
                df["region"] = df["region"].ffill()
                df["energy shortage (mu)"] = df["energy shortage (mu)"].fillna("0")
            return df
    return pd.DataFrame()

def limpiar_dataframe(df, year=None, month=None, day=None):
    """Renombra columnas."""
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df

def parse_year_range(folder_name):
    """Ej: '2013-2014' => (2013, 2014). None si no matchea."""
    match = re.match(r"(\d{4})-(\d{4})", folder_name)
    if match:
        start_year = int(match.group(1))
        end_year = int(match.group(2))
        return start_year, end_year
    return None, None

def parse_month_year(folder_name):
    """Ej: 'January 2014' => (1, 2014). None si no matchea."""
    match = re.match(r"([A-Za-z]+)\s+(\d{4})", folder_name)
    if match:
        month_str = match.group(1).lower()
        year_val = int(match.group(2))
        months_map = {
            "january": 1, "february": 2, "march": 3, "april": 4,
            "may": 5, "june": 6, "july": 7, "august": 8,
            "september": 9, "october": 10, "november": 11, "december": 12
        }
        month_num = months_map.get(month_str, 0)
        return month_num, year_val
    return None, None

def main():
    # Rango de años
    in_option = input(f"!Elegir cantidad de años a extraer 1: |2022-2024|  2: |2014-2024|  3: |2023-2024| :")
    if in_option == "3":
        target_years = range(2023, 2024)
    elif in_option == "2":
        target_years = range(2014, 2024)
    elif in_option == "1":
        target_years = range(2022, 2024)
    else:
        main()

    #Creamos carpeta temporal para almacenar los PDFs
    with tempfile.TemporaryDirectory() as download_dir:
        print(f"Carpeta temporal: {download_dir}")

        driver = setup_driver()

        # Lista donde acumularemos **todas** las URLs de PDF
        all_pdf_urls = []

        try:
            #Ir a la página principal
            base_url = "https://report.grid-india.in/index.php?p=Daily+Report%2FPSP+Report"  
            driver.get(base_url)
            
            # Esperar que aparezca la tabla de carpetas
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "table"))
            )
            
            year_range_elems = driver.find_elements(By.XPATH, "//a[contains(@href, '20') and not(@title)]")

            # Convertimos la lista de WebElements a una lista de (texto, href)
            year_range_data = []
            for elem in year_range_elems:
                text_ = elem.text.strip()
                href_ = elem.get_attribute("href")
                year_range_data.append((text_, href_))

            for (folder_name, folder_href) in year_range_data:
                start_year, end_year = parse_year_range(folder_name)
                if not start_year or not end_year:
                    continue
                # Si coincide con target_years
                if any(y in target_years for y in range(start_year, end_year+1)):
                    print(f"Ingresando a carpeta de rango: {folder_name}")
                    driver.get(folder_href)
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "table"))
                    )

                    # Recogemos subcarpetas de mes
                    month_elems = driver.find_elements(By.XPATH, "//div[@class='filename']/a[contains(@href, '20') and not(@title)]")
                    month_links_data = []
                    for mElem in month_elems:
                        mtext = mElem.text.strip()
                        mhref = mElem.get_attribute("href")
                        month_links_data.append((mtext, mhref))

                    print(f"  Meses encontrados: {len(month_links_data)}")

                    for (mfolder_name, mfolder_href) in month_links_data:
                        month_num, year_val = parse_month_year(mfolder_name)
                        if year_val in target_years:
                            print(f"    -> Ingresando a carpeta de mes: {mfolder_name}")
                            driver.get(mfolder_href)
                            time.sleep(2)

                            # Buscar PDF
                            pdf_elems = driver.find_elements(By.XPATH, "//div[@class='filename']/a[contains(@href, '.pdf')]")
                            # Recolectar las URLs para la descarga
                            for pelem in pdf_elems:
                                pdf_url = pelem.get_attribute("href")
                                pdf_href = pdf_url.replace("&view=", "&dl=")
                                #print(f"Pdf formateado: {pdf_href}")
                                all_pdf_urls.append(pdf_href)

                            # Regresar a la vista de subcarpetas
                            driver.back()
                            time.sleep(1)

                    # Regresar a la lista principal de rangos
                    driver.back()
                    time.sleep(1)



        finally:
            #Obtener cookies, cerrar Selenium
            cookies = driver.get_cookies()
            driver.quit()

        #Crear una sesión requests con esas cookies
        session = requests.Session()
        for c in cookies:
            session.cookies.set(c['name'], c['value'])

        print(f"Total de PDFs a descargar: {len(all_pdf_urls)}")

        # Descarga en paralelo con ThreadPoolExecutor
        def download_pdf(url):
            filename = os.path.basename(url)
            # Reemplazar cualquier carácter inválido en Windows
            filename = re.sub(r'[\\/*?:"<>|]', '_', filename)
            # Asegurarnos de que termine en .pdf
            if not filename.lower().endswith(".pdf"):
                filename += ".pdf"
            local_path = os.path.join(download_dir, filename)

            try:
                r = session.get(url, stream=True, timeout=30)
                r.raise_for_status()
                with open(local_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"Descargado: {local_path}")
            except Exception as e:
                print(f"Error al descargar {url}: {e}")

        #Descargar de manera concurrente los pdf. workers segun CPU
        max_workers = os.cpu_count() * 2
        #max_workers = 20
        print(f"Usando {max_workers} workers para descargas concurrentes")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            executor.map(download_pdf, all_pdf_urls)
        

        #Procesar PDFs con Tabula
        print("Procesando pdf!...")
        df_master = pd.DataFrame()
        for pdf_path in glob.glob(os.path.join(download_dir, "*.pdf")):
            #pdf_path = re.sub(r'[\\/*?:"<>|]', '_', pdf_path)
            raw_df = extraer_tabla_c(pdf_path)
            if not raw_df.empty:
                clean_df = limpiar_dataframe(raw_df)
                df_master = pd.concat([df_master, clean_df], ignore_index=True)
        
        output_csv = "c_power_supply_positions.csv"
        df_master.to_csv(output_csv, index=False)
        print(f"¡Proceso completado! CSV generado: {output_csv}")


        #Crear ZIP de todos los PDFs
        print("Procesando pdf a ZIP...")
        zip_name = "all_reports"
        zip_path = shutil.make_archive(base_name=zip_name,
                                    format="zip",
                                    root_dir=download_dir)
        print(f"Archivo ZIP creado: {zip_path}")
    print("Carpeta temporal eliminada.")

    #Autentificar google drive
    gauth = GoogleAuth()
    gauth.settings['debug'] = True
    drive = GoogleDrive(gauth)

    #Subir zip a google drive
    file_drive = drive.CreateFile({"title": "Reports_2022_to_2024.zip"})
    file_drive.SetContentFile(zip_path)
    file_drive.Upload(param={'uploadType': 'resumable'})  # Parametro necesario por el tamaño del zip mayor a 100mb

    print("Zip Subido a Drive!, proceso terminado.")


if __name__ == "__main__":
    main()