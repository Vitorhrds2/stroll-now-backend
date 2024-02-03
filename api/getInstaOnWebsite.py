import requests
from bs4 import BeautifulSoup

def search_instagram_on_website(url):
    try:
        headers = {
            'authority': 'www.google.com',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'max-age=0',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        }
        response = requests.get(url, headers=headers)

        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        instagram_tag = soup.find('a', href=lambda href: href and 'instagram.com' in href)
        if instagram_tag:
            return instagram_tag['href']
    except Exception as e:
        print(e)
        return None