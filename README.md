# Maps Contact Scraper

Windows quick start
1. Install Python 3.10+ from python.org with "Add Python to PATH" enabled. Python's standard installer includes tkinter.
2. Extract this entire ZIP into a writable folder. Do not run it inside the ZIP.
3. Double-click start.bat. It creates an isolated environment, installs dependencies and Chromium, and opens the desktop app. Internet is required for setup and searches.
4. Enter a search such as "plumbers in Dallas Texas" or a full Google Maps search URL. Choose a maximum and click Start new search.
5. CSV results open in Excel: output/results.csv.

Fields: business name, address, Maps phone, website, public emails, website phones, source page URLs, Maps listing URL, extraction status. Multiple contact values are separated by semicolons in each business row. Website emails are not normally shown by Maps itself, so the app checks the linked homepage and up to four same-host contact/about/team pages. Phone text is collected from tel links and validated visible text (US default region). It does not verify deliverability, ownership or mobile/landline status.

Start new search archives the previous CSV/checkpoint and starts fresh. Resume saved search uses the saved query, ignores the current query field, skips completed listings and retries failed listings. Stop saves progress; it can take a network timeout to finish. Close the app only after stopping finishes. Keep output/checkpoint.json for resume. Only run one copy of the app per folder.

Limits: Google Maps only exposes a subset of results for a search. The maximum is a cap, not a guaranteed count. Make narrower city/trade searches for more coverage. The tool cannot extract private, unpublished or unavailable information, and does not promise all data. Websites rendered entirely in JavaScript may yield no contacts. Website robots rules are respected; pages that cannot be checked are skipped. Maps interface changes may require selector updates. Resolve consent or verification manually in the visible browser; no bypass is included. Use public business data in accordance with site terms and applicable requirements.

Troubleshooting: if installation fails, read the terminal error and check firewall/proxy restrictions. If Maps yields no results, use an English-language Google Maps search URL, resolve prompts, and Resume. Failed listings remain eligible for Resume. Contact cells starting with formula characters are prefixed with an apostrophe for safer Excel viewing.

Validation: Python syntax and local extraction/checkpoint-related smoke checks were performed in the build environment. Live Maps searches and Windows batch execution require verification on your Windows computer.
