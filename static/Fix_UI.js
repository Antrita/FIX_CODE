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
                        <h2 class="text-xl font-bold mb-4">Market Data</h2>
                        <div class="grid grid-cols-2 gap-4">
                            <div class="bg-gray-700 p-3 rounded">
                                <div class="text-green-400">Bid</div>
                                <div id="bid-price" class="text-2xl">---</div>
                            </div>
                            <div class="bg-gray-700 p-3 rounded">
                                <div class="text-red-400">Ask</div>
                                <div id="ask-price" class="text-2xl">---</div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Market Maker Section -->
                <div class="p-4 bg-gray-800 text-white rounded-lg">
                    <h2 class="text-xl font-bold mb-4">Market Maker Output</h2>
                    <div id="maker-output" class="bg-gray-900 p-2 rounded h-96 overflow-y-auto font-mono text-sm">
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
    const bidPrice = document.getElementById('bid-price');
    const askPrice = document.getElementById('ask-price');

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
            marketData = data.data;
            updateMarketData(data.data);
        } else if (data.type === 'maker_output') {
            makerOutput.push(data.message);
            updateMakerOutput(data.message);
        } else if (data.type === 'order_update') {
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

    // Update functions
    function updateMarketData(data) {
        if (data) {
            // Parse FIX message for bid/ask prices
            const message = data.toString();
            const bidMatch = message.match(/270=1.*?271=([\d.]+)/);
            const askMatch = message.match(/270=2.*?271=([\d.]+)/);

            if (bidMatch) bidPrice.textContent = bidMatch[1];
            if (askMatch) askPrice.textContent = askMatch[1];
        }
    }

    function updateOrderHistory(order) {
        const div = document.createElement('div');
        div.className = 'mb-2 text-sm';
        div.textContent = order;
        orderHistoryDiv.appendChild(div);
        orderHistoryDiv.scrollTop = orderHistoryDiv.scrollHeight;
    }

    function updateMakerOutput(message) {
        const div = document.createElement('div');
        div.className = 'whitespace-pre-wrap mb-1';
        div.textContent = message;
        makerOutputDiv.appendChild(div);
        makerOutputDiv.scrollTop = makerOutputDiv.scrollHeight;
    }
});