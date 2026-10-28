#!/usr/bin/env python3
# Gera o card do macho reprodutor atual da den de Kuro Ryu (#12568).
# Lê a den pública, acha o /breed/ID atual, lê a página do lobo e grava:
#   cave_br/stud/stud_card.png  — card com foto, nome, características e preço
#   cave_br/stud/index.html     — redireciona para o /breed/ID atual
#   cave_br/stud/stud.json      — dados usados (para conferência)
# Créditos: Thayná Batista da Silva | Kuro Ryu ID#12568
import html, io, json, os, re, sys, urllib.request
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin

# As imagens de lobo do Wolvden trazem um bloco de texto zTXt grande.
PngImagePlugin.MAX_TEXT_CHUNK = 64 * 1024 * 1024

DEN = 'https://www.wolvden.com/den/12568'
OUT = os.path.join(os.path.dirname(__file__), '..', 'cave_br', 'stud')
UA = {'User-Agent': 'Mozilla/5.0 (WolvdenCaveBR stud card; +https://thaynabds.github.io/Wolvden/)'}
FONT_B = '/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf'
FONT_R = '/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf'
EMOJI = '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf'


def get(url, binary=False):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        data = r.read()
    return data if binary else data.decode('utf-8', 'replace')


def text_of(fragment):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', fragment))).strip()


def field(page_text, label, stop):
    m = re.search(re.escape(label) + r'\s+(.*?)\s+(?:' + stop + r')', page_text)
    return m.group(1).strip() if m else ''


def scrape():
    den = get(DEN)
    ids = re.findall(r'/breed/(\d+)', den)
    if not ids:
        sys.exit('não achei /breed/ID na den pública')
    wid = ids[0]
    page = get(f'https://www.wolvden.com/wolf/{wid}')
    t = text_of(page)
    title = text_of(re.search(r'<title>(.*?)</title>', page, re.S).group(1)).split('|:|')[0].strip()
    img = re.search(r'https://wolf\.wolvden\.com/[^"\']*\.' + wid + r'\.\d+\.png', page)
    price = field(t, 'Stud Price', 'Items Applied')
    gc_sc = re.findall(r'\d+', price)
    carriers = []
    for mut in ['Albinism', 'Melanism', 'Brachycephaly', 'Hereditary Cataracts']:
        if re.search(mut + r'\s+Carrier', t):
            carriers.append(mut)
    data = {
        'id': wid,
        'name': title,
        'image': img.group(0) if img else '',
        'base': re.sub(r'\s*\([\d.]+%\)', '', field(t, 'Base', 'Base Genetics')),
        'eyes': field(t, 'Eyes', 'Skin'),
        'mutation': field(t, 'Mutation', 'Secondary Mutation'),
        'secondary': field(t, 'Secondary Mutation', 'Tertiary Mutation'),
        'carriers': carriers,
        'price_gc': gc_sc[0] if len(gc_sc) > 1 else '',
        'price_sc': gc_sc[-1] if gc_sc else '',
        'breed_url': f'https://www.wolvden.com/breed/{wid}',
    }
    return data


def chips(d):
    out = []
    g = re.search(r'\bG(\d)\b', d['name'])
    if g:
        out.append(f'Gen {g.group(1)}')
    elif 'NBW' in d['name'] or '💦' in d['name']:
        out.append('NBW')
    for m in (d['mutation'], d['secondary']):
        if m and m != 'None':
            out.append(m.replace('Piebald: ', 'Piebald '))
    for c in d['carriers']:
        out.append(f'{c} Carrier')
    if d['eyes']:
        out.append(d['eyes'] + ' eyes')
    if d['base']:
        out.append(d['base'])
    return out[:6]


def draw_text(img, xy, txt, font, fill, emoji_font, anchor='mm'):
    # Desenha texto com emojis coloridos (fonte separada para os emojis).
    d = ImageDraw.Draw(img)
    parts = re.findall(r'([\U0001F000-\U0001FAFF☀-➿⭐️‍]+|[^\U0001F000-\U0001FAFF☀-➿⭐️‍]+)', txt)
    size = font.size
    widths = []
    for p in parts:
        if re.match(r'[\U0001F000-\U0001FAFF☀-➿⭐]', p):
            widths.append(size * 1.15 * len(re.findall(r'[\U0001F000-\U0001FAFF☀-➿⭐]', p)))
        else:
            widths.append(d.textlength(p, font=font))
    total = sum(widths)
    x = xy[0] - total / 2 if anchor == 'mm' else xy[0]
    y = xy[1]
    for p, w in zip(parts, widths):
        if re.match(r'[\U0001F000-\U0001FAFF☀-➿⭐]', p):
            e = Image.new('RGBA', (160, 160), (0, 0, 0, 0))
            ImageDraw.Draw(e).text((80, 80), p, font=emoji_font, embedded_color=True, anchor='mm')
            bb = e.getbbox()
            if bb:
                e = e.crop(bb)
                e = e.resize((int(e.width * size / 109 * 1.05), int(e.height * size / 109 * 1.05)), Image.LANCZOS)
                img.alpha_composite(e, (int(x), int(y - e.height / 2)))
        else:
            d.text((x, y), p, font=font, fill=fill, anchor='lm')
        x += w


