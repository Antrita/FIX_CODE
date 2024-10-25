// Fix_UI.js
document.addEventListener('DOMContentLoaded', function() {
    // State variables
    let marketData = null;
    let orderHistory = [];
    let makerOutput = [];
    let status = 'Disconnected';
    const symbol = 'USD/BRL';

    // Create UI elements
    const app = document.getElementById('root');
    app.innerHTML = `
        <div class="p-4 bg-gray-900 min-h-screen">
            <div class="mb-4 text-white">
                <h1 class="text-2xl font-bold mb-2">FIX Trading Interface</h1>
                <div id="status-indicator" class="inline-block px-3 py-1 rounded bg-red-500">
                    ${status}
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <!-- Client Section -->
                <div class="space-y-4">
                    <div class="p-4 bg-gray-800 text-white rounded-lg">
                        <h2 class="text-xl font-bold mb-4 flex items-center">
                            <span class="mr-2">📱</span> Client Terminal
                        </h2>
                        <form id="command-form" class="mb-4">
                            <input
                                type="text"
                                id="command-input"
                                placeholder="Enter command (e.g., buy USD/BRL 100)"
                                class="w-full p-2 bg-gray-700 rounded border border-gray-600 text-white"
                            />
                        </form>
                        <div id="order-history" class="bg-gray-900 p-2 rounded h-48 overflow-y-auto">
                        </div>
                    </div>



               <div class="p-4 bg-gray-800 text-white rounded-lg">
    <h2 class="text-xl font-bold mb-4">Market Maker Output</h2>
    <div id="maker-output" class="bg-gray-900 p-2 rounded h-96 overflow-y-auto font-mono text-sm">
    </div>
</div>

<!-- Market Data Section (moved under Market Maker) -->
<div class="p-4 bg-gray-800 text-white rounded-lg mt-4">
    <h2 class="text-xl font-bold mb-4">Market Data</h2>
    <div id="market-data" class="bg-gray-900 p-2 rounded h-48 overflow-y-auto font-mono text-xs">
    </div>
</div>
            </div>
        </div>
    `;

    // Get UI elements
    const statusIndicator = document.getElementById('status-indicator');
    const commandForm = document.getElementById('command-form');
    const commandInput = document.getElementById('command-input');
    const orderHistoryDiv = document.getElementById('order-history');
    const makerOutputDiv = document.getElementById('maker-output');
    const marketDataDiv = document.getElementById('market-data');

    // WebSocket connection
    const ws = new WebSocket(`ws://${window.location.host}/ws`);

    ws.onopen = () => {
        status = 'Connected';
        statusIndicator.textContent = status;
        statusIndicator.classList.remove('bg-red-500');
        statusIndicator.classList.add('bg-green-500');
    };

    ws.onclose = () => {
        status = 'Disconnected';
        statusIndicator.textContent = status;
        statusIndicator.classList.remove('bg-green-500');
        statusIndicator.classList.add('bg-red-500');
    };

    ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === 'market_data') {
        // Handle market data updates
        updateMarketData(data.data);
    } else if (data.type === 'maker_output') {
        // Handle market maker output
        makerOutput.push(data.message);
        updateMakerOutput(data.message);
    } else if (data.type === 'order_update') {
        // Handle order updates
        orderHistory.push(data.order);
        updateOrderHistory(data.order);
    }
};

    // Event handlers
    commandForm.onsubmit = (e) => {
        e.preventDefault();
        const command = commandInput.value;

        fetch('/api/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command })
        });

        commandInput.value = '';
    };

    function updateMarketData(data) {
    if (!data) return;

    // Create table if it doesn't exist
    if (!marketDataDiv.querySelector('table')) {
        const table = document.createElement('table');
        table.className = 'w-full';
        table.innerHTML = `
            <colgroup>
                <col class="w-24">
                <col>
            </colgroup>
        `;
        marketDataDiv.appendChild(table);
    }

    const table = marketDataDiv.querySelector('table');
    const row = document.createElement('tr');
    row.className = 'hover:bg-gray-800';

    // Add timestamp
    const timeCell = document.createElement('td');
    timeCell.className = 'text-gray-500 text-xs pr-4 align-top';
    timeCell.textContent = new Date().toLocaleTimeString();

    // Add data content with hover effect
    const dataCell = document.createElement('td');
    dataCell.className = 'text-xs relative group';
    dataCell.innerHTML = `
        <div class="truncate">${data}</div>
        <div class="hidden group-hover:block absolute left-0 top-0 bg-gray-700 p-2 rounded shadow-lg z-10 whitespace-pre-wrap">
            ${data}
        </div>
    `;

    row.appendChild(timeCell);
    row.appendChild(dataCell);
    table.appendChild(row);
    marketDataDiv.scrollTop = marketDataDiv.scrollHeight;
}


    function updateOrderHistory(order) {
    // Create table if it doesn't exist
    if (!orderHistoryDiv.querySelector('table')) {
        const table = document.createElement('table');
        table.className = 'w-full';
        table.innerHTML = `
            <colgroup>
                <col class="w-24">
                <col>
            </colgroup>
        `;
        orderHistoryDiv.appendChild(table);
    }

    const table = orderHistoryDiv.querySelector('table');
    const row = document.createElement('tr');
    row.className = 'hover:bg-gray-800';

    // Add time column
    const timeCell = document.createElement('td');
    timeCell.className = 'text-gray-500 text-sm pr-4 align-top';
    timeCell.textContent = new Date().toLocaleTimeString();

    // Add message column with hover effect
    const messageCell = document.createElement('td');
    messageCell.className = 'text-sm relative group';
    messageCell.innerHTML = `
        <div class="truncate">${order}</div>
        <div class="hidden group-hover:block absolute left-0 top-0 bg-gray-700 p-2 rounded shadow-lg z-10 whitespace-pre-wrap">
            ${order}
        </div>
    `;

    row.appendChild(timeCell);
    row.appendChild(messageCell);
    table.appendChild(row);
    orderHistoryDiv.scrollTop = orderHistoryDiv.scrollHeight;
}

function updateMakerOutput(message) {
    // Create table if it doesn't exist
    if (!makerOutputDiv.querySelector('table')) {
        const table = document.createElement('table');
        table.className = 'w-full';
        table.innerHTML = `
            <colgroup>
                <col class="w-24">
                <col>
            </colgroup>
        `;
        makerOutputDiv.appendChild(table);
    }

    const table = makerOutputDiv.querySelector('table');
    const row = document.createElement('tr');
    row.className = 'hover:bg-gray-800';

    // Add time column
    const timeCell = document.createElement('td');
    timeCell.className = 'text-gray-500 text-sm pr-4 align-top';
    timeCell.textContent = new Date().toLocaleTimeString();

    // Add message column with hover effect
    const messageCell = document.createElement('td');
    messageCell.className = 'text-sm relative group';
    messageCell.innerHTML = `
        <div class="truncate">${message}</div>
        <div class="hidden group-hover:block absolute left-0 top-0 bg-gray-700 p-2 rounded shadow-lg z-10 whitespace-pre-wrap">
            ${message}
        </div>
    `;

    row.appendChild(timeCell);
    row.appendChild(messageCell);
    table.appendChild(row);
    makerOutputDiv.scrollTop = makerOutputDiv.scrollHeight;
}
    function updateMakerOutput(message) {
        const div = document.createElement('div');
        div.className = 'whitespace-pre-wrap mb-1';
        div.textContent = message;
        makerOutputDiv.appendChild(div);
        makerOutputDiv.scrollTop = makerOutputDiv.scrollHeight;
    }
});