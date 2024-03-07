# FaB-History-Scraper

## About
`FaB-History-Scraper` is a userscript for GreaseMonkey/TamperMonkey designed to scrape a user's personal matchup history from [https://gem.fabtcg.com/profile/player/](https://gem.fabtcg.com/profile/player/). This script automates the process of gathering match history data, which can be useful for analysis, tracking progress, or simply archiving your match records.

## Prerequisites
To use `FaB-History-Scraper`, you need:
- A web browser (such as Chrome or Firefox).
- GreaseMonkey (for Firefox users) or TamperMonkey (for Chrome and other browsers) extension installed in your browser.

## Installation
1. Open your browser and click on the GreaseMonkey/TamperMonkey extension icon.
2. Choose to create a new script.
3. Copy the contents of `FaB-History-Scraper.user.js` from this repository.
4. Paste the script into the new script section in GreaseMonkey/TamperMonkey.
5. Save the script.

## Usage
1. Navigate to [https://gem.fabtcg.com/profile/player/](https://gem.fabtcg.com/profile/player/) in your web browser.
2. The script should automatically run and begin scraping match history data.
3. Once the scraping process is complete, the script will download a CSV file containing the scraped match history.

## How it Works
The script navigates through each page of your match history, collecting data on each match. Once it reaches the end of the history, it compiles all collected data into a CSV format and triggers a download of this file.

## Note
This script is intended for personal use and should be used ethically and in compliance with the website's terms of service. Please ensure that you do not violate any terms or overload the server with requests.

## Contributions
Contributions, issues, and feature requests are welcome. Feel free to check [issues page](https://github.com/[YourGitHubUsername]/FaB-History-Scraper/issues) if you want to contribute.

## Author
[Your Name]

## License
This project is [MIT](https://choosealicense.com/licenses/mit/) licensed.
