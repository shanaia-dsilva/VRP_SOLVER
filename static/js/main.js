let currentData = null;
let currentResults = null;

document.addEventListener('DOMContentLoaded', () => {
    taskId = generateUUID(); 
    setupFileUpload();
    setupDragDrop();
    initializeSmartPaste();
    setupResetButton();
    document.getElementById('process-data-btn').addEventListener('click', processPastedData);
    const modal = document.getElementById('progressModal');
    modal.classList.add('hidden');    
    modal.classList.remove('show');   
    updateProgress(0, '');  
});

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
    formData.append('task_id', taskId); 

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

// calculating distances
async function calculateDistances() {
    if (!currentData) return showStatus('No data loaded.', 'error');

    const modal = document.getElementById('progressModal');
    modal.classList.remove('hidden');
    modal.classList.add('show');

    const taskId = generateUUID();
    
    pollProgress(taskId);

    const payload = {
        task_id: taskId,
        data: currentData.map(row => ({
            'Vehicle Number': row[0],
            'Institute': row[1],
            'Category': row[2],
            'Route Number': row[3],
            'Driver Employee ID': row[4],
            'Licensed Experience (years)': row[5],
            'Driver pt Latitude': row[6],
            'Driver pt Longitude': row[7],
            'Driver pt Name': row[8],
            '1st Pickup pt Latitude': row[9],
            '1st Pickup pt Longitude': row[10],
            '1st Pickup pt Name': row[11]
        }))
    };

    try {
        const res = await fetch('/calculate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();

        if (data.success) {
            currentResults = data.results;
            showResults(data);
            updateProgress(100, 'Completed!');
            showStatus('Distance calculation complete.', 'success');
        } else {
            showStatus(data.error, 'error');
        }
    } catch (err) {
        console.error('Distance calculation error:', err);
        showStatus('Error during distance calculation.', 'error');
    } finally {
        setTimeout(() => {
            modal.classList.remove('show');
            modal.classList.add('hidden');
            updateProgress(0, '');
        }, 1500);
    }
}

let currentPollInterval = null;

let driverList = []; 
let pickupList = [];   


async function generateDistanceMatrix() {
    const payload = {
        driver_data: driverList,
        pickup_data: pickupList
    };

    const res = await fetch('/generate_matrix', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    const data = await res.json();
    return data.matrix; 
}
async function optimizeAssignments(matrix) {
    const payload = {
        driver_data: driverList,
        pickup_data: pickupList,
        distance_matrix: matrix
    };

    const res = await fetch('/optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    const data = await res.json();

    if (data.success) {
        showOptimizedResults(data.assignments);
        updateInsightsDashboard(data.insights);
        showSwapChains(data.chains);
    } else {
        showStatus(data.error || 'Optimization failed.', 'error');
    }
}
document.getElementById('run-optimization-btn').addEventListener('click', async () => {
    const matrix = await generateDistanceMatrix();
    await optimizeAssignments(matrix);
});
function exportOptimizedResults(data) {
    const url = `/export/optimized?data=${encodeURIComponent(JSON.stringify(data))}`;
    const link = document.createElement('a');
    link.href = url;
    link.download = 'optimized_assignments.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}
function showOptimizedResults(assignments) {
    const section = document.getElementById('results-section');
    const table = document.getElementById('results-table');
    const summary = document.getElementById('results-summary');

    table.innerHTML = '';
    section.style.display = 'block';

    const columns = ['From Bus', 'To Bus', 'Dead KM'];
    
    // Summary box
    summary.innerHTML = `<strong>Total Assignments:</strong> ${assignments.length}`;

    const thead = document.createElement('thead');
    const headRow = document.createElement('tr');
    columns.forEach(col => {
        const th = document.createElement('th');
        th.textContent = col;
        headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    assignments.forEach(row => {
        const tr = document.createElement('tr');
        columns.forEach(col => {
            const td = document.createElement('td');
            td.textContent = row[col] ?? 'N/A';
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);
}
function updateInsightsDashboard(insights) {
    document.getElementById('total-projects-num').textContent = insights.original_dead_km ?? '—';
    document.getElementById('routes-num').textContent = insights.total_dead_km.toFixed(2);
    document.getElementById('savings-num').textContent = insights.total_minimized?.toFixed(2) ?? '—';
    document.getElementById('routes-swapped').textContent = insights.total_swaps;

    document.getElementById('inter-swaps').textContent = insights.inter_institute ?? 0;
    document.getElementById('intra-swaps').textContent = insights.intra_institute ?? 0;
}
function showSwapChains(chains) {
    const section = document.getElementById('results-summary');
    const chainHTML = chains.map(chain => {
        return `<li>🔄 ${chain.join(' → ')}</li>`;
    }).join('');

    section.innerHTML += `
        <strong>Swap Chains:</strong>
        <ul>${chainHTML}</ul>
    `;
}
document.getElementById('download-csv').addEventListener('click', () => {
    if (!currentResults) return;
    const url = `/export/optimized?data=${encodeURIComponent(JSON.stringify(currentResults))}`;
    const link = document.createElement('a');
    link.href = url;
    link.download = 'optimized_assignments.csv';
    link.click();
});
document.getElementById('run-optimization-btn').addEventListener('click', async () => {
    const matrix = await generateDistanceMatrix(); // assumes you have this function
    const payload = {
        driver_data: driverList,
        pickup_data: pickupList,
        distance_matrix: matrix
    };

    const res = await fetch('/optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    const data = await res.json();

    if (data.success) {
        currentResults = data.assignments;
        showOptimizedResults(data.assignments);
        updateInsightsDashboard(data.insights);
        showSwapChains(data.chains);
        document.getElementById('download-csv').style.display = 'inline-block';
        document.getElementById('download-xlsx').style.display = 'inline-block';
    } else {
        showStatus(data.error || 'Optimization failed.', 'error');
    }
});

function pollProgress(taskId) {
    if (currentPollInterval) {
        console.log('Clearing old polling loop');
        clearInterval(currentPollInterval);
    }

    currentPollInterval = setInterval(async () => {
        try {
            const res = await fetch(`/progress/${taskId}`);
            const data = await res.json();

            if (data.percent != null) {
                updateProgress(data.percent, data.message || `${data.percent}% complete`);
            }

            if (data.percent >= 100) {
                clearInterval(currentPollInterval);
                currentPollInterval = null;
            }
        } catch (err) {
            console.warn('Progress polling error:', err);
            clearInterval(currentPollInterval);
            currentPollInterval = null;
        }
    }, 1000);
}

// =======================
// drag dropp
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
            let lines = pastedText.trim().split('\n').map(line => line.split('\t'));

            if (lines.every(cells => cells.length === 1)) {
                lines = pastedText.trim().split('\n').map(line => line.trim().split(/\s{2,}|\s*\|\s*/));
            }


            const isHeaderRow = lines[0].some(cell =>
                /vehicle|institute|lat|lon/i.test(cell)
            );
            const dataRows = isHeaderRow ? lines.slice(1) : lines;

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


// =======================preview
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
// UUID  genr
function generateUUID() {
    return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
        (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
}

// =======================

// ==========
function showResults(data) {
    const table = document.getElementById('results-table');
    const section = document.getElementById('results-section');
    const summaryBox = document.getElementById('results-summary');

    table.innerHTML = '';

    const columns = [
        'Vehicle Number', 'Institute',
        'Driver pt Latitude','Driver pt Longitude',
        '1st Pickup pt Latitude','1st Pickup pt Longitude',
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

// document.getElementById('progressModal').classList.add('show');

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