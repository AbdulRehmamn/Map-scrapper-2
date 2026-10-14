"""Visible-browser Google Maps business contact collector. Python 3.10+."""
import csv
import json
import queue
import re
import threading
import time
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse
import tkinter as tk
from tkinter import ttk, messagebox

ROOT = Path(__file__).resolve().parent
FIELDS = ['name', 'address', 'maps_phone', 'website', 'emails', 'website_phones', 'contact_sources', 'maps_url', 'status']


def extract_contacts(html, url):
    from bs4 import BeautifulSoup
    import phonenumbers
    soup = BeautifulSoup(html, 'html.parser')
    emails, phones = set(), set()
    for a in soup.select('a[href]'):
        href = a['href']
        if href.lower().startswith('mailto:'):
            emails.update(re.findall(r'[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}', href.split('?')[0]))
        if href.lower().startswith('tel:'):
            phones.add(href[4:].split('?')[0].strip())
    for tag in soup(['script', 'style', 'noscript']):
        tag.decompose()
    text = soup.get_text(' ', strip=True)
    emails.update(re.findall(r'[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}', text))
    for match in phonenumbers.PhoneNumberMatcher(text, 'US'):
        if phonenumbers.is_valid_number(match.number):
            phones.add(phonenumbers.format_number(match.number, phonenumbers.PhoneNumberFormat.E164))
    emails = {e.lower().rstrip('.') for e in emails if not e.lower().endswith(('.png', '.jpg', '.svg', '.webp'))}
    links = []
    for a in soup.select('a[href]'):
        target = urljoin(url, a['href']).split('#')[0]
        if urlparse(target).hostname == urlparse(url).hostname and any(w in (a.get_text(' ') + target).lower() for w in ('contact', 'about', 'team')):
            if target not in links:
                links.append(target)
    return emails, phones, links


def crawl_site(url, stop):
    import requests
    from urllib.robotparser import RobotFileParser
    session = requests.Session()
    session.headers['User-Agent'] = 'MapsContactCollector/1.0'
    emails, phones, sources, errors = set(), set(), [], []
    origin = '{0.scheme}://{0.netloc}'.format(urlparse(url))
    robot = RobotFileParser()
    try:
        response = session.get(origin + '/robots.txt', timeout=12)
        if response.status_code in (401, 403):
            return '', '', '', 'Website robots access denied'
        if response.ok:
            robot.parse(response.text.splitlines())
        elif response.status_code != 404:
            return '', '', '', 'Website robots unavailable'
        else:
            robot.parse([])
    except requests.RequestException:
        return '', '', '', 'Website robots unavailable'
    todo, visited = [url], set()
    while todo and len(visited) < 5 and not stop.is_set():
        current = todo.pop(0)
        if current in visited:
            continue
        visited.add(current)
        if not robot.can_fetch('MapsContactCollector', current):
            errors.append('robots disallowed page')
            continue
        try:
            response = session.get(current, timeout=15)
            response.raise_for_status()
            if urlparse(response.url).hostname != urlparse(url).hostname:
                errors.append('redirect to different host; skipped')
                continue
            if 'text/html' not in response.headers.get('Content-Type', ''):
                continue
            e, p, links = extract_contacts(response.text, response.url)
            emails.update(e)
            phones.update(p)
            if e or p:
                sources.append(response.url)
            todo.extend(x for x in links if x not in visited and x not in todo)
        except requests.RequestException as exc:
            errors.append(type(exc).__name__)
        stop.wait(1)
    return '; '.join(sorted(emails)), '; '.join(sorted(phones)), '; '.join(sources), '; '.join(sorted(set(errors)))


