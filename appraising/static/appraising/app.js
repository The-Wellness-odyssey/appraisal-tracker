/*
 * Vehicle Appraisal Tracker - client-side interactivity
 *
 * Loaded from layout.html with `defer`, so it runs after the HTML has been
 * parsed and every element below already exists.
 *
 * Every feature here adds to a page that already works without JavaScript.
 * If this file fails to load: the list still shows every file, the valuation
 * notes are still visible, the form still submits to Django (which still
 * validates it), and the close button still closes the file.
 */

// ---------------------------------------------------------------------------
// 1. Live filter on the Active Appraisals list
// ---------------------------------------------------------------------------

/*
 * setUpListFilter
 * Triggered: once, when the script runs on the list page.
 * Changes:   creates a search box and a "Showing X of Y" counter above the list,
 *            and an empty-state row inside it. The box is created here, not in
 *            the template, so visitors without JavaScript never see a box that
 *            does nothing.
 */
function setUpListFilter() {
    const list = document.querySelector('#appraisal-list');
    if (!list) return;   // not on the list page

    // querySelectorAll (plural) is needed here because the filter has to test
    // every row in the list, not just the first one querySelector would return.
    const rows = list.querySelectorAll('.appraisal-row');
    if (rows.length === 0) return;

    // Build the filter box
    const wrapper = document.createElement('div');
    wrapper.className = 'filter-box';

    const input = document.createElement('input');
    input.type = 'search';
    input.id = 'live-filter';
    input.placeholder = 'Filter by claim, vehicle or status...';
    input.setAttribute('aria-label', 'Filter appraisals');

    const counter = document.createElement('p');
    counter.className = 'filter-count';
    counter.setAttribute('aria-live', 'polite');

    wrapper.append(input, counter);
    list.before(wrapper);

    // Empty-state row, shown only when nothing matches
    const noMatch = document.createElement('li');
    noMatch.className = 'no-match is-hidden';
    list.append(noMatch);

    input.addEventListener('input', () => applyFilter(input.value, rows, counter, noMatch));
    applyFilter('', rows, counter, noMatch);
}

/*
 * applyFilter
 * Triggered: every time the user types in (or clears) the filter box.
 * Changes:   adds .is-hidden to rows that do not contain the typed text and
 *            removes it from rows that do; updates the "Showing X of Y" counter;
 *            shows the "No files match" row when the count reaches zero.
 */
function applyFilter(text, rows, counter, noMatch) {
    const term = text.trim().toLowerCase();
    let shown = 0;   // `let` because it goes up as matching rows are found

    rows.forEach((row) => {
        const matches = row.dataset.search.toLowerCase().includes(term);
        row.classList.toggle('is-hidden', !matches);
        if (matches) shown += 1;
    });

    counter.textContent = `Showing ${shown} of ${rows.length} file${rows.length === 1 ? '' : 's'}`;
    noMatch.textContent = `No files match "${text.trim()}".`;
    noMatch.classList.toggle('is-hidden', shown > 0);
}

// ---------------------------------------------------------------------------
// 2. Show / hide valuation notes on the detail page
// ---------------------------------------------------------------------------

/*
 * setUpNotesToggles
 * Triggered: once, when the script runs on a detail page.
 * Changes:   collapses each valuation's notes and inserts a "Show notes" button
 *            next to it. Without JavaScript the notes simply stay visible.
 */
function setUpNotesToggles() {
    // Plural again: a file can have many valuations, and each needs its own button.
    const noteBlocks = document.querySelectorAll('.valuation-notes');

    noteBlocks.forEach((notes) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'toggle-notes';
        button.textContent = 'Show notes';
        button.setAttribute('aria-expanded', 'false');

        notes.classList.add('is-collapsed');
        notes.before(button);

        button.addEventListener('click', () => toggleNotes(button, notes));
    });
}

/*
 * toggleNotes
 * Triggered: clicking a "Show notes" / "Hide notes" button.
 * Changes:   flips .is-collapsed on that one valuation's notes and swaps the
 *            button label between "Show notes" and "Hide notes".
 */
function toggleNotes(button, notes) {
    const nowHidden = notes.classList.toggle('is-collapsed');
    button.textContent = nowHidden ? 'Show notes' : 'Hide notes';
    button.setAttribute('aria-expanded', String(!nowHidden));
}

