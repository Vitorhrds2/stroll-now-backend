import requests
import json
import urllib.parse
from html import unescape
from pprint import pprint
from flask import Flask, jsonify, request
from flask_cors import CORS
from concurrent.futures import ThreadPoolExecutor
import instaloader
from bs4 import BeautifulSoup
import re

app = Flask(__name__)
CORS(app, origins="*")

def modificar_largura_altura_url(url, nova_largura=1178, nova_altura=1138):
    return re.sub(r'&[wh]=\d+', f'&w={nova_largura}&h={nova_altura}', url)


def extrair_latitude_longitude_nome_da_url_imagem(url, nomes_vistos):
    pattern = r'/p/AF1Qip(.*?)=w.*?\",\"(.*?)\",.*?,(-?\d+\.\d+),(-?\d+\.\d+)'
    pattern_street = r'/v1/thumbnail\?panoid=(.*?)&pitch=0&thumbfov=100.*?\",\"(.*?)\",.*?,(-?\d+\.\d+),(-?\d+\.\d+)'
    matches = re.findall(pattern, url)
    matches_street = re.findall(pattern_street, url)

    informacoes = []

    for match in matches:
        url_id, name, longitude, latitude = match

        if url_id and name and name not in nomes_vistos and "fotos" not in name:
            nomes_vistos.add(name)
            link_imagem = f"https://lh5.googleusercontent.com/p/AF1Qip{url_id}=s1031"
            informacoes.append({"nome": name, "imagem": link_imagem, "latitude": latitude, "longitude": longitude})
    
    for match_street in matches_street:
        url_id, name, longitude, latitude = match_street

        if url_id and name and name not in nomes_vistos and "fotos" not in name:
            nomes_vistos.add(name)
            url_id = modificar_largura_altura_url(url_id, nova_largura=1178, nova_altura=1138)
            link_imagem = f"https://streetviewpixels-pa.googleapis.com/v1/thumbnail?panoid={url_id}"
            informacoes.append({"nome": name, "imagem": link_imagem, "latitude": latitude, "longitude": longitude})

    return informacoes

def encontrar_urls_no_json_image(data):
    urls_encontradas = []

    def buscar_recursivamente(item):
        if isinstance(item, list):
            for subitem in item:
                buscar_recursivamente(subitem)

        elif isinstance(item, str) and '/p/AF1Qip' in item:
            nomes_vistos = set()
            info = extrair_latitude_longitude_nome_da_url_imagem(item, nomes_vistos)
            if info:
                for info in info:
                    urls_encontradas.append(info)
        
        elif isinstance(item, str) and 'streetviewpixels-pa.googleapis.com' in item:
            info = extrair_latitude_longitude_nome_da_url_imagem(item)
            if info:
                for info in info:
                    urls_encontradas.append(info)

    buscar_recursivamente(data)

    return urls_encontradas

def extrair_latitude_longitude_nome(url):
    pattern = r'url\?q=(.*?)&opi=.*?,null,\[null,null,(-?\d+\.\d+),(-?\d+\.\d+)\],"[^"]+","(.*?)"'
    matches = re.findall(pattern, url)

    informacoes = []
    for match in matches:
        website, latitude, longitude, nome = match
        informacoes.append({"website": website, "latitude": latitude, "longitude": longitude, "nome": nome})

    return informacoes


def encontrar_urls_no_json(data):
    urls_encontradas = []

    def buscar_recursivamente(item):
        if isinstance(item, list):
            for subitem in item:
                buscar_recursivamente(subitem)

        elif isinstance(item, str) and '/url?q=' in item:
            informacoes = extrair_latitude_longitude_nome(item)

            if informacoes:
                for info in informacoes:
                    urls_encontradas.append(info)

    buscar_recursivamente(data)

    return urls_encontradas

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

def baixar_posts(profile):
    bot = instaloader.Instaloader()
    profile = instaloader.Profile.from_username(bot.context, profile)
    posts = profile.get_posts()
    numero_de_posts_desejado = 1
    posts_baixados = 0

    for index, post in enumerate(posts, 1):
        if posts_baixados >= numero_de_posts_desejado:
            break

        posts_baixados += 1
        return post.url

def pegarBio(profile):
    bot = instaloader.Instaloader()
    profile = instaloader.Profile.from_username(bot.context, profile)
    return profile.biography

def juntar_listas_por_nome(locais_info, websites_info):
    locais_dict = {item['nome']: item for item in locais_info}
    for website_info in websites_info:
        nome = website_info['nome']

        if nome in locais_dict:
            locais_dict[nome].update(website_info)

        else:
            locais_dict[nome] = website_info
            
    return list(locais_dict.values())


def obter_party_banner(item):
    website = item.get('website')
    try:
        if website and 'instagram' in website:
            website = urllib.parse.unquote(website)
            perfil = website.split('.com/')[-1].split('/')[0].split('%')[0].split('?')[0]
            item['party_banner'] = baixar_posts(perfil)  
            item['bio_casa_noturna'] = pegarBio(perfil)
            pprint("Perfil no Instagram buscado diretamente: " + perfil)

        elif website and 'instagram' not in website:
            website = urllib.parse.unquote(website)
            instagram_extracted = search_instagram_on_website(website)

            if instagram_extracted:
                profile = instagram_extracted.split('.com/')[-1].split('/')[0].split('%')[0].split('?')[0]
                item['party_banner'] = baixar_posts(profile)  
                item['bio_casa_noturna'] = pegarBio(profile)
                print("Perfil no Instagram buscado no website:", profile, "Website:", website)

            else:
                print("Nenhum link de Instagram encontrado no website:", website)

    except Exception as e:
        print("Erro ao buscar Instagram no website:", e)

@app.route('/get-location-image', methods=['POST'])
def get_location_image():
    nomes_vistos = set()
    data = request.get_json()
    latitude, longitude, zoom = data['latitude'], data['longitude'], data['zoom']
    url = f"https://www.google.com/maps/search/casa+noturna/@{latitude},{longitude},{zoom}z"
    response = requests.get(url)

    if response.status_code == 200:
        txt = response.text
        find1, find2 = "window.APP_INITIALIZATION_STATE=", ";window.APP"
        i1 = txt.find(find1)
        i2 = txt.find(find2, i1 + 1)
        js = unescape(txt[i1 + len(find1):i2].replace("\\\\u003d", "=").replace("\\\\u0026", "&"))

        try:
            data = json.loads(js)
            locais_info = encontrar_urls_no_json_image(data)

            websites_info = encontrar_urls_no_json(data)
            locais_websites_combinados = juntar_listas_por_nome(locais_info, websites_info)
            pprint(locais_websites_combinados)
            print("-" * 100)

            if locais_websites_combinados:
                
                with ThreadPoolExecutor(max_workers=len(locais_websites_combinados)) as executor:
                    executor.map(obter_party_banner, locais_websites_combinados)

                pprint(locais_websites_combinados)
                return jsonify(locais_websites_combinados)
            else:
                return jsonify({'message': 'Nenhum local encontrado'})

        except json.JSONDecodeError as e:
            print(f"Erro ao decodificar JSON: {e}")
    else:
        print(f"A requisição falhou. Código de status: {response.status_code}")

if __name__ == '__main__':
    app.run(debug=True, port=4000, host='0.0.0.0')