class App:
    def __init__(self, root):
        self.root, self.events, self.stop = root, queue.Queue(), threading.Event()
        self.active = False
        root.title('Maps Contact Scraper')
        root.geometry('880x600')
        frame = ttk.Frame(root, padding=20)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Maps Contact Scraper', font=('Segoe UI', 23, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Business listings + public contact details from linked websites').pack(anchor='w', pady=(0, 15))
        ttk.Label(frame, text='Search phrase or Google Maps search URL').pack(anchor='w')
        self.query = ttk.Entry(frame)
        self.query.insert(0, 'electrical contractors in San Diego CA')
        self.query.pack(fill='x', pady=8)
        row = ttk.Frame(frame)
        row.pack(fill='x')
        ttk.Label(row, text='Maximum listings:').pack(side='left')
        self.limit = ttk.Spinbox(row, from_=1, to=1000, width=8)
        self.limit.set('100')
        self.limit.pack(side='left', padx=10)
        self.start = ttk.Button(row, text='Start new search', command=lambda: self.launch(False))
        self.start.pack(side='left', padx=5)
        self.resume = ttk.Button(row, text='Resume saved search', command=lambda: self.launch(True))
        self.resume.pack(side='left', padx=5)
        ttk.Button(row, text='Stop and save', command=self.stop.set).pack(side='left', padx=5)
        ttk.Label(frame, text='Results autosave to output/results.csv. Emails are collected from websites, when published.\nIf Google shows consent or verification, resolve it in the browser; the app waits up to 2 minutes.', wraplength=800).pack(anchor='w', pady=15)
        self.log = tk.Text(frame, height=20, wrap='word', state='disabled')
        self.log.pack(fill='both', expand=True)
        self.root.after(150, self.poll)
        self.root.protocol('WM_DELETE_WINDOW', self.close)

    def close(self):
        if self.active:
            self.stop.set()
            messagebox.showinfo('Saving', 'Stopping safely. Close the window after the run finishes.')
        else:
            self.root.destroy()

    def poll(self):
        while not self.events.empty():
            msg = self.events.get()
            if msg is None:
                self.active = False
                self.start.config(state='normal')
                self.resume.config(state='normal')
            else:
                self.log.config(state='normal')
                self.log.insert('end', msg + '\n')
                self.log.see('end')
                self.log.config(state='disabled')
        self.root.after(150, self.poll)

    def launch(self, resume):
        if self.active:
            return
        try:
            limit = int(self.limit.get())
            if not 1 <= limit <= 1000:
                raise ValueError()
            query = self.query.get().strip()
            if not query:
                raise ValueError()
        except ValueError:
            messagebox.showerror('Input', 'Enter a search and a listing limit from 1 to 1000.')
            return
        self.stop.clear()
        self.active = True
        self.start.config(state='disabled')
        self.resume.config(state='disabled')
        threading.Thread(target=self.run, args=(query, limit, resume), daemon=True).start()

    def run(self, query, limit, resume):
        output = ROOT / 'output'
        output.mkdir(exist_ok=True)
        state_path = output / 'checkpoint.json'
        try:
            from playwright.sync_api import sync_playwright
            if resume:
                if not state_path.exists():
                    raise ValueError('No saved search found. Start a new search first.')
                state = json.loads(state_path.read_text('utf-8'))
                query = state['query']
                self.events.put('Resuming: ' + query)
            else:
                if state_path.exists():
                    stamp = time.strftime('%Y%m%d-%H%M%S')
                    for file in (state_path, output / 'results.csv'):
                        if file.exists():
                            file.rename(file.with_name(stamp + '-' + file.name))
                state = {'query': query, 'urls': [], 'rows': [], 'completed': []}
            def save():
                temp = state_path.with_suffix('.tmp')
                temp.write_text(json.dumps(state, indent=2, ensure_ascii=False), 'utf-8')
                temp.replace(state_path)
                with (output / 'results.csv').open('w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=FIELDS)
                    writer.writeheader()
                    for row in state['rows']:
                        # Prevent scraped strings from becoming Excel formulas.
                        writer.writerow({k: ("'" + str(v) if str(v).startswith(('=', '+', '-', '@')) else v) for k, v in row.items()})
            save()
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=False)
                context = browser.new_context(locale='en-US')
                page = context.new_page()
                url = query if query.startswith('https://') else 'https://www.google.com/maps/search/' + quote(query)
                if urlparse(url).hostname not in ('www.google.com', 'maps.google.com', 'google.com'):
                    raise ValueError('Use a Google Maps URL or a plain search phrase.')
                page.goto(url, wait_until='domcontentloaded', timeout=60000)
                self.events.put('Browser opened. Waiting for Maps results...')
                ready = False
                for _ in range(120):
                    if self.stop.is_set():
                        break
                    if page.locator('a[href*="/maps/place/"]').count() or page.locator('h1').count() and '/maps/place/' in page.url:
                        ready = True
                        break
                    self.stop.wait(1)
                if not ready:
                    raise RuntimeError('No Maps results detected. Resolve any browser prompt and resume.')
                if '/maps/place/' in page.url:
                    if page.url not in state['urls']:
                        state['urls'].append(page.url)
                else:
                    unchanged = 0
                    while len(state['urls']) < limit and unchanged < 6 and not self.stop.is_set():
                        before = len(state['urls'])
                        for href in page.locator('a[href*="/maps/place/"]').evaluate_all('(els) => els.map(e => e.href)'):
                            href = href.split('?')[0]
                            if href not in state['urls']:
                                state['urls'].append(href)
                        save()
                        unchanged = unchanged + 1 if len(state['urls']) == before else 0
                        feed = page.locator('[role="feed"]').first
                        if feed.count():
                            feed.evaluate('(e) => e.scrollTop = e.scrollHeight')
                        else:
                            break
                        self.stop.wait(2)
                self.events.put(f"Discovered {len(state['urls'])} listings. Extracting up to {limit}.")
                def text(selector):
                    loc = page.locator(selector).first
                    return loc.inner_text(timeout=5000).strip() if loc.count() else ''
                def attr(selector, name):
                    loc = page.locator(selector).first
                    return (loc.get_attribute(name) or '') if loc.count() else ''
                for link in state['urls'][:limit]:
                    if self.stop.is_set():
                        break
                    if link in state['completed']:
                        continue
                    try:
                        page.goto(link, wait_until='domcontentloaded', timeout=45000)
                        page.locator('h1').first.wait_for(timeout=20000)
                        row = dict.fromkeys(FIELDS, '')
                        row.update(name=text('h1'), address=attr('[data-item-id="address"]', 'aria-label').removeprefix('Address: '), maps_phone=attr('[data-item-id^="phone:tel:"]', 'data-item-id').removeprefix('phone:tel:'), website=attr('a[data-item-id="authority"]', 'href'), maps_url=link)
                        if not row['name']:
                            raise RuntimeError('Listing title missing')
                        if row['website']:
                            self.events.put('Checking website: ' + row['name'])
                            row['emails'], row['website_phones'], row['contact_sources'], row['status'] = crawl_site(row['website'], self.stop)
                        row['status'] = row['status'] or 'Collected; blank fields were not found'
                        if self.stop.is_set():
                            break  # retry interrupted listing on resume
                        state['rows'].append(row)
                        state['completed'].append(link)
                        save()
                        self.events.put(f"Saved {len(state['rows'])}: {row['name']}")
                    except Exception as exc:
                        self.events.put('Listing skipped (retry with Resume): ' + str(exc)[:200])
                    self.stop.wait(1.5)
                browser.close()
            save()
            self.events.put('Stopped and saved.' if self.stop.is_set() else 'Finished. Results: ' + str(output / 'results.csv'))
        except Exception as exc:
            self.events.put('ERROR: ' + str(exc))
        finally:
            self.events.put(None)


if __name__ == '__main__':
    root = tk.Tk()
    ttk.Style().theme_use('clam')
    App(root)
    root.mainloop()
