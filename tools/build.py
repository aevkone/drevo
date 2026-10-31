"""Сборка index.html из данных в data/.

Данные древа лежат в index.html как JSON-литералы window.FAMILY_BASE,
window.FAMILY_SRC и window.FAMILY_ENTRIES. Править их нужно в data/*.json,
затем запустить:  python tools/build.py
Первичное извлечение из готовой страницы:  python tools/build.py --extract
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = ROOT / 'index.html'
DATA = ROOT / 'data'
VARS = {'FAMILY_BASE': 'base.json', 'FAMILY_SRC': 'src.json', 'FAMILY_ENTRIES': 'entries.json'}


def locate(html, var):
    key = 'window.%s=' % var
    i = html.index(key) + len(key)
    _, n = json.JSONDecoder().raw_decode(html[i:])
    return i, i + n


def extract():
    html = PAGE.read_bytes().decode('utf-8')
    DATA.mkdir(exist_ok=True)
    for var, name in VARS.items():
        a, b = locate(html, var)
        val = json.loads(html[a:b])
        (DATA / name).write_text(json.dumps(val, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        print('извлечено', name)


def build():
    html = PAGE.read_bytes().decode('utf-8')
    for var, name in VARS.items():
        val = json.loads((DATA / name).read_text(encoding='utf-8'))
        a, b = locate(html, var)
        html = html[:a] + json.dumps(val, ensure_ascii=False) + html[b:]
    PAGE.write_bytes(html.encode('utf-8'))
    print('index.html собран')


if __name__ == '__main__':
    extract() if '--extract' in sys.argv else build()
