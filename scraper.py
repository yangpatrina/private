import re
import requests 
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, urlunparse, quote
import hashlib
from collections import Counter
from requests.exceptions import Timeout, RequestException
from stopwords import stop_words

visited_urls = set()
common_words = Counter()
longest_page_word_count = 0
longest_page_url = ''
subdomains = Counter()

def scraper(url, resp):
    if resp.status_code == 200 and not is_dead_url(resp.content):
        word_count, words = count_words(resp.content)
        global longest_page_word_count, longest_page_url
        if word_count > longest_page_word_count:
            longest_page_word_count = word_count
            longest_page_url = url
        common_words.update(words)
        track_subdomain(url)

        links = extract_next_links(url, resp)
        return [link for link in links if is_valid(link)]
    return []
    
def normalize_url(url):
    parsed_url = urlparse(url)
    return parsed_url._replace(fragment='').geturl()
    
def is_valid(url):
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        
        domain_valid = re.search(
            r"^(.*\.)?(ics|cs|informatics|stat)\.uci\.edu$", parsed.netloc, re.IGNORECASE)
        if not domain_valid:
            return False

        blocked = re.compile(
            r".*\.(css|js|bmp|gif|jpe?g|svg|ico|png|tiff?|mid|mp2|mp3|mp4"
            r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            r"|epub|dll|cnf|tgz|sha1|thmx|mso|arff|rtf|jar"
            r"|csv|rm|smil|wmv|swf|wma|zip|rar|gz)$", re.IGNORECASE)
        if blocked.search(parsed.path.lower()):
            return False

        return True
    except TypeError:
        print("TypeError for URL:", url)
        return False

def detect_infinite_traps(url):
    # for detecting potential infinite traps based on patterns
    pattern = re.compile(r'\d+$')  # URLs ending in numbers
    match = pattern.search(url)
    max_length = 200
    if match:
        base_url = url[:match.start()]
        if base_url in visited_urls or len(url) > max_length:
            return True
    return False

def is_dead_url(content):
    if len(content) < 100 or not BeautifulSoup(content, 'lxml').find(True):
        return True
    return False

def count_words(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    text = soup.get_text()
    words = re.findall(r'\b\w+\b', text.lower())
    filtered_words = [word for word in words if word not in stop_words]
    return len(filtered_words), filtered_words

def track_subdomain(url):
    parsed_url = urlparse(url)
    if ".uci.edu" in parsed_url.netloc:
        subdomains[parsed_url.netloc] += 1

def scraper(url, resp):
    if resp.status_code == 200 and not is_dead_url(resp.content):
        global longest_page_word_count, longest_page_url
        word_count, words = count_words(resp.content)
        if word_count > longest_page_word_count:
            longest_page_word_count = word_count
            longest_page_url = url

        common_words.update([word for word in words if word not in stop_words])
        track_subdomain(url)

        links = extract_next_links(url, resp)
        return [link for link in links if is_valid(link) and not detect_infinite_traps(link)]
    return []

def extract_next_links(url, resp):
    soup = BeautifulSoup(resp.content, 'lxml')
    extracted_links = []
    for link in soup.find_all('a'):
        href = link.get('href')
        if href:
            absolute_link = urljoin(url, href)
            normalized_link = normalize_url(absolute_link)
            if normalized_link not in visited_urls:
                visited_urls.add(normalized_link)
                if is_valid(normalized_link):
                    extracted_links.append(normalized_link)
    return extracted_links
    
