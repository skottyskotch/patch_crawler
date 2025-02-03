import requests
import time
import getpass
from bs4 import BeautifulSoup
import os
import re
import sys
import argparse

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
    if form == None:
        return False, False
    action = form.get('action')
    saml_value = form.find('input', {'name': 'SAMLResponse'}).get('value')
    data = {
        'SAMLResponse': saml_value,
        'RelayState': target_url
    }
    response_target = session.post(action, data=data)
    time.sleep(0.3)

    return response_target, session

def processExclusion(filename, conf, size, size_limit, all):
	if os.path.isfile(os.path.join(conf,'exclusions.txt')):
		with open(os.path.join(conf,'exclusions.txt')) as file:
			for line in file:
				if filename in line:
					print(filename + ' ignored (mentionned in exclusions.txt), size: ' + str(size/1024/1024).split('.')[0] + ' Mb')
					if all:
						print('--all requested. Ignore list bypassed')
					return True
	sExclude = input('\nThe file ' + filename + ' exceeds ' + str(size_limit) + 'Mb (' + str(size) + '). Add it to exclusions? (y/n):')
	while not sExclude.lower() in ['yes', 'y', 'no', 'n', 'oui', 'o']:
		sExclude = input("Invalid answer. Please enter 'yes', 'y', 'no' or 'n'")
	if sExclude.lower() in ['yes', 'y', 'oui', 'o']:
		with open(os.path.join(conf,'exclusions.txt'), 'a') as file:
			file.write(filename+'\n')
		return True
	else:
		return False

def main(argv=sys.argv[1:]):
	size_limit = 2
	sys.argv = sys.argv[1:]
	parser = argparse.ArgumentParser(
		prog = 'Patch gatherer',
		description = 'Fetch the current patches from intranet, keeping history of versions')
	parser.add_argument('conf', nargs='?', default=default_conf, help='710SP1 (default), 700SP0, 630SP3, 620SP2, 610SP1, 600SP0,520SP2')
	parser.add_argument('-a', '--all',  action='store_true', default=False, help='Bypass ignore list to download all patches')
	args = parser.parse_args(argv)
	conf = args.conf
	target_url = 'https://kiwi.planisware.com/Intranet/versions/' + conf + '/patches/_en_dev/'
	print('Download from ' + target_url)
	response, session = fetchTargetPageWithSamlNego(target_url)
	if response == False:
		print('Login failed. exit')
		return False
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
				if size < size_limit * 1024 * 1024 or not processExclusion(link.text, conf, size, size_limit, args.all):
					text = session.get(url).text
					lines = text.splitlines()
					firstline = lines[0]
					documentation = ''
					for eachLine in lines[:5]:
						if eachLine.startswith('DOCUMENTATION:'):
							documentation = eachLine
					match = re.search(r'v (\d+\.\d+)',firstline)
					if match:
						version = match.group(1)
						if not os.path.isfile(os.path.join(conf,link.text,link.text+'_'+version)):
							with open (os.path.join(conf,link.text,link.text+'_'+version), 'w') as file:
								for line in lines:
									file.write(line+'\n')
							print('\n' + 'new version: ' + link.text + ' ' + version + ' ' + documentation)
	
	patchlist = []
	for path, directories, files in os.walk(conf):
		for file in files:
			if '.obin' in file:
				with open(os.path.join(path,file),'r') as fread:
					lines = fread.readlines()
					documentation = ''
					for eachLine in lines[:5]:
						if eachLine.startswith('DOCUMENTATION:'):
							documentation = eachLine
					patchlist.append(file+'\t'+documentation)
	patchlist.sort()
	with open(os.path.join(conf,'patch_list_'+conf+'.txt'),'w') as fout:
		fout.write(''.join(patchlist))
	sOpen = input('Do you want to open the patch listing? ')
	if sOpen.lower() in ['yes', 'y', 'oui', 'o']:
		os.startfile(os.path.join(conf,'patch_list_'+conf+'.txt'))


default_conf = '710SP1'
if __name__ == '__main__':
    main()
