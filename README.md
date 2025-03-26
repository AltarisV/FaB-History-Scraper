# FaB-History-Scraper

Check out the latest release here: [Latest Release](https://github.com/AltarisV/FaB-History-Scraper/releases)

## About
`FaB-History-Scraper` is a userscript for GreaseMonkey/TamperMonkey designed to scrape a user's personal matchup history from [https://gem.fabtcg.com/profile/player/](https://gem.fabtcg.com/profile/player/). This script automates the process of gathering match history data, which can be useful for analysis, tracking progress, or simply archiving your match records.

## Prerequisites
To use the Scraper, you need:
- A web browser (such as Chrome or Firefox).
- GreaseMonkey (for Firefox users) or TamperMonkey (for Chrome and other browsers) extension installed in your browser.

## Installation
1. Open your browser and click on the GreaseMonkey/TamperMonkey extension icon.
2. Choose to create a new script.
3. Copy the contents of `fabHistoryScript.js` from this repository.
4. Paste the script into the new script section in GreaseMonkey/TamperMonkey.
5. Save the script (Ctrl+S).

## Usage
1. Navigate to [https://gem.fabtcg.com/profile/player/](https://gem.fabtcg.com/profile/player/) in your web browser.
2. Change your language to English (top right of the page)
3. There should be a Yellow Button next to your player name ("Start Match History Export").
4. The script will automatically enter your match history and go from page to page. Just let it run.
5. Once the scraping process is complete, the script will download a CSV file containing the scraped match history.

## Visualizing Data
To visualize your match history data, you can use the `datadoll.exe` script provided in the latest release.
1. Drop the "match_history.csv" file generated by the scraper in the same folder as the `datadoll.exe` file.
2. Run `datadoll.exe`.
3. The script will generate visualizations of your match history data.
4. After running `datadoll.exe`, a dash web-app will start at [http://localhost:8050/](http://localhost:8050/). You can view the visualizations in your web browser.

## Upcoming
Very useful features like
- How much Elo did I steal from this one player in all of our matches
- How does the tournament starting time affect my performance
- More silly graphs

## License
This project is [MIT](https://choosealicense.com/licenses/mit/) licensed.