def render(d):
    W, H = 640, 560
    img = Image.new('RGBA', (W, H), (14, 14, 34, 255))
    dr = ImageDraw.Draw(img)
    if d['image']:
        wolf = Image.open(io.BytesIO(get(d['image'], binary=True))).convert('RGBA')
        r = W / wolf.width
        wolf = wolf.resize((W, int(wolf.height * r)), Image.LANCZOS)
        # O lobo fica na parte de baixo da imagem do Wolvden: recorta 340px
        # terminando um pouco acima da borda inferior.
        bottom = max(340, wolf.height - int(wolf.height * 0.04))
        img.alpha_composite(wolf.crop((0, bottom - 340, W, bottom)), (0, 0))
    dr.rectangle((0, 340, W, H), fill=(20, 20, 40, 255))
    dr.line((0, 340, W, 340), fill=(109, 40, 217, 255), width=4)
    fs = ImageFont.truetype(FONT_R, 18)
    fb = ImageFont.truetype(FONT_B, 30)
    fc = ImageFont.truetype(FONT_R, 19)
    em = ImageFont.truetype(EMOJI, 109)
    dr.text((W / 2, 362), 'F O R   S T U D', font=fs, fill=(124, 58, 237), anchor='mm')
    name = d['name']
    while dr.textlength(name, font=fb) > W - 40 and fb.size > 18:
        fb = ImageFont.truetype(FONT_B, fb.size - 1)
    draw_text(img, (W / 2, 400), name, fb, (232, 228, 248), em)
    # etiquetas
    cs = chips(d)
    rows, row, wsum = [], [], 0
    for c in cs:
        w = dr.textlength(c, font=fc) + 28
        if wsum + w > W - 40 and row:
            rows.append(row); row, wsum = [], 0
        row.append((c, w)); wsum += w + 8
    if row:
        rows.append(row)
    y = 440
    for row in rows[:2]:
        total = sum(w for _, w in row) + 8 * (len(row) - 1)
        x = (W - total) / 2
        for c, w in row:
            dr.rounded_rectangle((x, y, x + w, y + 32), 10, outline=(124, 58, 237), width=2, fill=(124, 58, 237, 40))
            dr.text((x + w / 2, y + 16), c, font=fc, fill=(196, 181, 253), anchor='mm')
            x += w + 8
        y += 40
    if d['price_sc']:
        price = f"{d['price_sc']} SC" + (f" OR {d['price_gc']} GC" if d['price_gc'] else '')
        dr.text((W / 2, H - 22), price, font=ImageFont.truetype(FONT_B, 20), fill=(245, 184, 46), anchor='mm')
    dr.rectangle((0, 0, W - 1, H - 1), outline=(109, 40, 217), width=4)
    return img.convert('RGB')


def main():
    os.makedirs(OUT, exist_ok=True)
    d = scrape()
    render(d).save(os.path.join(OUT, 'stud_card.png'), optimize=True)
    with open(os.path.join(OUT, 'stud.json'), 'w', encoding='utf-8') as f:
        # Sem a URL da imagem: ela muda de carimbo a cada acesso e geraria
        # um commit a cada execução mesmo sem troca de stud.
        json.dump({k: v for k, v in d.items() if k != 'image'}, f, ensure_ascii=False, indent=2)
    with open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stud atual — Howling Ebony</title>
<meta http-equiv="refresh" content="0; url={d['breed_url']}">
<style>body{{background:#0d0f1a;color:#e8e4f8;font-family:sans-serif;text-align:center;padding:40px}}a{{color:#c4b5fd}}</style>
</head><body><p>Abrindo o stud atual… <a href="{d['breed_url']}">{html.escape(d['name'])}</a></p>
<p style="font-size:12px;color:#8f90a8">Thayná Batista da Silva | Kuro Ryu ID#12568</p></body></html>''')
    print('STUD-CARD-OK', d['id'], d['name'])


if __name__ == '__main__':
    main()
