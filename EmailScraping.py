#! python3
import concurrent
import re, urllib.request, time
from urllib.parse import urlparse, urljoin

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
def extractEmailsFromUrlText(urlText) -> set[str]:
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
    return seen

#HtmlPage Read Func
def htmlPageRead(url, i) -> set[str]:
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
        return extractEmailsFromUrlText(urlText)
    except:
        pass
    
#EmailsLeechFunction
def emailsLeechFunc(url, i) -> set[str]:
    try:
        return htmlPageRead(url,i)
    except urllib.error.HTTPError as err:
        if err.code == 404:
            try:
                logger.info(f"Fetching Cached Page {url}")
                url = 'http://webcache.googleusercontent.com/search?q=cache:'+url
                return htmlPageRead(url, i)
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

def fetch_internal_links(url) -> set[str]:
    try:
        logger.info(f"Fetching Internal Links from {url}")
        headers = { 'User-Agent' : 'Mozilla/5.0' }
        request = urllib.request.Request(url, None, headers)
        logger.info(f"Requesting {url}")
        response = urllib.request.urlopen(request)
        logger.info(f"Response from {url}")
        soup = BeautifulSoup(response, 'html.parser')
        internal_links = set()

        excluded_domains = ['tiktok', 'twitter', 'facebook', 'instagram', 'linkedin', 'youtube', 'reddit', 'google', 'yandex']

        for link in soup.find_all('a'):
            href = link.get('href')
            if href:
                href = urljoin(url, href)  # Join the URL with the href
                href_domain = urlparse(href).netloc  # Get domain of the href
                # Only add href to internal_links if its domain matches the URL's domain,
                # and it does not belong to the excluded domains
                if not any(excluded in href_domain for excluded in excluded_domains):
                    internal_links.add(href)
        logger.info(f"Found {len(internal_links)} internal links.")
        return internal_links
    except Exception as e:
        logger.error(e)
        return set()

emails = set()
all_urls = set()
def run_program(urlfile, emailfile):
    urls = set()
    for urlLink in urlfile.readlines():
        urlLink = urlLink.strip('\'"')
        urlLink = add_http_if_missing(urlLink)
        fetched = fetch_internal_links(urlLink)
        for url in fetched:
            urls.add(url)
    logger.info(f"urls: {urls}")

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(fetch_internal_links, url): url for i, url in enumerate(urls)}

        def callback(future):
            try:
                temp = future.result(timeout=5)
                for url in temp:
                    all_urls.add(url)
            except concurrent.futures.TimeoutError:
                logger.warning(f'Timeout: {temp} took too long to complete.')
            except Exception as exc:
                logger.error(f'{temp} generated an exception: {exc}')
            if all(f.done() for f in futures):
                logger.info("All futures are done for internal links.")
                fetch_emails_with_depth(all_urls, emailfile)

        for future in futures:
            future.add_done_callback(callback)

current_index = 1
def fetch_emails_with_depth(urls, emailfile):
    try:
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = {executor.submit(emailsLeechFunc, url, i): url for i, url in enumerate(urls)}

            def callback(future):
                global current_index
                url = futures[future]
                try:
                    # Add a timeout of 5 seconds
                    fetched = future.result(timeout=5)  # get the result of the function
                    for email in fetched:
                        current_index = current_index + 1
                        emails.add(email)
                        logger.info(f"Total emails found: {len(emails)}")
                except concurrent.futures.TimeoutError:
                    logger.warning(f'Timeout: {url} took too long to complete.')
                except Exception as exc:
                    logger.error(f'{url} generated an exception: {exc}')
                if all(f.done() for f in futures):
                    logger.info("All futures are done.")
                    # Write all to emails.txt
                    for email in emails:
                        emailfile.write(f"{email}\n")

            for future in futures:
                future.add_done_callback(callback)
    except Exception as e:
        logger.error(e)

if __name__ == "__main__":
    start = time.time()
    urlFile = open("urls.txt", 'r')
    emailFile = open("emails.txt", 'a')
    try:
        run_program(urlFile, emailFile)
    except Exception as e:
        logger.error(e)
    finally:
        urlFile.close()
        emailFile.close()
        print("Elapsed Time: %s" % (time.time() - start))

