
let currentData = null;
let currentResults = null;

document.addEventListener('DOMContentLoaded', () => {
    setupFileUpload();
    setupDragDrop();
    initializeSmartPaste();
    setupResetButton();
    document.getElementById('process-data-btn').addEventListener('click', processPastedData);
});

// =======================
// File Upload

function setupFileUpload() {
    const form = document.getElementById('csv-form');
    const fileInput = document.getElementById('file-input');

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        uploadCSV();
    });

    fileInput.addEventListener('change', () => {
        showStatus('File selected. Click "Upload CSV File" to continue.', 'info');
    });
}

function uploadCSV() {
    const file = document.getElementById('file-input').files[0];
    if (!file) return showStatus('Please select a file.', 'error');
    if (!file.name.toLowerCase().endsWith('.csv')) return showStatus('Only CSV files are supported.', 'error');

    const formData = new FormData();
    formData.append('file', file);

    showStatus('Uploading CSV...', 'info');

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                currentData = data.full_data;
                showPreview(data.preview);
                showStatus(`File uploaded successfully! ${data.row_count} rows loaded.`, 'success');
            } else {
                showStatus(data.error, 'error');
            }
        })
        .catch(err => {
            console.error('Upload Error:', err);
            showStatus('Error uploading file.', 'error');
        });
}

// =======================
// Drag & Drop
function setupDragDrop() {
    const dragArea = document.getElementById('drag-area');

    dragArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        dragArea.classList.add('hover');
    });

    dragArea.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dragArea.classList.remove('hover');
    });

    dragArea.addEventListener('drop', (e) => {
        e.preventDefault();
        dragArea.classList.remove('hover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            const fileInput = document.getElementById('file-input');
            fileInput.files = files;
            showStatus('File dropped. Click "Upload CSV File" to continue.', 'info');
        }
    });
}

// =======================

function setActiveToggle(index) {
    document.querySelectorAll('.btn-toggle').forEach((btn, i) => {
        btn.classList.toggle('active', i === index);
    });
}

function switchToUpload() {
    document.getElementById('upload-section').style.display = 'block';
    document.getElementById('paste-section').style.display = 'none';
    setActiveToggle(0);
}

function switchToPaste() {
    document.getElementById('upload-section').style.display = 'none';
    document.getElementById('paste-section').style.display = 'block';
    setActiveToggle(1);
}

const pasteFieldIds = [
    'vehicle-number', 'institute',
    'point1-lat', 'point1-lon',
    'point2-lat', 'point2-lon'
];

function setupPasteFields() {
    const mainField = document.getElementById(pasteFieldIds[0]);

    mainField.addEventListener('paste', (e) => {
        const text = (e.clipboardData || window.clipboardData).getData('text');
        if (!text.includes('\t')) return;

        e.preventDefault();

        const rows = text.trim().split('\n').map(row => row.split('\t'));
        const isHeaderRow = rows[0].some(cell => /vehicle|institute|lat|lon/i.test(cell));
        const dataRows = isHeaderRow ? rows.slice(1) : rows;

        const columns = Array.from({ length: pasteFieldIds.length }, (_, i) =>
            dataRows.map(row => row[i] || '').join('\n')
        );

        pasteFieldIds.forEach((id, i) => {
            document.getElementById(id).value = columns[i] || '';
        });

        showStatus('Data pasted. Click "Process Data" to continue.', 'info');
    });
}

document.getElementById('process-data-btn').addEventListener('click', processPastedData);

function initializeSmartPaste() {
    const allPasteFields = [
        'vehicle-number',
        'institute',
        'point1-lat',
        'point1-lon',
        'point2-lat',
        'point2-lon'
    ];

    allPasteFields.forEach((id, startIndex) => {
        const field = document.getElementById(id);

        field.addEventListener('paste', function (e) {
            const pastedText = (e.clipboardData || window.clipboardData).getData('text');
            if (!pastedText.includes('\t')) return;

            e.preventDefault();

            const lines = pastedText.trim().split('\n').map(line => line.split('\t'));

            // Check for headers in first row and skip
            const isHeaderRow = lines[0].some(cell =>
                /vehicle|institute|lat|lon/i.test(cell)
            );
            const dataRows = isHeaderRow ? lines.slice(1) : lines;

            // Fill starting from the currently focused field
            dataRows.forEach((row, rowIndex) => {
                row.forEach((cell, offset) => {
                    const colIndex = startIndex + offset;
                    if (colIndex < allPasteFields.length) {
                        const targetField = document.getElementById(allPasteFields[colIndex]);
                        const lines = targetField.value.split('\n');
                        lines[rowIndex] = cell;
                        targetField.value = lines.join('\n');
                    }
                });
            });

            showStatus('Data pasted. Click "Process Data" to continue.', 'info');
        });
    });
}

