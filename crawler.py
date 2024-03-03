import requests
import time
import getpass
from bs4 import BeautifulSoup
import os
import re

def fetchTargetPageWithSamlNego(target_url):
    username = input('Username: ')
    password = getpass.getpass('Password: ')
    otp = input('OTP: ')
    #Session keeps cookies
    session = requests.Session()
    response_auth = session.get(target_url)
    time.sleep(0.4)

    # Saml
    soup = BeautifulSoup(response_auth.text, 'html.parser')
    form = soup.find('form')
    saml_payload = {}
    for input_field in form.find_all('input'):
        saml_payload[input_field.get('name')] = input_field.get('value')
    saml_payload['username'] = username
    saml_payload['password'] = password
    response_saml = session.post(form['action'], data=saml_payload)
    time.sleep(0.3)

    # OTP
    soup = BeautifulSoup(response_saml.text, 'html.parser')
    form = soup.find('form')
    otp_payload = {}
    for input_field in form.find_all('input'):
        otp_payload[input_field.get('name')] = input_field.get('value')
    otp_payload['otp'] = otp
    response_otp = session.post(form['action'], data=otp_payload)

    # Ressource
    soup = BeautifulSoup(response_otp.text, 'html.parser')
    form = soup.find('form', {'name': 'saml-post-binding'})
    action = form.get('action')
    saml_value = form.find('input', {'name': 'SAMLResponse'}).get('value')
    data = {
        'SAMLResponse': saml_value,
        'RelayState': target_url
    }
    response_target = session.post(action, data=data)
    time.sleep(0.3)

    return response_target, session

def processExclusion(filename):
    if os.path.isfile(os.path.join(conf,'exclusions.txt')):
        with open(os.path.join(conf,'exclusions.txt')) as file:
            for line in file:
                if filename == line:
                    return True
    sExclude = input('\nThe file ' + filename + ' exceeds ' + str(size_limit) + 'Mb. Add it to exclusions? (y/n):')
    while not sExclude.lower() in ['yes', 'y', 'no', 'n', 'oui', 'o']:
        sExclude = input("Invalid answer. Please enter 'yes', 'y', 'no' or 'n'")
    if sExclude.lower() in ['yes', 'y', 'oui', 'o']:
        with open(os.path.join(conf,'exclusions.txt'), 'a') as file:
            file.write(filename)
        return True
    else:
        return False

def __main__(conf, size_limit):
    target_url = 'https://kiwi.planisware.com/Intranet/versions/' + conf + '/patches/_en_dev/'
    print('Download from ' + target_url)
    response, session = fetchTargetPageWithSamlNego(target_url)
    if not os.path.isdir(conf):
        os.mkdir(conf)
    if response.status_code != 200:
        print('Unable to open ' + target_url + 'Status: ' + response.status_code)
    else:
        soup = BeautifulSoup(response.text, 'html.parser')
        links = [link for link in soup.find_all('a', href=True) if link['href'].endswith('.obin')]
        i=0
        for link in links:
            i+=1
            print(str(i)+'/'+str(len(links)) + '    ',end = '\r')
            if not os.path.isdir(os.path.join(conf,link.text)):
                os.makedirs(os.path.join(conf,link.text))
            if os.path.isdir(os.path.join(conf,link.text)):
                url = target_url + link['href']
                size = int(session.head(url).headers['Content-Length'])
                if size < size_limit * 1024 * 1024 or not processExclusion(link.text):
                    text = session.get(url).text
                    lines = text.splitlines()
                    firstline = lines[0]
                    match = re.search(r'v (\d+\.\d+)',firstline)
                    if match:
                        version = match.group(1)
                        if not os.path.isfile(os.path.join(conf,link.text,link.text+'_'+version)):
                            with open (os.path.join(conf,link.text,link.text+'_'+version), 'w') as file:
                                for line in lines:
                                    file.write(line+'\n')
size_limit = 2
conf = '710SP1'
__main__(conf, size_limit)

















