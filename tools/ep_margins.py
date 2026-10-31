"""margins.py ДЕЛО FROM TO — скачать кадры (параллельно) и собрать листы с полями-фамилиями.
Поле фамилии — вертикальная колонка у левого края каждой страницы разворота; режем полосы, поворачиваем
в горизонталь и складываем строками: <TEMP>/drevo_ep/<дело>/ m_<from>.jpg (по 12 кадров на лист)."""
import json, sys, pathlib, urllib.request
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw

vol, a, b = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
import tempfile, os
B = pathlib.Path(os.environ.get('DREVO_EP', pathlib.Path(tempfile.gettempdir()) / 'drevo_ep')); D = B / vol; D.mkdir(parents=True, exist_ok=True)
L = D / 'frames.json'
if not L.exists():
    j = json.load(urllib.request.urlopen('https://www.epaveldas.lt/vepis-api/internal/findById?id=1349/1/' + vol))
    L.write_text(json.dumps(sorted(j['resourcesFull'])))
urls = json.loads(L.read_text())

import io
def get(n):
    """кадр — только в памяти: на диск пишем лишь полосы полей"""
    p = '%04d' % n
    u = next(x for x in urls if x.rsplit('/', 1)[1].startswith(p + '-'))
    im = Image.open(io.BytesIO(urllib.request.urlopen(u).read())).convert('L'); W, H = im.size; k = W / 1400
    out = []
    for side, (x0, x1) in (('L', (150, 225)), ('R', (745, 825))):
        s = im.crop((int(x0 * k), int(260 * k), int(x1 * k), int(1120 * k))).rotate(90, expand=True)
        s.thumbnail((1600, 120)); s.load()
        out.append(('%d%s' % (n, side), s))
    return out

with ThreadPoolExecutor(4) as ex:
    rows = [r for rs in ex.map(get, range(a, b + 1)) for r in rs]
per = 24
for i in range(0, len(rows), per):
    chunk = rows[i:i + per]
    h = sum(r.size[1] + 4 for _, r in chunk); w = 1700
    sheet = Image.new('L', (w, h), 255); d = ImageDraw.Draw(sheet); y = 0
    for lab, r in chunk:
        d.text((4, y + r.size[1] // 2 - 5), lab, fill=0)
        sheet.paste(r, (90, y)); y += r.size[1] + 4
    sheet.save(D / ('m_%s.jpg' % chunk[0][0]), quality=80)
    print('m_%s.jpg' % chunk[0][0])
