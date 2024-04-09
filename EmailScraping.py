#! python3
import concurrent
import re, urllib.request, time
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from loguru import logger
from concurrent.futures import ThreadPoolExecutor

emailRegex = re.compile(r'''
#example :
#something-.+_@somedomain.com
(
([a-zA-Z0-9_.+]+
@
[a-zA-Z0-9_.+]+)
)
''', re.VERBOSE)
        
#Extacting Emails
def extractEmailsFromUrlText(urlText):
    extractedEmail =  emailRegex.findall(urlText)
    allemails = []
    for email in extractedEmail:
        allemails.append(email[0])
    lenh = len(allemails)
    print("\tNumber of Emails : %s\n"%lenh )
    seen = set()
    for email in allemails:
        if email not in seen:  # faster than `word not in output`
            seen.add(email)
            emailFile.write(email+"\n")#appending Emails to a filerea

#HtmlPage Read Func
def htmlPageRead(url, i):
    try:
        logger.info(f"Reading HTML Page {url}")
        start = time.time()
        headers = { 'User-Agent' : 'Mozilla/5.0' }
        request = urllib.request.Request(url, None, headers)
        logger.info(f"Requesting {url}")
        response = urllib.request.urlopen(request)
        logger.info(f"Response from {url}")
        urlHtmlPageRead = response.read()
        urlText = urlHtmlPageRead.decode()
        print ("%s.%s\tFetched in : %s" % (i, url, (time.time() - start)))
        extractEmailsFromUrlText(urlText)
    except:
        pass
    
#EmailsLeechFunction
def emailsLeechFunc(url, i):
    try:
        htmlPageRead(url,i)
    except urllib.error.HTTPError as err:
        if err.code == 404:
            try:
                logger.info(f"Fetching Cached Page {url}")
                url = 'http://webcache.googleusercontent.com/search?q=cache:'+url
                htmlPageRead(url, i)
            except:
                logger.info(f"Error in fetching Cached Page {url}")
                pass
        else:
            logger.info(f"Error in fetching {url}")
            pass    
      
def add_http_if_missing(url):
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'http://' + url
        return url

def fetch_internal_links(url) -> list:
    logger.info(f"Fetching Internal Links from {url}")
    headers = { 'User-Agent' : 'Mozilla/5.0' }
    request = urllib.request.Request(url, None, headers)
    logger.info(f"Requesting {url}")
    try:
        response = urllib.request.urlopen(request)
    except Exception as e:
        logger.error(e)
        return []

    logger.info(f"Response from {url}")
    soup = BeautifulSoup(response, 'html.parser')
    internal_links = []
    url_domain = urlparse(url).netloc  # Get domain of the URL

    excluded_domains = ['twitter', 'facebook', 'instagram', 'linkedin', 'youtube', 'reddit', 'google', 'yandex']

    for link in soup.find_all('a'):
        href = link.get('href')
        if href:
            href_domain = urlparse(href).netloc  # Get domain of the href
            # Only add href to internal_links if its domain matches the URL's domain
            # and it does not belong to the excluded domains
            if not any(excluded in href_domain for excluded in excluded_domains):
                internal_links.append(href)
    logger.info(f"Found {len(internal_links)} internal links.")
    return internal_links

def run_emailsLeechFunc_concurrently(urls):
    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = {executor.submit(emailsLeechFunc, url, i): url for i, url in enumerate(urls)}
        for future in concurrent.futures.as_completed(futures):
            url = futures[future]
            try:
                future.result()  # get the result of the function
            except Exception as exc:
                print(f'{url} generated an exception: {exc}')

links = fetch_internal_links('http://prota.com.tr')
for link in links:
    logger.info(link)


start = time.time()
urlFile = open("urls.txt", 'r')
emailFile = open("emails.txt", 'a')
i=0
#Iterate Opened file for getting single url
for urlLink in urlFile.readlines():
    urlLink = urlLink.strip('\'"')
    urlLink = add_http_if_missing(urlLink)
    urls = fetch_internal_links(urlLink)
    run_emailsLeechFunc_concurrently(urls)

print ("Elapsed Time: %s" % (time.time() - start))

urlFile.close()
emailFile.close()




