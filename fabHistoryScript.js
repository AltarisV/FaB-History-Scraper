// ==UserScript==
// @name         FaB History Scraper
// @version      1.0
// @description  Scrape match history data from a player's own page
// @author       Leon Schüßler
// @match        https://gem.fabtcg.com/profile/player/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    const navigationDelay = 2000;
    let allEventData = JSON.parse(localStorage.getItem('allEventData')) || [];
  
    function scrapeEventData() {
        const currentPageLink = document.querySelector('.pagination-pages li.page-item.active');
        const currentPageIndex = currentPageLink ? parseInt(currentPageLink.textContent.trim()) : 1;
      
        const events = document.querySelectorAll('.card.mb-3');

        events.forEach(event => {
            const eventDetails = event.querySelector('.card-body');
            if (eventDetails) {
                let eventName, eventDate;
                const eventRows = eventDetails.querySelectorAll('tbody tr');
                eventRows.forEach(row => {
                    const thText = row.querySelector('th')?.textContent.trim();
                    const tdText = row.querySelector('td')?.textContent.trim();
                    if (thText && tdText) {
                        if (thText === 'Event Nickname') {
                            eventName = tdText;
                        } else if (thText === 'Date') {
                            eventDate = tdText;
                        }
                    }
                });

                const eventMatches = eventDetails.querySelectorAll('.block-table tbody tr:not(:first-child)');
                const eventResults = {
                    eventName: eventName || 'Event name not found',
                    eventDate: eventDate || 'Event date not found',
                    matches: []
                };

                eventMatches.forEach(match => {
                    const round = match.querySelector('td:nth-child(1)').textContent.trim();
                    const player1 = match.querySelector('td:nth-child(2)').textContent.trim();
                    const player2 = match.querySelector('td:nth-child(3)').textContent.trim();
                    const result = match.querySelector('td:nth-child(4)').textContent.trim();
                    eventResults.matches.push({ round, player1, player2, result });
                });

                allEventData.push(eventResults);
            } else {
                console.log('Event details not found.');
            }
        });

        console.log(`Scraped data from page ${currentPageIndex}.`);
        localStorage.setItem('allEventData', JSON.stringify(allEventData));
        navigateToNextPage(currentPageIndex);
    }

    function navigateToNextPage(currentPageIndex) {
        const currentPageLink = document.querySelector('.pagination-pages li.page-item.active');
        if (currentPageLink && currentPageLink.nextElementSibling) {
            const nextPageLink = currentPageLink.nextElementSibling.querySelector('a.page-link');
            if (nextPageLink) {
                console.log(`Navigating to page ${currentPageIndex + 1}...`);
                window.location.href = nextPageLink.href;
            } else {
                console.log('Reached the end of match history. Saving data...');
                saveDataToCSV();
                localStorage.removeItem('allEventData'); // Clear the stored data
            }
        } else {
            console.log('Reached the end of match history. Saving data...');
            saveDataToCSV();
            localStorage.removeItem('allEventData'); // Clear the stored data
        }
    }
  
    function saveDataToCSV() {
        // Convert allEventData to CSV format
        const csvRows = ['Event Name,Event Date,Round,Player 1,Player 2,Result'];
        allEventData.forEach(event => {
            event.matches.forEach(match => {
                const row = [
                    `"${event.eventName}"`,
                    `"${event.eventDate}"`,
                    match.round,
                    `"${match.player1}"`,
                    `"${match.player2}"`,
                    `"${match.result}"`,
                ].join(',');
                csvRows.push(row);
            });
        });

        const csvContent = csvRows.join('\n');

        // Create a Blob from the CSV content
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);

        // Create a link to download the file
        const downloadLink = document.createElement('a');
        downloadLink.href = url;
        downloadLink.setAttribute('download', 'match_history.csv');
        document.body.appendChild(downloadLink);

        // Trigger download and remove the link
        downloadLink.click();
        document.body.removeChild(downloadLink);

        console.log('Scraped data saved to CSV.');
    }

    setTimeout(scrapeEventData, navigationDelay);
})();
