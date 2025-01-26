# Grid_India_Case_Mint_Data

Repositorio para Prueba técnica - MintData con PYTHON
Caso presentado por la empresa orientado hacia el webScrapping y automatizacion.

## Requisitos Previos
  Librerias necesarias para el funcionamiento de el script. (Se entrega un requirements.txt)
> pip install requirements.txt
### Librerias destacas
selenium
tabula-py
pandas
requests
PyDrive
jpype1
httplib2
pydrive2
  
--- 
  
## Configuración del Proyecto
### 1. Configuracion client_secrets.json
Es neceario agregar un archivo client_secrets.json, el cual funciona y usa el api de pydrive2, para asi poder lograr subir la informacion en Google Drive

El archivo debe ver algo asi mas o menos:
>{
>"installed": {
>"client_id": "TU_CLIENT_ID",
>"project_id": "TU_PROJECT_ID",
>"auth_uri": "https://accounts.google.com/o/oauth2/auth",
>"token_uri": "https://oauth2.googleapis.com/token",
>"auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
>"client_secret": "TU_CLIENT_SECRET",
>"redirect_uris": [
>"http://localhost"
>]
>}
>}

El cual se obtiene de la consola de API de GoogleCloud: https://console.cloud.google.com/apis/dashboard

Ademas se recomienda encarecidamente utilizar un entorno virtual como virtualenv: https://virtualenv.pypa.io/en/latest/user_guide.html

## 2. Propose and explain a format that better structures the requested data while minimizing loss of information.
Segun la informacion analizada lo mas correcto seria primero que nada estandarizar las columnas ya conocidad por el cliente:  
region  
states  
max.demand day  
shortage during maximum demand  
energy met  
drawal schedule  
od/ud 
max od  
energy shortage  
source_pdf_name (Agregaria un campo para poder rastrear el pdf que viene)  

Ademas se puede considerar normalizar desde este punto, buscando no repetir datos como lo son region y states, cuando hablamos de informes anuales o semestrales.  
Ejemplo en un modelo Entidad-Relacion:

![image](https://github.com/user-attachments/assets/a76558ed-3941-4990-b1b4-a5496446f2ce)



