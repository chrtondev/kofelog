# kofelog

A simple, self-hosted coffee logger. Record the coffees you make each morning —
beans, grinder + setting, method, brewer, recipe (dose / water / time / yield),
and a rating — then browse your brew history. Everything runs locally on your own
machine; your data lives in a single SQLite file.

## Requirements

- **Python 3.8+** (check with `python3 --version`)
- **git**

## Setup

Open a terminal and run these one at a time:

```bash
# 1. Download the code
git clone https://github.com/chrtondev/kofelog.git
cd kofelog

# 2. Create an isolated environment for the dependencies
python3 -m venv venv

# 3. Turn the environment on
source venv/bin/activate          # macOS / Linux
# venv\Scripts\activate           # Windows (use this line instead)

# 4. Install the one dependency (Flask)
pip install -r requirements.txt
```

## Run it

```bash
python app.py
```

You'll see a line like `Running on http://127.0.0.1:5000`.
Open that address in your browser: **http://localhost:5000**

That's it — start logging. To stop the server, press `Ctrl+C` in the terminal.

## Running it again later

You only do the setup once. Next time, just:

```bash
cd kofelog
source venv/bin/activate          # (Windows: venv\Scripts\activate)
python app.py
```

## How it works

- **Log Brew** — pick your beans, grinder, method, and brewer from dropdowns and
  save a brew. Use the **+ New** buttons to add new gear or beans without leaving
  the page.
- **History** — every brew you've logged, newest first.
- **Beans / Grinders / Brewers / Methods** — manage your reusable records. Items
  you've already used aren't deleted; they're *archived* so old logs stay intact.

Your coffee data is saved in `data/coffee.db`. Deleting that file wipes your log
and starts fresh.
