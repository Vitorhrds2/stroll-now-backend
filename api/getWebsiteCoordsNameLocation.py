import re

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