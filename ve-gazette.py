import os
import re
import ftplib
import requests
import bs4
import PyPDF2
from dotenv import load_dotenv


# Load environment variables from .env file (must be in ~)
load_dotenv(f'{os.environ["HOME"]}/.env')

start_url = 'http://spgoin.imprentanacional.gob.ve/cgi-win/be_alex.cgi?forma=FGENERAL&nombrebd=spgoin&c01=Titulo&m01=frase&t01=&c03=Descriptor_TGO1&m03=comienzo&c04=FechaInicio&m04=%3E%3D&t04=01-01-2021&c05=FechaInicio&t05=&c06=Descriptor_EDR1&m06=frase&t06=Publicado&TSalida=T%3AGeneralGCTOF&recuperar=3000&MostrarHijos=E&Cizq=2&xsl=&pxsl=&TipoDoc=GCTOF&Submit2=Buscar&Orden=;FID;'
download_directory = os.environ['HOME']

# Create list of files in FTP folder "procesados"
ftp_connection = ftplib.FTP(
    host=os.environ['AG2_HOST'],
    user=os.environ['AG2_USER'],
    passwd=os.environ['AG2_PASS'],

)
print(ftp_connection.getwelcome())
ftp_files = ftp_connection.nlst('/DO_Venezuela/procesados/')
ftp_connection.quit()

# Main page GET request, parse response
session = requests.Session()
response = session.get(start_url)
soup_object = bs4.BeautifulSoup(response.content, 'html.parser')

# Main response is an HTML table
tr_class_regex = re.compile(r'LineaTabla.*')
trs = soup_object.find_all('tr', class_=tr_class_regex)

# Compile regex outside loop
pre_pdf_link_regex = re.compile(r'.*Kb\).*?')

# Main loop
for tr in trs:

    # Issue metadata is inside <td> tags
    tds = tr.find_all('td')
    issue_number = tds[0].text.strip().replace('.', '')
    issue_edition = tds[1].text.strip()
    issue_day, issue_month, issue_year = tds[2].text.strip().split('-')
    issue_link = tds[0].a['href']
    file_name = f'{issue_number}_{issue_day}{issue_month}{issue_year}'

    # Check if file is already in FTP folder "procesados"
    if f'{file_name}.pdf' in ftp_files and f'{file_name}.csv' in ftp_files:
        try:
            os.remove(f'{os.environ["HOME"]}/{file_name}.csv')
            os.remove(f'{os.environ["HOME"]}/{file_name}.pdf')
            print(f'{file_name} already in FTP. Skipped.')
        except:
            print(f'{file_name} already in FTP. Skipped.')

    # New issue not in vLex
    elif f'{file_name}.pdf' not in ftp_files and not os.path.isfile(f'{os.environ["HOME"]}/{file_name}.pdf'):
        try:
            # Second GET request returns issue main page
            response2 = session.get(f'http://spgoin.imprentanacional.gob.ve{issue_link}')
            soup_object2 = bs4.BeautifulSoup(response2.content, 'html.parser')

            # Construct PDF viewer url and make GET request to PDF viewer url
            pre_pdf_link = soup_object2.find('a', text=pre_pdf_link_regex)

            # remove <this query parameters>
            # /cgi-win/be_alex.cgi?Documento=T028700038600/0&Nombrebd=spgoin&CodAsocDoc=2889 <&t04=1&t05=png&CIzq=2&TipoDoc=GCTOF>
            pdf_viewer_url = re.sub(r'(CodAsocDoc=\d+)&.*', r'\1', pre_pdf_link["href"])

            # GET request that returns bytes response
            pdf_viewer = session.get(f'http://spgoin.imprentanacional.gob.ve{pdf_viewer_url}')

            # Write bytes response to PDF file
            with open(f'{download_directory}/{file_name}.pdf', 'wb') as pdf_file:
                pdf_file.write(pdf_viewer.content)
            print(f'{file_name}: downloaded PDF file')

            # Count PDF pages
            read_pdf = PyPDF2.PdfFileReader(f'{download_directory}/{file_name}.pdf')
            total_pages = read_pdf.numPages

            # Create CSV file
            with open(f'{download_directory}/{file_name}.csv', 'w') as csv_file:
                csv_file.write(f'Gaceta Oficial de la República Bolivariana de Venezuela Nº {issue_number} del {issue_day}/{issue_month}/{issue_year}. Versión {issue_edition} (contenido completo)||{issue_edition}|{issue_day}/{issue_month}/{issue_year}|1|{total_pages}')

        # Error
        except:
            print(f'{file_name}: an error occurred. Please visit http://spgoin.imprentanacional.gob.ve/{pdf_viewer_url}')

# Close requests session
session.close()
