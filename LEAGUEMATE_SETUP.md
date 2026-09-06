# Setting Up the ClickyDraft Assistant (Windows, step by step)

This walks through everything from a blank computer to a running tool,
assuming no prior coding experience. It's written for Windows since
that's what this league mostly uses; a short Mac note is at the bottom.

Budget about 20 minutes the first time. Do this a day or two BEFORE the
draft, not five minutes before it starts.

---

## Step 1 — Install Python

1. Go to **https://www.python.org/downloads/** in your browser.
2. Click the big yellow "Download Python 3.x.x" button.
3. Open the downloaded installer file.
4. **Important:** on the very first install screen, there's a checkbox at
   the bottom that says **"Add Python.exe to PATH"** (or "Add python.exe
   to PATH"). **Check that box.** This is the single most common thing
   people miss.
5. Click "Install Now" and let it finish.
6. To confirm it worked: open **Command Prompt** (press the Windows key,
   type `cmd`, press Enter) and type:
   ```
   python --version
   ```
   Press Enter. You should see something like `Python 3.12.4`. If instead
   you see an error like "python is not recognized," restart your
   computer and try again — the PATH change needs a restart to take
   effect.

## Step 2 — Get the code

You don't need to install Git for this — easiest is downloading a ZIP.

1. Whoever is sharing this with you (Bradley) will give you a link to
   the GitHub repository, or add you as a collaborator on it. If you got
   a link, open it in your browser.
2. Click the green **"Code"** button, then **"Download ZIP"**.
3. Find the downloaded ZIP file (usually in your Downloads folder) and
   right-click it → **"Extract All..."** → choose somewhere easy to find,
   like your Desktop.
4. You should now have a folder (probably named `WETWILL-main` or
   similar) with files like `README.md`, `config.example.yaml`, and a
   `src` folder inside it. Rename it to `WETWILL` if you like — doesn't
   matter, just remember where it is.

## Step 3 — Open a terminal in that folder

1. Open the extracted `WETWILL` folder in File Explorer.
2. Click into the address bar at the top of the File Explorer window
   (where the folder path is shown), type `cmd`, and press Enter. This
   opens a Command Prompt window already pointed at that folder.
   (Alternative: open Command Prompt normally, then type `cd ` followed
   by the folder path, e.g. `cd C:\Users\YourName\Desktop\WETWILL`.)

## Step 4 — Install the tool

In that Command Prompt window, type:
```
pip install -e .
```
Press Enter and wait — it'll download a few small packages
(`requests`, `rich`, `PyYAML`, `openpyxl`). This can take a minute.

If you see an error mentioning `pip` not recognized, try `python -m pip install -e .` instead.

## Step 5 — Create your personal config file

1. In the `WETWILL` folder (in File Explorer), find `config.example.yaml`.
2. Right-click it → Copy, then right-click in empty space → Paste. This
   makes a copy.
3. Rename the copy to exactly `config.yaml` (make sure it's not
   `config.yaml.txt` — if File Explorer is hiding file extensions, you
   may need to check "File name extensions" under the View tab first).
4. Right-click `config.yaml` → **Open with** → **Notepad** (or any text
   editor).
5. Find the line that says `my_team_id:` and instead fill in
   `my_team_name:` with your team's exact name as it appears in
   ClickyDraft/Yahoo, in quotes. Example:
   ```yaml
   my_team_name: "Touchdown Titans"
   ```
   (Leave `my_team_id:` blank — the tool will figure out the ID from
   your team name automatically the first time it runs.)
6. Leave `league_id`, `league_instance_id`, and the scoring-related
   settings as they are — those are the same for everyone in the league.
7. For `projections_csv`, you have two choices:
   - Use the one Bradley shared with you, if he gave you a
     `projections.csv` file — put it in the `data` folder inside
     `WETWILL`, replacing/alongside the example one, matching whatever
     path is written in `config.yaml`.
   - Or make your own — see `data/projections.example.csv` in that same
     folder for the column format to copy.
8. Save the file (Ctrl+S) and close Notepad.

## Step 6 — Get your own ClickyDraft cookie

This lets the tool read the draft on your behalf. **Never use someone
else's cookie, and never send anyone yours** — it's the same as your
login session.

1. Log into ClickyDraft in Chrome, and open your league's draft board
   (the URL should look like
   `https://clickydraft.com/draftapp/board/305775`).
2. Press **F12** to open Developer Tools. A panel opens, usually on the
   right or bottom of the browser window.
3. Click the **Network** tab near the top of that panel.
4. Refresh the ClickyDraft page (F5) so requests start showing up in the
   list.
5. In the list, click on any request whose name contains `305775` or
   `picks` or `league-instances`.
6. On the right side, find the **Headers** section, scroll to **Request
   Headers**, and find the line starting with **Cookie:**
7. Click into that value and select/copy the ENTIRE thing after
   `Cookie: ` — it's long, with several `key=value;` pairs separated by
   semicolons. Copy all of it.

## Step 7 — Run it

Back in your Command Prompt window (still in the `WETWILL` folder):

1. Set your cookie for this session by typing (replace the placeholder
   with what you copied, keeping the quotes):
   ```
   set CLICKYDRAFT_COOKIE=paste the whole cookie value here
   ```
   Press Enter. (Nothing will print — that's normal.)
2. Run the tool:
   ```
   clickydraft-assistant --once
   ```
   This does a single check and prints a table — good for confirming
   everything is set up right without needing to babysit a live draft.
   If it prints a recommendations table with no red error text, you're
   good.
3. For the actual live draft, run it without `--once` so it keeps
   updating automatically:
   ```
   clickydraft-assistant
   ```
4. **Leave this Command Prompt window open** for the whole draft,
   side-by-side with your browser tab showing the ClickyDraft board. It
   refreshes on its own every second or two as picks happen.
5. To stop it at any point, click into the Command Prompt window and
   press **Ctrl+C**.

## Troubleshooting

- **"Auth error" / red text about the cookie** — your cookie has expired
  or was copied incompletely. Go back to Step 6 and re-capture it (you
  may need to refresh the ClickyDraft page again first).
- **"Could not find a team named '...'"** — the `my_team_name` in your
  `config.yaml` doesn't exactly match what ClickyDraft has on file. The
  error message will list the exact team names it found — copy one of
  those exactly (including capitalization) into `config.yaml`.
- **Command Prompt closes itself / window flashes shut** — you may have
  double-clicked a file instead of running the command from an open
  Command Prompt window. Make sure you're typing the commands into an
  already-open Command Prompt, not double-clicking anything.
- Still stuck — take a screenshot of the error and send it back for help.

---

## Note for Mac users

Same overall flow, different terminal commands:
- Install Python from python.org (Mac installer), or via `brew install python` if you have Homebrew.
- Use **Terminal** (Spotlight search → "Terminal") instead of Command Prompt.
- `cd` into the extracted folder: `cd ~/Downloads/WETWILL` (adjust the path).
- Setting the cookie: `export CLICKYDRAFT_COOKIE='paste the whole cookie value here'` (use single quotes).
- Everything else (`pip install -e .`, `clickydraft-assistant`, etc.) is identical.
