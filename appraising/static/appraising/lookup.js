/*
 * Vehicle Appraisal Tracker - Live Lookup
 *
 * The browser half of the API. The Live Lookup page asks /api/appraisals/
 * for JSON with fetch() and draws the results itself, with no page reload.
 * The server half is api_appraisals() in views.py.
 *
 * Loaded on every page from layout.html, but it only does anything when it
 * finds #lookup-form. Without JavaScript, that form submits to the
 * server-rendered Search page instead.
 */

// The key never changes: it is the one name this page saves its last search under.
const STORAGE_KEY = 'appraisalTracker.lastLookup';

// Wait this long after the last keystroke before asking the server, so typing
// "camry" sends one request instead of five.
const TYPING_DELAY_MS = 300;

/*
 * setUpLookup
 * Triggered: once, when the script runs on the Live Lookup page.
 * Changes:   restores the last search from localStorage into the box and
 *            dropdown, runs it, and starts listening for typing, dropdown
 *            changes and the Search button.
 */
function setUpLookup() {
    const form = document.querySelector('#lookup-form');
    if (!form) return;   // not on the Live Lookup page

    const input = form.querySelector('#lookup-q');
    const select = form.querySelector('#lookup-status');
    let typingTimer = null;   // `let` because each keystroke replaces it

    const saved = loadLastSearch();
    input.value = saved.q;
    select.value = saved.status;

    // Pressing Search (or Enter) fetches right away instead of leaving the page
    form.addEventListener('submit', (event) => {
        event.preventDefault();
        clearTimeout(typingTimer);
        runSearch(form);
    });

    // Typing fetches after a short pause
    input.addEventListener('input', () => {
        clearTimeout(typingTimer);
        typingTimer = setTimeout(() => runSearch(form), TYPING_DELAY_MS);
    });

    // Changing the status filter fetches right away
    select.addEventListener('change', () => runSearch(form));

    runSearch(form);
}

// Counts requests so a slow, older response can't overwrite a newer one.
let latestRequest = 0;

/*
 * runSearch
 * Triggered: by setUpLookup on page load, the Search button, typing, or the
 *            status dropdown.
 * Changes:   saves the search to localStorage, shows "Loading..." and then
 *            either the results, the empty state, or an error message.
 */
function runSearch(form) {
    const q = form.querySelector('#lookup-q').value.trim();
    const status = form.querySelector('#lookup-status').value;
    saveLastSearch(q, status);

    // Build /api/appraisals/?q=...&status=... (URLSearchParams escapes spaces and symbols)
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    if (status) params.set('status', status);
    const query = params.toString();
    const url = form.dataset.api + (query ? `?${query}` : '');

    latestRequest += 1;
    const thisRequest = latestRequest;
    showLoading();

    fetch(url, { headers: { Accept: 'application/json' } })
        .then((response) => {
            // fetch() only rejects when the network fails, so a 400 or 500 has to be
            // turned into an error here or it would be treated as good data
            if (!response.ok) {
                throw new Error(`The server answered ${response.status} ${response.statusText}.`);
            }
            return response.json();
        })
        .then((data) => {
            if (thisRequest !== latestRequest) return;   // a newer search is already on its way
            renderResults(data, q, status);
        })
        .catch((error) => {
            if (thisRequest !== latestRequest) return;
            showError(error);
        });
}

/*
 * showLoading
 * Triggered: by runSearch, the moment a request is sent.
 * Changes:   puts "Loading..." in the message line and fades the old results
 *            with .is-loading until the new data arrives.
 */
function showLoading() {
    const message = document.querySelector('#lookup-message');
    message.textContent = 'Loading...';
    message.className = 'lookup-message is-loading-text';
    document.querySelector('#lookup-results').classList.add('is-loading');
}

/*
 * renderResults
 * Triggered: by runSearch when the JSON arrives.
 * Changes:   empties the results list and builds one <li> card per file with
 *            createElement, or shows the empty-state message if count is 0.
 */