// =======================
function processPastedData() {
    const rowCount = document.getElementById('vehicle-number').value.trim().split('\n').length;
    const rows = [];

    for (let i = 0; i < rowCount; i++) {
        const row = pasteFieldIds.map(id =>
            (document.getElementById(id).value.split('\n')[i] || '').trim()
        );
        rows.push(row.join('\t'));
    }

    const headers = [
        'Vehicle Number', 'Institute',
        'Point 1 latitude', 'Point 1 longitude',
        'Point 2 latitude', 'Point 2 longitude'
    ];

    const payload = [headers.join('\t'), ...rows].join('\n');

    showStatus('Processing pasted data...', 'info');

    fetch('/process_paste', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: payload })
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                currentData = data.full_data;
                showPreview(data.preview);
                showStatus(`Pasted data processed. ${data.row_count} rows loaded.`, 'success');
            } else {
                showStatus(data.error, 'error');
            }
        })
        .catch(err => {
            console.error('Paste process error:', err);
            showStatus('Error processing pasted data.', 'error');
        });
}

// =======================
// Preview Table
// =======================
function showPreview(preview) {
    const table = document.getElementById('preview-table');
    const info = document.getElementById('preview-info');
    const section = document.getElementById('preview-section');

    table.innerHTML = '';

    const thead = document.createElement('thead');
    const headRow = document.createElement('tr');
    preview.columns.forEach(col => {
        const th = document.createElement('th');
        th.textContent = col;
        headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    preview.rows.forEach(row => {
        const tr = document.createElement('tr');
        row.forEach(cell => {
            const td = document.createElement('td');
            td.textContent = cell;
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);

    info.textContent = `(Showing ${preview.preview_rows} of ${preview.total_rows} rows)`;
    section.style.display = 'block';

    setTimeout(() => {
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
}

// =======================
// Distance Calculation
// =======================
function calculateDistances() {
    if (!currentData) return showStatus('No data loaded.', 'error');

    updateProgress(25, 'Sending data to server...');
    const columns = [
        'Vehicle Number', 'Institute',
        'Point 1 latitude', 'Point 1 longitude',
        'Point 2 latitude', 'Point 2 longitude',
        'Distance_km', 'Duration_minutes'
    ];
    const payload = {
    data: currentData.map(row => ({
        'Institute': row[1],
        'Vehicle Number': row[0],
        'Point 1 latitude': row[2],
        'Point 1 longitude': row[3],
        'Point 2 latitude': row[4],
        'Point 2 longitude': row[5]
    }))
};

    fetch('/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                currentResults = data.results;
                showResults(data);
                showStatus('Distance calculation complete.', 'success');
            } else {
                showStatus(data.error, 'error');
            }
        })
        .catch(err => {
            console.error('Distance calculation error:', err);
            showStatus('Error during distance calculation.', 'error');
        });
}

// =======================
// Show Results Table
// =======================
function showResults(data) {
    const table = document.getElementById('results-table');
    const section = document.getElementById('results-section');
    const summaryBox = document.getElementById('results-summary');

    table.innerHTML = '';

    const columns = [
        'Vehicle Number', 'Institute',
        'Point 1 latitude', 'Point 1 longitude',
        'Point 2 latitude', 'Point 2 longitude',
        'Distance_km', 'Duration_minutes'
    ];

    summaryBox.innerHTML = `
        <div class="summary-box">
            <strong>Calculation Summary:</strong><br>
            Total routes: ${data.summary.total_routes}<br>
            Successful: ${data.summary.successful_calculations}<br>
            Failed: ${data.summary.failed_calculations}
        </div>
    `;

    const thead = document.createElement('thead');
    const tr = document.createElement('tr');
    columns.forEach(col => {
        const th = document.createElement('th');
        th.textContent = col.replace(/_/g, ' ');
        tr.appendChild(th);
    });
    thead.appendChild(tr);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    data.results.forEach(row => {
        const tr = document.createElement('tr');
        columns.forEach(col => {
            const td = document.createElement('td');
            let val = row[col];

            if (col === 'Distance_km' && val != null) val = parseFloat(val).toFixed(3);
            if (col === 'Duration_minutes' && val != null) val = parseFloat(val).toFixed(1);

            td.textContent = val ?? 'N/A';
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);

    section.style.display = 'block';
    section.scrollIntoView({ behavior: 'smooth' });
}

// =======================
// Export CSV
// =======================
function exportResults() {
    if (!currentResults) return showStatus('No results to export.', 'error');

    const url = `/export/csv?data=${encodeURIComponent(JSON.stringify(currentResults))}`;
    const link = document.createElement('a');
    link.href = url;
    link.download = 'distance_results.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    showStatus('Results exported successfully!', 'success');
}

// =======================
function showStatus(message, type) {
    const statusBox = document.getElementById('status');
    statusBox.innerHTML = `<div class="status-${type}">${message}</div>`;
}

function updateProgress(percent, message) {
    const bar = document.getElementById('progress-bar');
    const text = document.getElementById('progress-text');
    bar.style.width = `${percent}%`;
    text.textContent = message;
}

function setupResetButton() {
    document.getElementById('reset-paste-btn').addEventListener('click', () => {
        const pasteFieldIds = [
            'vehicle-number',
            'institute',
            'point1-lat',
            'point1-lon',
            'point2-lat',
            'point2-lon'
        ];

        pasteFieldIds.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });

        showStatus('All pasted fields have been cleared.', 'info');
    });
}
