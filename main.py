from fastapi import FastAPI, HTTPException
from typing import Optional
from enum import Enum
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import requests

class Type(str, Enum):
    mod = "mod"
    modpack = "modpack"

class ServerClientRequired(str, Enum):
    required = "required"
    optional = "optional"
    unsupported = "unsupported"
    

class ModLoader(str, Enum):
    fabric = "fabric"
    forge = "forge"
    all = "quilt"

class Category(str, Enum):
    adventure = "adventure"
    cursed = "cursed"
    decoration = "decoration"
    economy = "economy"
    equipement = "equipement"
    food = "food"
    game_mechanics = "game-mechanics"
    library = "library"
    magic = "magic"
    management = "management"
    minigame = "minigame"
    mobs = "mobs"
    optimization = "optimization"
    social = "social"
    storage = "storage"
    technology = "technology"
    transportation = "transportation"
    utility = "utility"
    worldgen = "worldgen"

app = FastAPI()

@app.get("/")
def get_plugin_info():
    return {"info": "This plugin allows ChatGPT to use an intermediary API to Modrinth API for Minecraft mod searches"}

@app.get("/minecraft/versions")
def get_minecraft_versions():
    response = requests.get('https://api.modrinth.com/v2/tag/game_version')
    if response.status_code == 200:
        data = response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail=f'Modrinth Response Error: {response.status_code}')
    return data

@app.get("/mods/search")
def search_mods(modloader: ModLoader, minecraft_version: str, q: Optional[str] = None, categories: Optional[str] = None, type: Optional[Type] = None, client_side: Optional[ServerClientRequired] = None, server_side: Optional[ServerClientRequired] = None, limit: Optional[int] = 20):
    categories_list = categories.split(',') if categories else []
    facets = [
        f'["versions:{minecraft_version}"]',
        f'["categories:{modloader}"]',
    ]
    for x in categories_list:
        if x not in Category.__members__:
            raise HTTPException(status_code=400, detail=f"Invalid category: {x}, expected only one or multiple separated by comas of: {Category.__members__}")
        facets.append(f'["categories:{x}"]')
    if type:
        facets.append(f'["project_type:{type}"]')
    if client_side is not None:
        facets.append(f'["client_side:{client_side}"]')
    if server_side is not None:
        facets.append(f'["server_side:{server_side}"]')
    facets_str = ','.join(facets)

    url = f'https://api.modrinth.com/v2/search?'
    if q is not None:
        q = q.replace(' ', '%20')
        print("q is: "+q)
        url += f'query={q}&'
    url += f'limit={limit}&index=relevance&facets=[{facets_str}]'
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail=f'Modrinth Response Error: {response.status_code}, URL: {url}')
    return data

@app.get("/mods/{mod_name}/version")
def get_mod_version(mod_name: str, modloader: Optional[ModLoader] = None, minecraft_version: Optional[str] = None):
    url = f'https://api.modrinth.com/v2/project/{mod_name}/version'
    if modloader or minecraft_version:
        url += '?'
        if modloader:
            url += f'loaders=["{modloader}"]'
            if minecraft_version:
                url += '&'
        if minecraft_version:
            url+= f'game_versions=["{minecraft_version}"]'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail=f'Modrinth Response Error: {response.status_code}')
    return data

@app.get("/mods/{mod_name}/download")
def get_mod_download(mod_name: str, modloader: Optional[ModLoader] = None, minecraft_version: Optional[str] = None):
    url = f'https://api.modrinth.com/v2/project/{mod_name}/version'
    if modloader or minecraft_version:
        url += '?'
        if modloader:
            url += f'loaders=["{modloader}"]'
            if minecraft_version:
                url += '&'
        if minecraft_version:
            url+= f'game_versions=["{minecraft_version}"]'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data and 'files' in data[0] and data[0]['files']:
            file = data[0]['files'][0]

            url = file['url']
            filename = file['filename']

            return {"filename": filename, "url": url}
        else:
            raise HTTPException(status_code=404, detail=f'No files matching arguments for mod {mod_name}')
    else:
        raise HTTPException(status_code=response.status_code, detail=f'Modrinth Response Error: {response.status_code}')

@app.get("/mods/{mod_name}/wiki")
async def get_mod_wiki(mod_name: str, go_to_url: Optional[str] = None):
    response = requests.get(f'https://api.modrinth.com/v2/project/{mod_name}')
    if response.status_code == 200:
        data = response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail=f'Modrinth Response Error: {response.status_code}')

    if data['wiki_url']:
        if go_to_url is None:
            go_to_url = data['wiki_url']
        response = requests.get(go_to_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            text = soup.get_text()
            base_url = response.url
            links = [urljoin(base_url, a['href']) for a in soup.find_all('a', href=True)]

            return {"text": text, "links": links}
        else:
            raise HTTPException(status_code=response.status_code, detail=f'Wiki URL Response Error: {response.status_code}')
    else:
        raise HTTPException(status_code=404, detail=f'Mod {mod_name} has no wiki linked from Modrinth')
    
@app.get("/mods/{mod_name}/dependencies")
def get_mod_dependencies(mod_name: str):
    response = requests.get(f'https://api.modrinth.com/v2/project/{mod_name}/dependencies')
    if response.status_code == 200:
        data = response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail=f'Modrinth Response Error: {response.status_code}')
    return data

@app.get("/mods/{mod_name}")
def get_mod(mod_name: str):
    response = requests.get(f'https://api.modrinth.com/v2/project/{mod_name}')
    if response.status_code == 200:
        data = response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail=f'Modrinth Response Error: {response.status_code}')
    return data
