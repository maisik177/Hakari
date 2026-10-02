"""Small Windows desktop UI. Network work never blocks Tk's event loop."""
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser

from hoshi import Api, DATA, HoshiError, generate, load_key, parse_ids, process_queue, save_key


class App:
    def __init__(self, root):
        self.root = root
        self.busy = False
        self.events = queue.Queue()
        self.last_output = None
        root.title('Hoshi 0.1 — wydruki zamówień')
        root.geometry('720x480')
        root.minsize(620, 400)
        frame = ttk.Frame(root, padding=22)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Hoshi', font=('Segoe UI', 25, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Kompaktowe karty zamówień · dane z API IdoSell').pack(anchor='w', pady=(0, 16))
        self.key_status = tk.StringVar()
        ttk.Label(frame, textvariable=self.key_status).pack(anchor='w')
        ttk.Button(frame, text='Importuj / zmień klucz API z pliku…', command=self.import_key).pack(anchor='w', pady=(5, 18))
        ttk.Label(frame, text='Numery zamówień (oddziel spacją lub przecinkiem)').pack(anchor='w')
        self.ids = ttk.Entry(frame, font=('Segoe UI', 12))
        self.ids.pack(fill='x', pady=6)
        buttons = ttk.Frame(frame)
        buttons.pack(fill='x', pady=8)
        ttk.Button(buttons, text='Generuj i otwórz wydruk', command=self.manual).pack(side='left')
        ttk.Button(buttons, text='Pobierz kolejkę Hakari', command=self.queue_once).pack(side='left', padx=8)
        self.watch = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text='Odbieraj nowe paczki Hakari co 5 sekund', variable=self.watch).pack(anchor='w', pady=8)
        ttk.Label(frame, text='Nasłuchiwacz Hakari musi działać osobno (python/start-receiver.cmd).\nDrukowanie: Ctrl+P w podglądzie → A4, skala 100%.').pack(anchor='w', pady=8)
        self.status = tk.StringVar(value='Gotowe. Wybierz numery lub pobierz kolejkę.')
        ttk.Label(frame, textvariable=self.status, wraplength=660).pack(anchor='w', pady=10)
        self.update_key_status()
        root.after(100, self.drain)
        root.after(5000, self.poll)

    def update_key_status(self):
        try:
            load_key()
            self.key_status.set('Klucz zapisany dla tego użytkownika Windows — nie trzeba wpisywać ponownie.')
        except HoshiError:
            self.key_status.set('Brak klucza. Zaimportuj go jednorazowo z pliku.')

    def run(self, function):
        if self.busy:
            return
        self.busy = True
        self.status.set('Pobieranie danych z API…')
        def worker():
            try:
                self.events.put(('ok', function()))
            except HoshiError as exc:
                self.events.put(('error', str(exc)))
            except Exception:
                self.events.put(('error', 'Nie udało się wykonać operacji. Sprawdź dostęp do plików i połączenie; użyj CLI do diagnostyki.'))
        threading.Thread(target=worker, daemon=True).start()

    def import_key(self):
        if self.busy:
            return
        path = filedialog.askopenfilename(title='Wybierz plik z kluczem API', filetypes=[('Plik tekstowy', '*.txt'), ('Wszystkie', '*.*')])
        if not path:
            return
        def setup():
            key = Path(path).read_text(encoding='utf-8-sig').strip()
            Api(key).call('orders/orders/search', body={'params': {'resultsPage': 0, 'resultsLimit': 1}})
            save_key(key)
            return [], 'Klucz sprawdzony i zapisany. Kolejne uruchomienia nie wymagają importu.'
        self.run(setup)

    def manual(self):
        try:
            ids = parse_ids(self.ids.get())
        except HoshiError as exc:
            messagebox.showerror('Hoshi', str(exc))
            return
        def work():
            path, report = generate(ids)
            suffix = ' Uwaga: ' + '; '.join(report['warnings']) if report['warnings'] else ''
            return [path], f'Przygotowano {len(ids)} zamówień.' + suffix
        self.run(work)

    def queue_once(self):
        def work():
            paths = process_queue()
            return paths, f'Przygotowano paczki: {len(paths)}.' if paths else 'Brak nowych paczek w kolejce Hakari.'
        self.run(work)

    def poll(self):
        if self.watch.get() and not self.busy:
            self.queue_once()
        self.root.after(5000, self.poll)

    def drain(self):
        try:
            while True:
                status, value = self.events.get_nowait()
                self.busy = False
                if status == 'error':
                    self.watch.set(False)
                    self.status.set(value)
                    messagebox.showerror('Hoshi', value)
                else:
                    paths, message = value
                    self.status.set(message)
                    self.update_key_status()
                    for path in paths:
                        self.last_output = path
                        webbrowser.open(path.resolve().as_uri())
        except queue.Empty:
            pass
        self.root.after(100, self.drain)


if __name__ == '__main__':
    window = tk.Tk()
    App(window)
    window.mainloop()