// ---------------------------------------------------------------------------
// 3. Client-side validation on the Add Appraisal form
// ---------------------------------------------------------------------------

// These limits never change while the page is open: they mirror the
// max_length values on the AppraisalFile model, so `const` is correct.
const FIELD_RULES = [
    { id: 'id_claim_number', label: 'Claim number', maxLength: 50 },
    { id: 'id_vehicle_desc', label: 'Vehicle year/make/model', maxLength: 100 },
    { id: 'id_date_assigned', label: 'Date assigned' },
];

/*
 * setUpFormValidation
 * Triggered: once, when the script runs on the Add Appraisal page.
 * Changes:   switches off the browser's built-in bubbles (noValidate) so our
 *            inline messages are shown instead. Without JavaScript the browser
 *            bubbles and Django's own validation still run as before.
 */
function setUpFormValidation() {
    const form = document.querySelector('#appraisal-form');
    if (!form) return;

    form.noValidate = true;
    form.addEventListener('submit', (event) => validateForm(event, form));

    // Clear a field's warning as soon as the user starts fixing it
    FIELD_RULES.forEach((rule) => {
        const field = document.getElementById(rule.id);
        if (field) field.addEventListener('input', () => clearError(field));
    });
}

/*
 * validateForm
 * Triggered: pressing "Submit Appraisal".
 * Changes:   for each empty or too-long field, adds .has-error (red outline)
 *            and inserts a warning message under it, then cancels the submit.
 *            If everything passes, the form posts to Django as normal, and
 *            Django still runs its own checks (unique claim number, valid date).
 */
function validateForm(event, form) {
    let firstBadField = null;

    FIELD_RULES.forEach((rule) => {
        const field = document.getElementById(rule.id);
        if (!field) return;
        clearError(field);

        const value = field.value.trim();
        let message = '';
        if (value === '') {
            message = `${rule.label} is required.`;
        } else if (rule.maxLength && value.length > rule.maxLength) {
            message = `${rule.label} must be ${rule.maxLength} characters or fewer (currently ${value.length}).`;
        }

        if (message) {
            showError(field, message);
            if (!firstBadField) firstBadField = field;
        }
    });

    if (firstBadField) {
        event.preventDefault();
        firstBadField.focus();
    }
}

/*
 * showError
 * Triggered: by validateForm when a field fails.
 * Changes:   adds .has-error to the input and creates a <p class="field-error">
 *            right after it with the warning text.
 */
function showError(field, message) {
    field.classList.add('has-error');
    const warning = document.createElement('p');
    warning.className = 'field-error';
    warning.textContent = message;
    field.after(warning);
}

/*
 * clearError
 * Triggered: by validateForm before re-checking, and by typing in a field.
 * Changes:   removes .has-error from the input and removes its warning message
 *            from the page, if there is one.
 */
function clearError(field) {
    field.classList.remove('has-error');
    const next = field.nextElementSibling;
    if (next && next.classList.contains('field-error')) next.remove();
}

// ---------------------------------------------------------------------------
// 4. Confirm before closing a file
// ---------------------------------------------------------------------------

/*
 * setUpConfirmations
 * Triggered: once, when the script runs.
 * Changes:   nothing visible yet; listens for submit on any form marked
 *            data-confirm (currently "Mark File Closed").
 */
function setUpConfirmations() {
    // Plural so every form with data-confirm is covered, not only the first.
    const forms = document.querySelectorAll('form[data-confirm]');
    forms.forEach((form) => {
        form.addEventListener('submit', (event) => confirmSubmit(event, form));
    });
}

/*
 * confirmSubmit
 * Triggered: submitting a form marked data-confirm.
 * Changes:   shows a yes/no dialog with that form's message. "Cancel" stops the
 *            POST, so the file stays open; "OK" lets it through to Django.
 *            Without JavaScript the button closes the file directly.
 */
function confirmSubmit(event, form) {
    if (!window.confirm(form.dataset.confirm)) {
        event.preventDefault();
    }
}

// ---------------------------------------------------------------------------
// Start-up: each setUp function checks for its own elements and exits quietly
// on pages where they do not exist.
// ---------------------------------------------------------------------------
setUpListFilter();
setUpNotesToggles();
setUpFormValidation();
setUpConfirmations();
