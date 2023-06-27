from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from typing import Optional
from enum import Enum
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import requests

class Search(str, Enum):
    relevance = "relevance"
    downloads = "downloads"
    follows = "follows"
    newest = "newest"
    updated = "updated"

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

ORIGINS = [
    "http://localhost:8000",
    "https://chat.openai.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/.well-known", StaticFiles(directory=".well-known"), name="static")

@app.get("/")
def get_plugin_info():
    return {"info": "This plugin allows ChatGPT to use an intermediary API to Modrinth API for Minecraft mod searches"}

@app.get("/logo.png")
async def plugin_logo() -> FileResponse:
    return FileResponse('logo.png', media_type='image/png')

@app.get("/openapi.yaml")
async def openapi_spec() -> Response:
    with open("openapi.yaml") as f:
        return Response(f.read(), media_type="text/yaml")

@app.get("/minecraft/versions")
def get_minecraft_versions():
    response = requests.get('https://api.modrinth.com/v2/tag/game_version')
    if response.status_code == 200:
        data = response.json()
        cut_entries = data[:100]
        hidden_entries = len(data) - len(cut_entries)
        cut_entries.append(f"Due to length, {hidden_entries} entries are not shown")
        return cut_entries
    else:
        raise HTTPException(status_code=response.status_code, detail=f'Modrinth Response Error: {response.status_code}')
    
@app.get("/minecraft/versions/{minecraft_version}")
def verify_minecraft_version(minecraft_version: str):
    response = requests.get('https://api.modrinth.com/v2/tag/game_version')
    if response.status_code == 200:
        data = response.json()
        for entry in data:
            if entry["version"] == minecraft_version:
                return entry
        raise HTTPException(status_code=404, detail=f'{minecraft_version} is not a valid Minecraft version')
    else:
        raise HTTPException(status_code=response.status_code, detail=f'Modrinth Response Error: {response.status_code}')

@app.get("/mods/search")
def search_mods(modloader: ModLoader, minecraft_version: str, q: Optional[str] = None, search_type: Optional[Search] = "relevance", categories: Optional[str] = None, type: Optional[Type] = None, client_side: Optional[ServerClientRequired] = None, server_side: Optional[ServerClientRequired] = None, limit: Optional[int] = 20):
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
    url += f'limit={limit}&index={search_type}&facets=[{facets_str}]'
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
        slugs = []
        for project in data['projects']:
            slugs.append(project['slug'])
        return {"dependencies": slugs}
    else:
        raise HTTPException(status_code=response.status_code, detail=f'Modrinth Response Error: {response.status_code}')

@app.get("/mods/{mod_name}")
def get_mod(mod_name: str):
    response = requests.get(f'https://api.modrinth.com/v2/project/{mod_name}')
    if response.status_code == 200:
        data = response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail=f'Modrinth Response Error: {response.status_code}')
    return data
