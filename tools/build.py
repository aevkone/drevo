"""Сборка index.html из данных в data/.

index.html — шаблон сайта (разметка, стили и код генератора древа, та же версия, что у
сайта-образца) со встроенными данными. Данные лежат в странице как JSON-литералы
window.FAMILY_BASE, window.FAMILY_ENTRIES, window.FAMILY_SRC и window.FAMILY_BIO.
Править нужно только data/*.json, затем запустить:

    python tools/build.py

Что откуда берётся:
  data/base.json      люди (P), семьи (C), подписи браков (wl) и пр.  -> FAMILY_BASE
  data/branches.json  ветви: br, brs, low                              -> FAMILY_BASE.br/.brs/.low
  data/src.json       источники и уверенность по каждому человеку     -> FAMILY_SRC
  data/entries.json   воспоминания и дополнения родных                 -> FAMILY_ENTRIES
  data/bio.json       рассказы «Жизнь» в карточке ({код: текст})       -> FAMILY_BIO
  data/first.json     «Самое первое упоминание рода»: появляется, только если есть файл img

Подписи над карточками (поле tag в base.json: «дед», «мать», «сын»…) на сайт не выводятся:
по правилу семьи на карточках нет служебных подписей. В base.json они остаются как заметки.

Скрипт также пересчитывает цифры в шапке и в описании страницы (людей, поколений).
Первичное извлечение данных из готовой страницы:  python tools/build.py --extract
"""
import json
from html import escape as html_escape
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = ROOT / 'index.html'
DATA = ROOT / 'data'
VARS = {'FAMILY_BASE': 'base.json', 'FAMILY_ENTRIES': 'entries.json', 'FAMILY_SRC': 'src.json', 'FAMILY_BIO': 'bio.json'}


def locate(html, var):
    key = 'window.%s=' % var
    i = html.index(key) + len(key)
    _, n = json.JSONDecoder().raw_decode(html[i:])
    return i, i + n


def load(name, default=None):
    p = DATA / name
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding='utf-8'))


def ru(n, one, few, many):
    a, b = n % 10, n % 100
    return one if a == 1 and b != 11 else few if 2 <= a <= 4 and not 12 <= b <= 14 else many


def base_for_page():
    base = load('base.json')
    br = load('branches.json', {}) or {}
    brs = br.get('brs', {})
    mp = dict(br.get('br', {}))
    for pid, p in base['P'].items():   # новые люди ветвей k/s/m/r/l — в свою ветвь по коду фамилии
        if pid not in mp and p[2] in brs:
            mp[pid] = p[2]
    base['br'] = {k: v for k, v in mp.items() if k in base['P']}
    base['brs'] = brs
    base['low'] = [x for x in br.get('low', []) if x in base['P']]
    base['tag'] = {}
    return base


def image_size(path):
    """Ширина и высота JPEG или PNG без сторонних библиотек."""
    b = path.read_bytes()
    if b[:8] == b'\x89PNG\r\n\x1a\n':
        return int.from_bytes(b[16:20], 'big'), int.from_bytes(b[20:24], 'big')
    i = 2
    while i < len(b) - 9:
        if b[i] != 0xFF:
            i += 1
            continue
        m = b[i + 1]
        if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            return int.from_bytes(b[i + 7:i + 9], 'big'), int.from_bytes(b[i + 5:i + 7], 'big')
        i += 2 + int.from_bytes(b[i + 2:i + 4], 'big')
    raise ValueError('не удалось узнать размер ' + str(path))


