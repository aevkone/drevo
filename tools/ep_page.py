"""page.py ДЕЛО КАДР СТОРОНА(L|R|LR) [y0 y1] — страница кадра в среднем разрешении, без хранения кадра.
y0,y1 — доли высоты (по умолчанию вся страница). Пишет <TEMP>/drevo_ep/<дело>/ p_<кадр><сторона>.jpg"""
import io, json, sys, pathlib, urllib.request
from PIL import Image

vol, n, side = sys.argv[1], int(sys.argv[2]), sys.argv[3]
y0, y1 = (float(sys.argv[4]), float(sys.argv[5])) if len(sys.argv) > 5 else (0.0, 1.0)
import tempfile, os
D = pathlib.Path(os.environ.get('DREVO_EP', pathlib.Path(tempfile.gettempdir()) / 'drevo_ep')) / vol; D.mkdir(parents=True, exist_ok=True)
L = D / 'frames.json'
if not L.exists():
    j = json.load(urllib.request.urlopen('https://www.epaveldas.lt/vepis-api/internal/findById?id=1349/1/' + vol))
    L.write_text(json.dumps(sorted(j['resourcesFull'])))
p = '%04d' % n
u = next(x for x in json.loads(L.read_text()) if x.rsplit('/', 1)[1].startswith(p + '-'))
im = Image.open(io.BytesIO(urllib.request.urlopen(u).read())).convert('L'); W, H = im.size
x0, x1 = {'L': (0.08, 0.53), 'R': (0.50, 0.95), 'LR': (0.08, 0.95)}[side]
c = im.crop((int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)))
c.thumbnail((1500, 1500)); out = D / ('p_%d%s.jpg' % (n, side)); c.save(out, quality=82); print(out.name, c.size)
