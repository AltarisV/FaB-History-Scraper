// ==UserScript==
// @name         FaB History Scraper
// @version      2.0
// @description  Scrape match history from all pages manually using a button on the profile history page. Includes multilingual result parsing and recognizes Byes.
// @author       Leon Schüßler
// @match        https://gem.fabtcg.com/profile/history/*
// @grant        none
// ==/UserScript==

(function () {
    'use strict';

    const navigationDelay = 1000;

    const localizedWins = ['Win', '勝利', 'Victoria', 'Vittoria', 'Victoire', 'Sieg'];
    const localizedLosses = ['Loss', '敗北', 'Derrota', 'Sconfitta', 'Défaite', 'Niederlage'];
    const localizedDraws = ['Draw', '引き分け', 'Empate', 'Pareggio', 'Match nul', 'Unentschieden', 'Égalité'];
    const localizedByes = ['Bye', '不戦勝', 'Bye (Freilos)', 'Sin rival'];

    if (localStorage.getItem('scrapeInProgress') === 'true') {
        console.log('Resuming scraping...');
        setTimeout(scrapeEventData, navigationDelay);
        return;
    }

    injectScrapeButton();

    function injectScrapeButton() {
        const headings = [...document.querySelectorAll('h1, h2, h3, h4')];
        const header = headings.find(h => h.textContent.trim().toLowerCase().includes('event history') || h.textContent.trim().toLowerCase().includes('historique'));

        const button = document.createElement('button');
        button.textContent = 'Start Match History Export';
        button.style.fontSize = '14px';
        button.style.padding = '6px 10px';
        button.style.marginLeft = '20px';
        button.style.backgroundColor = '#d4af37';
        button.style.color = '#000';
        button.style.border = 'none';
        button.style.borderRadius = '4px';
        button.style.cursor = 'pointer';
        button.style.boxShadow = '0 1px 4px rgba(0,0,0,0.3)';
        button.style.verticalAlign = 'middle';

        button.addEventListener('click', () => {
            console.log('Scraping started...');
            localStorage.setItem('allEventData', JSON.stringify([]));
            localStorage.setItem('scrapeInProgress', 'true');
            scrapeEventData();
        });

        if (header) {
            const wrapper = document.createElement('span');
            wrapper.appendChild(button);
            header.appendChild(wrapper);
        } else {
            button.style.position = 'fixed';
            button.style.top = '20px';
            button.style.right = '20px';
            button.style.zIndex = '1000';
            document.body.appendChild(button);
        }
    }

    function scrapeEventData() {
        const currentPageIndex = getCurrentPageIndex();
        let allEventData = JSON.parse(localStorage.getItem('allEventData')) || [];

        const events = document.querySelectorAll('.event');
        if (!events.length) {
            console.warn('No .event containers found!');
        }

        events.forEach(event => {
            const eventName = event.querySelector('h4.event__title')?.textContent.trim() || 'Unknown';
            const eventDate = event.querySelector('.event__when')?.textContent.trim() || 'Unknown';

            let rated = 'Unknown';
            const ratedItem = [...event.querySelectorAll('.event__meta-item')].find(div => div.textContent.toLowerCase().includes('rated'));
            if (ratedItem) {
                const ratedText = ratedItem.textContent.toLowerCase();
                rated = ratedText.includes('not rated') ? 'No' : (ratedText.includes('rated') ? 'Yes' : 'Unknown');
            }

            const tables = event.querySelectorAll('table');
            if (tables.length < 1) return;

            const matchRows = tables[tables.length - 1].querySelectorAll('tbody tr');
            const matches = [];
            matchRows.forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells.length >= 3) {
                    const round = cells[0].textContent.trim();
                    const opponent = cells[1].textContent.trim().normalize('NFC');
                    let result = cells[2].textContent.trim();
                    const ratingChange = cells[4]?.textContent.trim() ?? '';

                    if (localizedWins.includes(result)) result = 'Win';
                    else if (localizedLosses.includes(result)) result = 'Loss';
                    else if (localizedDraws.includes(result)) result = 'Draw';
                    else if (localizedByes.includes(result)) result = 'Bye';
                    else result = 'Unknown';

                    matches.push({ round, opponent, result, ratingChange });
                }
            });

            allEventData.push({ eventName, eventDate, rated, matches });
        });

        console.log(`Scraped page ${currentPageIndex}.`);
        localStorage.setItem('allEventData', JSON.stringify(allEventData));
        navigateToNextPage(currentPageIndex);
    }

    function getCurrentPageIndex() {
        const active = document.querySelector('.pagination .page-item.active');
        return active ? parseInt(active.textContent.trim()) : 1;
    }

    function navigateToNextPage(currentPageIndex) {
        const active = document.querySelector('.pagination .page-item.active');
        const next = active?.nextElementSibling;
        const link = next?.querySelector('a.page-link');

        if (link) {
            console.log(`Navigating to page ${currentPageIndex + 1}...`);
            setTimeout(() => {
                window.location.href = link.href;
            }, navigationDelay);
        } else {
            console.log('Reached last page. Saving CSV...');
            localStorage.setItem('scrapeInProgress', 'false');
            saveDataToCSV();
            localStorage.removeItem('allEventData');
        }
    }

    function saveDataToCSV() {
        const allEventData = JSON.parse(localStorage.getItem('allEventData')) || [];
        const csvRows = ['Event Name,Event Date,Rated,Round,Opponent,Result,Rating Change'];

        allEventData.forEach(event => {
            event.matches.forEach(match => {
                csvRows.push([
                    `"${event.eventName}"`,
                    `"${event.eventDate}"`,
                    `"${event.rated}"`,
                    `"${match.round}"`,
                    `"${match.opponent}"`,
                    `"${match.result}"`,
                    `"${match.ratingChange}"`
                ].join(','));
            });
        });

        const BOM = '\uFEFF';
        const csvContent = BOM + csvRows.join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });

        const url = URL.createObjectURL(blob);
        const downloadLink = document.createElement('a');
        downloadLink.href = url;
        downloadLink.setAttribute('download', 'match_history.csv');
        document.body.appendChild(downloadLink);
        downloadLink.click();
        document.body.removeChild(downloadLink);

        console.log('Scraped data saved to CSV.');
    }
})();