def first_section():
    """«Самое первое упоминание рода» — только если скан из data/first.json лежит на месте."""
    f = load('first.json')
    if not f or not f.get('img') or not (ROOT / f['img']).is_file():
        return ''
    e = lambda s: html_escape(str(s or ''), quote=True)
    w, h = image_size(ROOT / f['img'])
    pts = f.get('poly') or (lambda x, y, bw, bh: [[x, y], [x + bw, y], [x + bw, y + bh], [x, y + bh]])(*f['box'])
    poly = ' '.join('%.1f,%.1f' % (px * w, py * h) for px, py in pts)
    return ('<section class="first-anc" id="firstAnc" aria-labelledby="faHead">\n'
            '  <h2 class="fa-head" id="faHead">%s</h2>\n'
            '  <figure class="fa-scan">\n'
            '    <button type="button" class="fa-img" id="faImg" data-src="%s" data-title="%s" aria-label="Открыть скан крупно">\n'
            '      <img src="%s" width="%d" height="%d" alt="%s" loading="lazy" decoding="async">\n'
            '      <svg class="fa-outline" viewBox="0 0 %d %d" preserveAspectRatio="none" aria-hidden="true"><polygon points="%s"/></svg>\n'
            '    </button>\n  </figure>\n'
            '  <div class="fa-text">\n    <h3 id="faTitle">%s</h3>\n    <p class="fa-lead">%s</p>\n%s'
            '    <p class="fa-btns">%s<button type="button" class="fa-zoom" id="faZoom">Скан крупно</button></p>\n'
            '  </div>\n</section>') % (
        e(f.get('head')), e(f['img']), e(f.get('scanTitle')), e(f['img']), w, h, e(f.get('alt')), w, h, poly,
        e(f.get('title')), e(f.get('lead')),
        '    <p class="fa-src">%s</p>\n' % e(f['src']) if f.get('src') else '',
        '<button type="button" class="fa-go" data-line="%s">Показать на древе</button>' % e(f['line']) if f.get('line') else '')


def build():
    html = PAGE.read_bytes().decode('utf-8')
    a = html.index('<!--FIRST-->') + len('<!--FIRST-->')
    html = html[:a] + first_section() + html[html.index('<!--/FIRST-->', a):]
    vals = {'FAMILY_BASE': base_for_page(), 'FAMILY_ENTRIES': load('entries.json', []),
            'FAMILY_SRC': load('src.json', {}), 'FAMILY_BIO': load('bio.json', {})}
    for var in VARS:
        a, b = locate(html, var)
        html = html[:a] + json.dumps(vals[var], ensure_ascii=False) + html[b:]

    P = vals['FAMILY_BASE']['P']
    people = len([k for k in P if k != 'SIB']) + len(vals['FAMILY_BASE'].get('sib', {}).get('list', []))
    gens = max(p[0] for p in P.values()) + 1
    pw, gw = ru(people, 'человек', 'человека', 'человек'), ru(gens, 'поколение', 'поколения', 'поколений')
    html = re.sub(r'<b id="fPeople">\d+</b> <span id="fPeopleWord">[^<]*</span>',
                  '<b id="fPeople">%d</b> <span id="fPeopleWord">%s</span>' % (people, pw), html, count=1)
    html = re.sub(r'<b id="fGens">\d+</b> <span id="fGensWord">[^<]*</span>',
                  '<b id="fGens">%d</b> <span id="fGensWord">%s</span>' % (gens, gw), html, count=1)
    html = re.sub(r'(<meta (?:name|property)="(?:og:)?description" content="[^"]*?)\d+ человека?, \d+ поколени[а-я]+',
                  lambda m: '%s%d %s, %d %s' % (m.group(1), people, pw, gens, gw), html)
    PAGE.write_bytes(html.encode('utf-8'))
    print('index.html собран: %d %s, %d %s' % (people, pw, gens, gw))


def extract():
    html = PAGE.read_bytes().decode('utf-8')
    DATA.mkdir(exist_ok=True)
    for var, name in VARS.items():
        if var == 'FAMILY_BASE':
            continue  # base.json хранит больше, чем страница (подписи tag), его не перезаписываем
        a, b = locate(html, var)
        (DATA / name).write_text(json.dumps(json.loads(html[a:b]), ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        print('извлечено', name)


if __name__ == '__main__':
    extract() if '--extract' in sys.argv else build()
