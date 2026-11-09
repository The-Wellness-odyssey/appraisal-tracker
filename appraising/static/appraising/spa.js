/*
 * Vehicle Appraisal Tracker - single-page Files section
 *
 * Three views, one page: the list (/files/?page=N), one file (/files/<id>/) and the
 * create form (/files/new/). Moving between them never reloads the page:
 *
 *   click a link  -> navigate()  -> history.pushState() changes the URL  -> render()
 *   Back/Forward  -> 'popstate' event fires, the URL is already changed  -> render()
 *   direct load   -> Django sends the same shell for every /files/ URL   -> render()
 *
 * render() always works from the URL alone, which is why all three paths end up
 * showing the same thing for the same address.
 *
 * Loaded on every page from layout.html; it only does anything when #files-app exists.
 */

(function () {
    const app = document.querySelector('#files-app');
    if (!app) return;   // not on a /files/ page

    // These never change while the page is open: they come from Django's {% url %} tags
    // in the shell, so the JavaScript never hard-codes an address the server could rename.
    const API = app.dataset.api;    // "/api/appraisals/"
    const BASE = app.dataset.base;  // "/files/"
    const PAGE_SIZE = 10;           // rows per page; Django does the slicing

    // querySelectorAll because there are four view sections and showView() has to
    // hide every one that isn't the target.
    const views = app.querySelectorAll('.spa-view');
    const status = app.querySelector('#spa-status');

    let latestRequest = 0;          // stops a slow old response overwriting a newer view
    let currentRoute = null;        // what render() last showed, for the Retry button
    let lastListUrl = BASE;         // so "Back to all files" returns to the same page number
    let firstRender = true;         // don't steal focus from the browser on the first load

    // The browser would try to restore scroll itself on Back, before our new content
    // exists. We save and restore it ourselves instead (see navigate() and onPopState()).
    history.scrollRestoration = 'manual';

    // -----------------------------------------------------------------------
    // Routing
    // -----------------------------------------------------------------------

    /*
     * parseRoute
     * Triggered: by render() every time the view has to change.
     * Changes:   nothing on the page; turns the current URL into a route object
     *            such as {name: 'detail', id: 7} or {name: 'list', page: 2}.
     */
    function parseRoute(loc) {
        const path = loc.pathname;
        if (path === BASE) {
            const page = parseInt(new URLSearchParams(loc.search).get('page'), 10);
            return { name: 'list', page: page > 0 ? page : 1 };
        }
        if (path === `${BASE}new/`) return { name: 'create' };
        const match = path.match(new RegExp(`^${BASE}(\\d+)/$`));
        if (match) return { name: 'detail', id: Number(match[1]) };
        return { name: 'missing' };
    }

    /*
     * navigate
     * Triggered: clicking any link marked data-spa-link, or saving a new file.
     * Changes:   remembers the current scroll position on the history entry we are
     *            leaving, pushes the new URL onto the history stack (or replaces the
     *            current entry), then renders the view for that URL.
     */
    function navigate(url, { replace = false } = {}) {
        const target = new URL(url, location.href);
        if (target.href === location.href) return;   // already here: don't add a duplicate entry

        history.replaceState({ ...history.state, scrollY: window.scrollY }, '');
        if (replace) {
            history.replaceState({ scrollY: 0 }, '', target.href);
        } else {
            history.pushState({ scrollY: 0 }, '', target.href);
        }
        render({ scrollY: 0 });
    }

    /*
     * onLinkClick
     * Triggered: any click anywhere on the page (one listener, delegated).
     * Changes:   if the click was on a data-spa-link, stops the browser loading a
     *            new page and calls navigate() instead. Ctrl/Cmd/Shift-clicks and
     *            middle clicks are left alone so "open in new tab" still works.
     */
    function onLinkClick(event) {
        const link = event.target.closest('a[data-spa-link]');
        if (!link || event.defaultPrevented || event.button !== 0
            || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
            return;
        }
        event.preventDefault();
        navigate(link.getAttribute('href'));
    }

    /*
     * onPopState
     * Triggered: the Back or Forward button (or history.back() in the console).
     *            By the time this fires the browser has already changed the URL,
     *            but nothing on the page has changed. That is our job.
     * Changes:   renders the view for the URL we've arrived at, then puts the scroll
     *            position back where it was when the user left that entry.
     */
    function onPopState(event) {
        const scrollY = event.state && typeof event.state.scrollY === 'number' ? event.state.scrollY : 0;
        render({ scrollY });
    }

    // -----------------------------------------------------------------------
    // Rendering
    // -----------------------------------------------------------------------

    /*
     * render
     * Triggered: navigate(), onPopState(), the first page load, and the Retry button.
     * Changes:   reads the URL, shows the loading state, fetches what that view needs
     *            from the JSON API, fills the view in, and switches to it.
     */
    function render({ scrollY = 0 } = {}) {
        const route = parseRoute(location);
        currentRoute = route;
        latestRequest += 1;
        const thisRequest = latestRequest;

        // Drop any errors left over from a create attempt before leaving the form
        if (route.name !== 'create') clearFormErrors();

        if (route.name === 'create') {
            showView('create', 'New Appraisal File', scrollY);
            return;
        }
        if (route.name === 'missing') {
            showMissing('There is no page at this address in the Files section.', scrollY);
            return;
        }

        const url = route.name === 'list'
            ? `${API}?limit=${PAGE_SIZE}&page=${route.page}`
            : `${API}${route.id}/`;

        showLoading(route.name === 'list' ? `Loading page ${route.page}...` : 'Loading file...');

        fetchJson(url)
            .then((data) => {
                if (thisRequest !== latestRequest) return;   // the user has already moved on
                if (route.name === 'list') {
                    fillList(data);
                    showView('list', `Appraisal Files, page ${data.page}`, scrollY);
                } else {
                    fillDetail(data);
                    showView('detail', `${data.claim_number} - ${data.vehicle}`, scrollY);
                }
            })
            .catch((error) => {
                if (thisRequest !== latestRequest) return;
                if (error.status === 404) {
                    showMissing(route.name === 'list'
                        ? `Page ${route.page} doesn't exist.`
                        : `File #${route.id} doesn't exist, or it was deleted.`, scrollY);
                } else {
                    showError(error);
                }
            });
    }

    /*
     * fetchJson
     * Triggered: by render().
     * Changes:   nothing on the page; returns a promise for the parsed JSON. A non-OK
     *            response becomes an error carrying its status, so render() can tell
     *            "not found" (404) apart from "the server is broken" (500).
     */
    function fetchJson(url) {
        return fetch(url, { headers: { Accept: 'application/json' } })
            .then((response) => {
                if (!response.ok) {
                    const error = new Error(`The server answered ${response.status} ${response.statusText}.`);
                    error.status = response.status;
                    throw error;
                }
                return response.json();
            });
    }

    /*
     * showView
     * Triggered: by render() once a view's content is ready.
     * Changes:   hides every other view, un-hides the target, then adds .is-active on
     *            the next frame so the CSS fade/slide transition plays. Updates the tab
     *            title, moves keyboard focus to the new heading, and restores scroll.
     */
    function showView(name, title, scrollY) {
        hideLoading();
        let target = null;

        views.forEach((view) => {
            if (view.dataset.view === name) {
                target = view;
            } else {
                view.classList.remove('is-active');
                view.hidden = true;   // hidden also takes it out of the Tab order
            }
        });

        if (target.hidden) {
            target.hidden = false;
            target.classList.remove('is-active');
            // Force the browser to apply the starting style before we add the class,
            // otherwise it skips straight to the end and there is no transition.
            void target.offsetWidth;
        }
        target.classList.add('is-active');

        document.title = `${title} | Vehicle Appraisal Tracker`;
        window.scrollTo(0, scrollY);

        // Screen readers and keyboard users start from the new heading, the same
        // place a normal page load would put them.
        if (!firstRender) target.querySelector('h1').focus({ preventScroll: true });
        firstRender = false;
    }

    /*
     * showLoading
     * Triggered: by render() just before a fetch is sent.
     * Changes:   shows the status bar with a message and adds .is-busy, which fades the
     *            view that is still on screen until the new data arrives.
     */
    function showLoading(message) {
        status.replaceChildren(message);
        status.className = 'spa-status is-loading';
        app.classList.add('is-busy');
        app.setAttribute('aria-busy', 'true');
    }

    /*
     * hideLoading
     * Triggered: by showView() and showError().
     * Changes:   hides the status bar and removes .is-busy.
     */
    function hideLoading() {
        status.className = 'spa-status is-hidden';
        status.replaceChildren();
        app.classList.remove('is-busy');
        app.removeAttribute('aria-busy');
    }

    /*
     * showError
     * Triggered: by render() when the server is down or answers with an error.
     * Changes:   shows a red message in the status bar with a real <button> that runs
     *            render() again for the same URL.
     */
    function showError(error) {
        hideLoading();
        const reason = error instanceof TypeError
            ? "The server couldn't be reached."
            : error.message;
        const retry = document.createElement('button');
        retry.type = 'button';
        retry.textContent = 'Try again';
        retry.addEventListener('click', () => render({ scrollY: window.scrollY }));
        status.replaceChildren(`Couldn't load this view. ${reason} `, retry);
        status.className = 'spa-status is-error';
        retry.focus();
        console.error('Files section request failed:', error, currentRoute);
    }

    /*
     * showMissing
     * Triggered: by render() for an unknown /files/ URL or a 404 from the API.
     * Changes:   fills in the "Not found" view and switches to it.
     */
    function showMissing(message, scrollY) {
        app.querySelector('#missing-message').textContent = message;
        showView('missing', 'Not found', scrollY);
    }

    /*
     * fillList
     * Triggered: by render() when a page of the list arrives.
     * Changes:   rebuilds the rows with createElement, updates "Showing 11-20 of 25",
     *            and points the Previous/Next links at the right ?page= URLs (hiding
     *            whichever one doesn't apply).
     */
    function fillList(data) {
        const rows = app.querySelector('#list-rows');
        rows.replaceChildren(...data.results.map(buildRow));

        const first = (data.page - 1) * data.query.limit + 1;
        const last = first + data.count - 1;
        app.querySelector('#list-summary').textContent = data.total === 0
            ? 'No appraisal files yet.'
            : `Showing ${first}-${last} of ${data.total} files`;

        const prev = app.querySelector('#pager-prev');
        const next = app.querySelector('#pager-next');
        prev.href = data.page - 1 === 1 ? BASE : `${BASE}?page=${data.page - 1}`;
        next.href = `${BASE}?page=${data.page + 1}`;
        prev.classList.toggle('is-hidden', !data.has_previous);
        next.classList.toggle('is-hidden', !data.has_next);
        app.querySelector('#pager-label').textContent = `Page ${data.page} of ${data.num_pages}`;

        lastListUrl = location.pathname + location.search;
    }

    /*
     * buildRow
     * Triggered: by fillList(), once per file.
     * Changes:   nothing on its own; returns a new <li> whose link is a real <a href>
     *            to /files/<id>/, so Tab, Enter and "open in new tab" all work.
     */
    function buildRow(file) {
        const row = document.createElement('li');
        row.className = 'spa-row';

        const link = document.createElement('a');
        link.href = file.spa_url;
        link.dataset.spaLink = '';
        link.className = 'spa-row-link';
        link.textContent = `${file.claim_number} - ${file.vehicle}`;
        row.append(link);

        if (file.is_priority) {
            const badge = document.createElement('span');
            badge.className = 'badge';
            badge.textContent = 'PRIORITY';
            row.append(' ', badge);
        }

        const meta = document.createElement('p');
        meta.className = 'spa-row-meta';
        meta.textContent = `${file.status} | assigned ${file.date_assigned}`
            + (file.tags.length ? ` | ${file.tags.join(', ')}` : '');
        row.append(meta);
        return row;
    }

    /*
     * fillDetail
     * Triggered: by render() when one file's JSON arrives.
     * Changes:   fills in the heading, the facts list and the valuations, and sets the
     *            back link to the list page the user came from.
     */
    function fillDetail(file) {
        app.querySelector('#detail-heading').textContent = `${file.claim_number} - ${file.vehicle}`;
        app.querySelector('#detail-back').href = lastListUrl;
        app.querySelector('#detail-classic').href = file.detail_url;

        const facts = [
            ['Status', file.status],
            ['Assigned', file.date_assigned],
            ['Priority', file.is_priority ? 'Yes' : 'No'],
            ['Tags', file.tags.length ? file.tags.join(', ') : 'None'],
        ];
        const dl = app.querySelector('#detail-facts');
        dl.replaceChildren();
        facts.forEach(([label, value]) => {
            const dt = document.createElement('dt');
            dt.textContent = label;
            const dd = document.createElement('dd');
            dd.textContent = value;
            dl.append(dt, dd);
        });

        const list = app.querySelector('#detail-valuations');
        list.replaceChildren();
        if (file.valuations.length === 0) {
            const empty = document.createElement('li');
            empty.textContent = 'No valuations recorded yet.';
            list.append(empty);
        }
        file.valuations.forEach((v) => {
            const item = document.createElement('li');
            item.textContent = `Market value $${v.market_value.toLocaleString('en-US')}, `
                + `diminished value $${v.diminished_value.toLocaleString('en-US')}`
                + (v.notes ? `. ${v.notes}` : '');
            list.append(item);
        });
    }

    // -----------------------------------------------------------------------
    // Create form
    // -----------------------------------------------------------------------

    /*
     * onCreateSubmit
     * Triggered: pressing "Save file" on the create view (after the browser's own
     *            required-field checks pass).
     * Changes:   posts the form to /api/appraisals/ with fetch() instead of loading a
     *            new page. On success it opens the new file's view; on a 400 it shows
     *            Django's field errors under each field.
     */
    function onCreateSubmit(event) {
        event.preventDefault();
        const form = event.target;
        const button = form.querySelector('#create-submit');
        clearFormErrors();
        button.disabled = true;
        button.textContent = 'Saving...';

        fetch(API, {
            method: 'POST',
            body: new FormData(form),
            headers: {
                Accept: 'application/json',
                // Django rejects a POST without the CSRF token; the shell's {% csrf_token %} provides it
                'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value,
            },
        })
            .then((response) => response.json().then((data) => ({ response, data })))
            .then(({ response, data }) => {
                if (response.status === 201) {
                    form.reset();
                    // replace, not push: Back from the new file should go to where the
                    // user was before the form, not to an empty form they already sent
                    navigate(data.spa_url, { replace: true });
                } else if (response.status === 400) {
                    showFormErrors(data.errors);
                } else {
                    throw new Error(`The server answered ${response.status}.`);
                }
            })
            .catch((error) => {
                showFormErrors({ __all__: [`Couldn't save the file. ${error instanceof TypeError ? "The server couldn't be reached." : error.message}`] });
            })
            .finally(() => {
                button.disabled = false;
                button.textContent = 'Save file';
            });
    }

    /*
     * showFormErrors
     * Triggered: by onCreateSubmit() when Django says the form is invalid.
     * Changes:   outlines each bad field with .has-error, inserts its message under it,
     *            and moves focus to the first bad field.
     */
    function showFormErrors(errors) {
        let firstBad = null;
        Object.entries(errors).forEach(([field, messages]) => {
            const input = app.querySelector(`#id_${field}`);
            if (!input) {
                const general = app.querySelector('#create-errors');
                general.textContent = messages.join(' ');
                general.classList.remove('is-hidden');
                return;
            }
            input.classList.add('has-error');
            const message = document.createElement('p');
            message.className = 'field-error spa-field-error';
            message.textContent = messages.join(' ');
            input.after(message);
            if (!firstBad) firstBad = input;
        });
        if (firstBad) firstBad.focus();
    }

    /*
     * clearFormErrors
     * Triggered: before each submit and whenever the user leaves the create view.
     * Changes:   removes every error message the form added and the red outlines.
     */
    function clearFormErrors() {
        app.querySelectorAll('.spa-field-error').forEach((el) => el.remove());
        app.querySelectorAll('#spa-create-form .has-error').forEach((el) => el.classList.remove('has-error'));
        app.querySelector('#create-errors').classList.add('is-hidden');
    }

    // -----------------------------------------------------------------------
    // Start-up
    // -----------------------------------------------------------------------
    document.addEventListener('click', onLinkClick);
    window.addEventListener('popstate', onPopState);
    app.querySelector('#spa-create-form').addEventListener('submit', onCreateSubmit);

    // Give the entry we landed on a state object too, so Back to it has a scroll value
    history.replaceState({ scrollY: 0 }, '');
    render();
})();
