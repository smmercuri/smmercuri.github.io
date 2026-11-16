#!/usr/bin/env python3
"""
Builds index.html from template.html and the text in content/*.md.

    python3 generate_html.py

Edit content/*.md (text) or template.html (layout, styling), never index.html: it is
overwritten every time this runs. Commit and push the regenerated index.html with your edits.

Content format
  about.md, images.md   paragraphs; "# " heading, "- " bullets (indent to continue a bullet)
  employment.md, education.md, talks.md, conferences.md
                        blocks separated by a blank line: date / title / where / optional note
  publications.md       blocks: title line / details line (numbered automatically, newest highest)
  profile.md            "key: value" lines: name, role, affiliation, email (with "(at)"),
                        github, updated, and any number of "link: Label | URL"
  Everywhere: [text](url), **bold**, *italic*, $maths$ / $$display maths$$ (\\$ for a dollar sign),
  and <!-- comments --> are ignored.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent


# ───────────── tiny Markdown helpers ─────────────
def esc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def emph(t):
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    return re.sub(r'\*(.+?)\*', r'<em>\1</em>', t)


def link(text, url):
    external = not re.match(r'(#|mailto:)', url)
    return f'<a href="{url}"' + (' target="_blank" rel="noopener"' if external else '') + f'>{emph(text)}</a>'


def text_only(md):
    """[text](url), **bold**, *italic*; everything else is plain text."""
    out, last = '', 0
    for m in re.finditer(r'\[([^\]]+)\]\(([^)\s]+)\)', md):
        out += emph(esc(md[last:m.start()])) + link(esc(m[1]), esc(m[2]))
        last = m.end()
    return out + emph(esc(md[last:]))


def inline(md):
    """Maths first ($$display$$, $inline$, \\$ for a literal dollar), so * and _ inside TeX are left alone."""
    md = md.replace('\\$', '\x01')
    out, last = '', 0
    for m in re.finditer(r'\$\$([\s\S]+?)\$\$|\$((?:\\\$|[^$])+?)\$', md):
        display = m[1] is not None
        tex = (m[1] if display else m[2]).replace('\x01', '\\$')
        out += text_only(md[last:m.start()].replace('\x01', '$'))
        out += f'<span class="tex" data-display="{1 if display else 0}">{esc(tex)}</span>'
        last = m.end()
    return out + text_only(md[last:].replace('\x01', '$'))


def clean(text):
    return re.sub(r'<!--[\s\S]*?-->', '', text).replace('\r\n', '\n').replace('\r', '\n').strip()


def blocks(text, keep_indent=False):
    """Blank-line separated blocks → lists of non-empty lines."""
    out = []
    for b in re.split(r'\n\s*\n', clean(text)):
        lines = [l.rstrip() if keep_indent else l.strip() for l in b.split('\n')]
        lines = [l for l in lines if l.strip()]
        if lines:
            out.append(lines)
    return out


# ───────────── renderers, one per kind of file ─────────────
def paragraphs(text, lede_first):
    """Headings (# ...), bullet lists (- ...) and paragraphs."""
    html, first = [], [True]
    for lines in blocks(text, keep_indent=True):
        para, items = [], []

        def flush():
            if para:
                cls = ' class="lede"' if lede_first and first[0] else ''
                html.append(f'<p{cls}>{inline(" ".join(para))}</p>')
                first[0] = False
                para.clear()
            if items:
                html.append('<ul class="bullets">' + ''.join(f'<li>{inline(i)}</li>' for i in items) + '</ul>')
                items.clear()

        for raw in lines:
            line = raw.strip()
            if re.match(r'#\s+', line):
                flush()
                html.append(f'<h2>{inline(re.sub(r"^#\s+", "", line))}</h2>')
            elif re.match(r'[-*•]\s+', line):
                if para:
                    flush()
                items.append(re.sub(r'^[-*•]\s+', '', line))
            elif items and re.match(r'\s', raw):
                items[-1] += ' ' + line
            else:
                if items:
                    flush()
                para.append(line)
        flush()
    return ''.join(html)


def rows(text):
    """date / title / where / optional note"""
    out = ''
    for l in blocks(text):
        out += (f'<li><span class="when">{inline(l[0])}</span><div>'
                f'<div class="what">{inline(l[1] if len(l) > 1 else "")}</div>'
                + (f'<div class="where">{inline(l[2])}</div>' if len(l) > 2 else '')
                + (f'<div class="note">{inline(" ".join(l[3:]))}</div>' if len(l) > 3 else '')
                + '</div></li>')
    return out


def pubs(text):
    """title / details"""
    return ''.join(f'<li><span class="t">{inline(l[0])}</span>'
                   + (f'<span class="m">{inline(" ".join(l[1:]))}</span>' if len(l) > 1 else '')
                   + '</li>' for l in blocks(text))


RENDER = {
    'about': lambda t: paragraphs(t, True),
    'images': lambda t: paragraphs(t, False),
    'employment': rows, 'education': rows, 'talks': rows, 'conferences': rows,
    'publications': pubs,
}


# ───────────── profile (top of page + footer) ─────────────
ICONS = {
    'github': '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 .5a11.5 11.5 0 0 0-3.64 22.41c.58.1.79-.25.79-.56v-2c-3.2.7-3.88-1.37-3.88-1.37-.52-1.33-1.28-1.69-1.28-1.69-1.04-.71.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.76 2.7 1.25 3.36.96.1-.75.4-1.25.73-1.54-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.29 1.19-3.1-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.77 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.81 1.19 1.84 1.19 3.1 0 4.42-2.7 5.39-5.26 5.68.41.36.78 1.06.78 2.14v3.17c0 .31.21.67.8.56A11.5 11.5 0 0 0 12 .5Z"/></svg>',
    'link': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17 17 7M9 7h8v8"/></svg>',
}


def button(icon, label, href):
    return f'<li><a href="{esc(href)}" target="_blank" rel="noopener">{ICONS[icon]}<span>{esc(label)}</span></a></li>'


def parse_profile(text):
    p = {'links': []}
    for line in clean(text).split('\n'):
        m = re.match(r'\s*([a-z]+)\s*:\s*(.*?)\s*$', line, re.I)
        if not m:
            continue
        key = m[1].lower()
        if key == 'link':
            p['links'].append(m[2])
        else:
            p[key] = m[2]
    return p


def profile_field(p, field, tag, attrs):
    if field == 'links':   # the email button is added by the page script, from data-email
        html = button('github', 'GitHub', p['github']) if p.get('github') else ''
        for l in p['links']:
            label, _, url = l.partition('|')
            if url:
                html += button('link', label.strip(), url.strip())
        return f'<{tag}{attrs} data-email="{esc(p.get("email", ""))}">{html}</{tag}>'
    if field == 'footer':
        year = re.search(r'\d{4}', p.get('updated', ''))
        year = year[0] if year else str(__import__('datetime').date.today().year)
        text = f'© {year} {p.get("name", "")}' + (f' · Last updated {p["updated"]}' if p.get('updated') else '')
    else:
        text = p.get(field, '')
    return f'<{tag}{attrs}>{esc(text)}</{tag}>'


# ───────────── fill the template ─────────────
def main():
    template = (ROOT / 'template.html').read_text()
    cut = template.index('<script>\n  (function () {')   # only fill the markup, never the script text
    page, script = template[:cut], template[cut:]
    read = lambda name: (ROOT / 'content' / f'{name}.md').read_text()
    p = parse_profile(read('profile'))
    filled = []

    def slot(m):
        tag, attrs, name = m[1], m[2], m[3]
        text = read(name)
        filled.append(name)
        if name == 'publications':   # numbers count down, newest highest
            attrs += f' style="counter-reset: pub {len(blocks(text)) + 1}"'
        return f'<{tag}{attrs}>{RENDER[name](text)}</{tag}>'

    page = re.sub(r'<(\w+)([^>]*?\sdata-md="([\w-]+)"[^>]*)></\1>', slot, page)
    page = re.sub(r'<(\w+)([^>]*?\sdata-field="(\w+)"[^>]*)>[\s\S]*?</\1>',
                  lambda m: profile_field(p, m[3], m[1], m[2]), page)
    if p.get('name'):
        page = re.sub(r'(<div class="avatar[^"]*"><img [^>]*?alt=")[^"]*"', lambda m: m[1] + esc(p['name']) + '"', page)
    page = re.sub(r'<!--\n  Template for index.html[\s\S]*?-->\n',
                  '<!-- Generated by generate_html.py from template.html and content/*.md. Do not edit: changes here are overwritten. -->\n',
                  page, count=1)

    (ROOT / 'index.html').write_text(page + script)
    print(f'Wrote index.html ({", ".join(filled)}).')


if __name__ == '__main__':
    main()
