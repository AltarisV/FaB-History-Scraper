// ==UserScript==
// @name         FaB History Scraper
// @version      2.1
// @description  Scrape match history from all pages manually using a button on the profile history page. Includes multilingual result parsing, distinguishes between Swiss and Playoff rounds, and captures both rated and unrated events.
// @author       Leon Schüßler
// @match        https://gem.fabtcg.com/profile/player/
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

    const isProfilePage = window.location.pathname.startsWith('/profile/player');
    const isHistoryPage = window.location.pathname.startsWith('/profile/history');

    if (isProfilePage) {
        injectScrapeButton();
    }

    if (localStorage.getItem('scrapeInProgress') === 'true' && isHistoryPage) {
        console.log('Resuming scraping...');
        setTimeout(scrapeEventData, navigationDelay);
        return;
    }

    function injectScrapeButton() {
        const nameHeader = document.querySelector('.profile-text h2');
        if (!nameHeader) return;

        const wrapper = document.createElement('div');
        wrapper.style.display = 'flex';
        wrapper.style.alignItems = 'center';
        wrapper.style.justifyContent = 'space-between';

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

        button.addEventListener('click', () => {
            const playerName = nameHeader.textContent.trim();
            const gemId = document.querySelector('.profile-text p')?.textContent.trim().replace('GEM ID: ', '') || 'Unknown';
            const eloBlock = [...document.querySelectorAll('.profile-stat h3')].find(h => h.textContent.includes('Elo Rating'));
            const eloRating = eloBlock?.querySelector('strong')?.textContent.trim() || 'Unknown';

            localStorage.setItem('fabPlayerMeta', JSON.stringify({ name: playerName, gemId, eloRating }));
            localStorage.setItem('allEventData', JSON.stringify([]));
            localStorage.setItem('scrapeInProgress', 'true');

            window.location.href = '/profile/history/?page=1';
        });

        nameHeader.parentElement.insertBefore(wrapper, nameHeader);
        wrapper.appendChild(nameHeader);
        wrapper.appendChild(button);
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

            // Determine the rated status by scanning all meta items.
            // Default to "No" if none explicitly indicate rating.
            let rated = 'No';
            const metaItems = Array.from(event.querySelectorAll('.event__meta-item'));
            for (const item of metaItems) {
                const txt = item.textContent.toLowerCase();
                if (txt.includes('rated')) {
                    rated = txt.includes('not rated') || txt.includes('unrated') ? 'No' : 'Yes';
                    break;
                }
            }

            // Process all tables to capture both Swiss and Playoff matches.
            const tables = event.querySelectorAll('table');
            const matches = [];
            tables.forEach(table => {
                const headerCell = table.querySelector('tr th');
                if (!headerCell) return;
                const headerText = headerCell.textContent.trim().toLowerCase();
                // Only process tables that indicate match data.
                if (!(headerText.includes('round') || headerText.includes('playoff'))) return;

                // Get rows from tbody if available; if not, exclude the header row.
                let rows = table.querySelectorAll('tbody tr');
                if (!rows.length) {
                    rows = table.querySelectorAll('tr:not(:first-child)');
                }

                if (headerText.includes('playoff')) {
                    // Process Playoff rounds table.
                    rows.forEach(row => {
                        const cells = row.querySelectorAll('td');
                        if (cells.length >= 3) {
                            // Prepend "P" to differentiate playoff rounds from Swiss rounds.
                            let round = "P" + cells[0].textContent.trim();
                            const opponent = cells[1].textContent.trim().normalize('NFC');
                            let result = cells[2].textContent.trim();
                            const ratingChange = cells[3]?.textContent.trim() || '';

                            if (localizedWins.includes(result)) result = 'Win';
                            else if (localizedLosses.includes(result)) result = 'Loss';
                            else if (localizedDraws.includes(result)) result = 'Draw';
                            else if (localizedByes.includes(result)) result = 'Bye';
                            else result = 'Unknown';

                            matches.push({ round, opponent, result, ratingChange });
                        }
                    });
                } else if (headerText.includes('round')) {
                    // Process Swiss rounds table.
                    rows.forEach(row => {
                        const cells = row.querySelectorAll('td');
                        if (cells.length >= 3) {
                            let round = cells[0].textContent.trim();
                            const opponent = cells[1].textContent.trim().normalize('NFC');
                            let result = cells[2].textContent.trim();
                            // Use cell 4 if available, otherwise leave ratingChange blank.
                            const ratingChange = (cells.length >= 5 ? cells[4].textContent.trim() : '');

                            if (localizedWins.includes(result)) result = 'Win';
                            else if (localizedLosses.includes(result)) result = 'Loss';
                            else if (localizedDraws.includes(result)) result = 'Draw';
                            else if (localizedByes.includes(result)) result = 'Bye';
                            else result = 'Unknown';

                            matches.push({ round, opponent, result, ratingChange });
                        }
                    });
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
        const playerMeta = JSON.parse(localStorage.getItem('fabPlayerMeta')) || {};

        const metaHeader = [
            `# Player Name: ${playerMeta.name ?? 'Unknown'}`,
            `# GEM ID: ${playerMeta.gemId ?? 'Unknown'}`,
            `# Elo Rating (Overall): ${playerMeta.eloRating ?? 'Unknown'}`,
            `# Export Date: ${new Date().toISOString()}`,
            ''
        ];

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
        const csvContent = BOM + metaHeader.concat(csvRows).join('\n');
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
