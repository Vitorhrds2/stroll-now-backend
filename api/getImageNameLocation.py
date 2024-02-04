import requests
import json
import re
import urllib.parse
from html import unescape
from pprint import pprint
from flask import Flask, jsonify, request
from flask_cors import CORS
import getInstaOnWebsite
from concurrent.futures import ThreadPoolExecutor
from scrapping import baixar_posts, pegarBio

app = Flask(__name__)
CORS(app, origins="*")

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

def encontrar_textos_entre_lista(lista, texto_inicio, texto_fim):
    textos_entre = []
    for item in lista:
        if isinstance(item, str):
            posicao_inicio = 0
            while True:
                posicao_inicio = item.find(texto_inicio, posicao_inicio)
                if posicao_inicio == -1:
                    break
                posicao_fim = item.find(texto_fim, posicao_inicio + len(texto_inicio))
                if posicao_fim == -1:
                    break
                texto_entre = item[posicao_inicio + len(texto_inicio):posicao_fim]
                textos_entre.append(texto_entre)
                posicao_inicio = posicao_fim + len(texto_fim)
    return textos_entre

def modificar_largura_altura_url(url, nova_largura=1178, nova_altura=1138):
    return re.sub(r'&[wh]=\d+', f'&w={nova_largura}&h={nova_altura}', url)

def processar_url(url, nomes_vistos):
    url = url.replace("\"", "")
    url = re.sub(r'w203.*?,', 's1031,', url)

    url, name = url.split(",", 1)
    if url and name and name not in nomes_vistos and "fotos" not in name:
        nomes_vistos.add(name)

        if "pitch=0&thumbfov=100" in url:
            url = modificar_largura_altura_url(url, nova_largura=1178, nova_altura=1138)
            link_imagem = f"https://streetviewpixels-pa.googleapis.com/v1/thumbnail?panoid={url}"
        else:
            link_imagem = f"https://lh5.googleusercontent.com/p/AF1Qip{url}"

        return {"nome": name, "imagem": link_imagem}
    return None

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
            item['party_banner'] = baixar_posts(perfil)  # Cria uma lista com o URL do banner de festa
            item['bio_casa_noturna'] = pegarBio(perfil)
            pprint("Perfil no Instagram buscado diretamente: " + perfil)
        elif website and 'instagram' not in website:
            website = urllib.parse.unquote(website)
            instagram_extracted = getInstaOnWebsite.search_instagram_on_website(website)
            if instagram_extracted:
                profile = instagram_extracted.split('.com/')[-1].split('/')[0].split('%')[0].split('?')[0]
                item['party_banner'] = baixar_posts(profile)  # Cria uma lista com o URL do banner de festa
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
            locais_info = []

            for item in data:
                if isinstance(item, list):
                    textos_entre = encontrar_textos_entre_lista(item, "/p/AF1Qip", "\",[")
                    textos_entre_street = encontrar_textos_entre_lista(item, "/v1/thumbnail?panoid=", "\",null")

                    if textos_entre or textos_entre_street:
                        for url in textos_entre + textos_entre_street:
                            info = processar_url(url, nomes_vistos)
                            if info:
                                locais_info.append(info)

            websites_info = encontrar_urls_no_json(data)
            locais_websites_combinados = juntar_listas_por_nome(locais_info, websites_info)
            pprint(locais_websites_combinados)
            print("-" * 100)

            if locais_websites_combinados:
                # Utilizando ThreadPoolExecutor para obter party_banner concorrentemente
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