function renderResults(data, q, status) {
    const message = document.querySelector('#lookup-message');
    const list = document.querySelector('#lookup-results');
    list.classList.remove('is-loading');
    list.replaceChildren();   // remove the previous results

    if (data.count === 0) {
        const filters = [q && `"${q}"`, status && `status ${status}`].filter(Boolean).join(' with ');
        message.textContent = `No appraisal files match ${filters}. Try a shorter word or "Any status".`;
        message.className = 'lookup-message is-empty';
        return;
    }

    message.textContent = `${data.count} file${data.count === 1 ? '' : 's'} found`;
    message.className = 'lookup-message';
    data.results.forEach((file) => list.append(buildCard(file)));
}

/*
 * buildCard
 * Triggered: by renderResults, once per file in the JSON.
 * Changes:   nothing on its own; returns a new <li> for renderResults to insert.
 *            Uses textContent rather than innerHTML so text from the database
 *            is shown as text and can never run as code.
 */
function buildCard(file) {
    const card = document.createElement('li');
    card.className = 'lookup-card';

    const title = document.createElement('a');
    title.href = file.detail_url;
    title.textContent = `${file.claim_number} - ${file.vehicle}`;
    title.className = 'lookup-title';
    card.append(title);

    if (file.is_priority) {
        const badge = document.createElement('span');
        badge.className = 'badge';
        badge.textContent = 'PRIORITY';
        card.append(' ', badge);
    }

    const value = file.top_market_value === null
        ? 'no valuations yet'
        : `top market value $${file.top_market_value.toLocaleString('en-US')}`;
    const meta = document.createElement('p');
    meta.className = 'lookup-meta';
    meta.textContent = `${file.status} | assigned ${file.date_assigned} | `
        + `${file.valuation_count} valuation${file.valuation_count === 1 ? '' : 's'}, ${value}`;
    card.append(meta);

    if (file.tags.length > 0) {
        const tagRow = document.createElement('p');
        file.tags.forEach((name) => {
            const tag = document.createElement('span');
            tag.className = 'tag';
            tag.textContent = name;
            tagRow.append(tag);
        });
        card.append(tagRow);
    }

    return card;
}

/*
 * showError
 * Triggered: by runSearch's .catch() when the server is down, the URL is wrong,
 *            the server answers with an error, or the JSON can't be read.
 * Changes:   clears the results and shows a plain-English message in red,
 *            with the technical details in the console for debugging.
 */
function showError(error) {
    const message = document.querySelector('#lookup-message');
    const list = document.querySelector('#lookup-results');
    list.classList.remove('is-loading');
    list.replaceChildren();

    let reason;   // `let` because which sentence fits depends on the kind of failure
    if (error instanceof TypeError) {
        reason = "The server couldn't be reached. Check that it's running and try again.";
    } else if (error instanceof SyntaxError) {
        reason = "The server's answer wasn't valid JSON.";
    } else {
        reason = error.message;   // the HTTP status message built in runSearch
    }

    message.textContent = `Couldn't load appraisal files. ${reason}`;
    message.className = 'lookup-message is-error';
    console.error('Live Lookup request failed:', error);
}

/*
 * saveLastSearch
 * Triggered: by runSearch every time a search is sent.
 * Changes:   nothing on the page; writes {q, status} to localStorage so the
 *            same search comes back after a reload.
 */
function saveLastSearch(q, status) {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ q, status }));
    } catch (error) {
        // Private windows and blocked storage throw; the page still works without it
    }
}

/*
 * loadLastSearch
 * Triggered: by setUpLookup when the page loads.
 * Changes:   nothing on the page; returns the saved {q, status}, or empty
 *            values if nothing was saved or storage is unavailable.
 */
function loadLastSearch() {
    try {
        const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
        if (saved && typeof saved.q === 'string' && typeof saved.status === 'string') {
            return saved;
        }
    } catch (error) {
        // Missing, unreadable or blocked storage: start with an empty search
    }
    return { q: '', status: '' };
}

setUpLookup();
