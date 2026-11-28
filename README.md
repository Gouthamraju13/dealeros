# DealerOS reconciliation

Two systems, A and B, record the same business events. This app loads both exports, finds the rows where they disagree, and shows them in a table, without ever showing one company's data to another.

The stack is Django (with Django REST Framework) and SQLite on the backend, and React (Vite) on the front.

Live demo: https://dealeros-khaki.vercel.app

## How to run it

You need Python 3.11 or newer, Node.js 18 or newer, and Git. Start from a fresh clone and run these in order.

```bash
git clone <your-repo-url> dealeros
cd dealeros

# 1. Install the backend
python -m venv .venv
.venv\Scripts\activate             # on Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt

# 2. Create the database, import the CSVs and find the disagreements
cd backend
python manage.py migrate
python manage.py import_data

# 3. Start the backend (leave this running)
python manage.py runserver
```

Open a second terminal for the screen:

```bash
cd dealeros/frontend
npm install
npm run dev
```

Then open http://localhost:5173 in your browser.

To run the tests, use the first terminal (with the virtual environment active): `cd backend` and then `python -m pytest`.

When the import finishes it prints a summary like `A: 120 read, 120 saved, 120 in database; B: 121 read, 121 saved, 121 in database`. If "read" and "in database" ever differ, the command stops with an error. It is safe to run `import_data` as many times as you like.

The CSV files live in `backend/data/` and are never edited. A short list of the odd things in them is in `docs/DATA_NOTES.md`.

## What I built

An importer (`python manage.py import_data`) that saves every CSV row, including the messy ones, and keeps the original text of anything it had to clean. A comparison function (`reconcile/compare.py`) with no database or web code in it. One API endpoint, `GET /api/disagreements/?org=ORG-A&reason=VALUE_MISMATCH&sort=-value`. And a plain React table with an org picker, a reason filter and sortable value columns. The difference column is B minus A.

It finds seven kinds of disagreement: the four required ones (MISSING_IN_B, ORPHAN_IN_B, DUPLICATE_IN_B, VALUE_MISMATCH) plus LOCATION_MISMATCH, DATE_MISMATCH and VOIDED_IN_A. On the supplied files it finds 12 disagreements. The reasons for each rule are in DECISIONS.md.

## What I deliberately did not build

Login, pagination, Docker, a pretty design, and extra filters. The org picker is not real security, because there is no login: the API does keep the orgs apart, but anyone who can reach it can ask for either org. A real version would take the org from the signed-in user. I spent my time on the importer's safety, the comparison rules, the tests and keeping the orgs separate.


## How I worked with the agent

I used Claude as my coding agent. It first built a working version and tested it, then walked me through rebuilding the whole project by hand, one small step at a time. I typed or pasted each file myself, ran each command, and asked questions when I did not understand something. For example, I asked why the importer could not run before the other files existed, and it explained that the importer is only a set of instructions and needs the command file as a "button" to run it.

I checked the agent's work with my own eyes instead of trusting it. I ran the importer twice and made sure the counts stayed the same (120 rows from A and 121 from B saved). I ran the tests (19 for the comparison rules, 31 in total). I broke the code on purpose, first by flagging every split as a duplicate and then by removing the org filter, and watched the tests fail before putting it back. I also opened the page in my browser and checked that ORG-B never shows an ORG-A location.

## The three questions

**a. One thing the AI agent got wrong, and how I noticed.**

When I was creating the folders, the agent gave me several PowerShell commands to paste at once. Only some of them ran, so the `management` and `tests` folders were missing and one command failed with "Could not find a part of the path". I noticed because the file list in VS Code did not match what the agent described, and there was red error text in the terminal. We fixed it by running the commands one at a time and checking the file list again.

**b. The part I am least confident about, and why.**

The VOIDED decision. If System A says a record is voided but System B still has an entry, I flag it as VOIDED_IN_A. Someone could reasonably say that B's entry is expected and not an error. I am also not fully sure about the cross-org row (REC-1077): only ORG-A sees it, and ORG-B is never told about its stray entry. If I had more time, I would ask what the reviewers expect in both cases.

**c. If I had a second day, what I would fix first.**

Login. Right now the org comes from the web address, so anyone who can reach the API could ask for the other org's data. It comes first because keeping the two companies apart is the main point of the assignment, and a real fix would take the org from the signed-in user instead of the address.