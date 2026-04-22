(function() {
    const wsUrlInput = document.getElementById('ws-url');
    const connectBtn = document.getElementById('connect-btn');
    const clearBtn = document.getElementById('clear-btn');
    const statusSpan = document.getElementById('connection-status');
    const frameCountSpan = document.getElementById('frame-count');
    const tableBody = document.querySelector('#frames-table tbody');
    const chartCanvas = document.getElementById('signal-chart');
    const chartIdInput = document.getElementById('chart-id');
    const chartByteInput = document.getElementById('chart-byte');
    const chartUpdateBtn = document.getElementById('chart-update');

    let ws = null;
    let frameCounter = 0;
    const maxTableRows = 50;
    let chartData = [];
    const maxChartPoints = 100;

    function updateStatus(text, connected) {
        statusSpan.textContent = text;
        statusSpan.style.color = connected ? 'green' : 'red';
    }

    function addFrameToTable(timestamp, id, dataHex, decoded) {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${timestamp}</td>
            <td>${id}</td>
            <td>${dataHex}</td>
            <td>${decoded || ''}</td>
        `;
        tableBody.prepend(row);
        while (tableBody.children.length > maxTableRows) {
            tableBody.removeChild(tableBody.lastChild);
        }
        frameCounter++;
        frameCountSpan.textContent = `Ramki: ${frameCounter}`;
    }

    function clearTable() {
        tableBody.innerHTML = '';
        frameCounter = 0;
        frameCountSpan.textContent = `Ramki: 0`;
    }

    function connectWebSocket() {
        if (ws) {
            ws.close();
        }
        const url = wsUrlInput.value.trim();
        if (!url) {
            alert('Podaj adres WebSocket');
            return;
        }
        updateStatus('Łączenie...', false);
        ws = new WebSocket(url);

        ws.onopen = () => {
            updateStatus('Połączono', true);
            connectBtn.textContent = 'Rozłącz';
        };

        ws.onmessage = (event) => {
            try {
                const frame = JSON.parse(event.data);
                const id = frame.id || '?';
                const data = frame.data || [];
                const timestamp = frame.timestamp
                    ? new Date(frame.timestamp * 1000).toLocaleTimeString()
                    : new Date().toLocaleTimeString();
                const hexData = data.map(b => b.toString(16).padStart(2, '0')).join(' ');

                let decodedStr = '';
                if (frame.decoded) {
                    decodedStr = Object.entries(frame.decoded)
                        .map(([k, v]) => `${k}=${v.toFixed(2)}`)
                        .join(', ');
                }

                addFrameToTable(timestamp, id, hexData, decodedStr);

                // Aktualizuj wykres jeśli ID i bajt pasują
                const chartId = chartIdInput.value.trim();
                const byteIdx = parseInt(chartByteInput.value);
                if (id.toUpperCase() === chartId.toUpperCase() && byteIdx < data.length) {
                    chartData.push(data[byteIdx]);
                    if (chartData.length > maxChartPoints) {
                        chartData.shift();
                    }
                    drawChart();
                }
            } catch (e) {
                console.error('Błąd parsowania ramki:', e);
            }
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            updateStatus('Błąd', false);
        };

        ws.onclose = () => {
            updateStatus('Rozłączony', false);
            connectBtn.textContent = 'Połącz';
            ws = null;
        };
    }

    function drawChart() {
        const ctx = chartCanvas.getContext('2d');
        const w = chartCanvas.width;
        const h = chartCanvas.height;
        ctx.clearRect(0, 0, w, h);
        if (chartData.length < 2) return;

        const minVal = Math.min(...chartData);
        const maxVal = Math.max(...chartData);
        const range = maxVal - minVal || 1;

        ctx.beginPath();
        ctx.strokeStyle = '#1a73e8';
        ctx.lineWidth = 2;
        chartData.forEach((val, i) => {
            const x = (i / (chartData.length - 1)) * w;
            const y = h - ((val - minVal) / range) * (h - 20) - 10;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.stroke();

        // Osie
        ctx.fillStyle = '#666';
        ctx.font = '10px Arial';
        ctx.fillText(`Min: ${minVal}`, 5, h - 5);
        ctx.fillText(`Max: ${maxVal}`, w - 40, 15);
    }

    connectBtn.addEventListener('click', () => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.close();
        } else {
            connectWebSocket();
        }
    });

    clearBtn.addEventListener('click', clearTable);

    chartUpdateBtn.addEventListener('click', () => {
        chartData = [];
        drawChart();
    });

    // Inicjalne połączenie
    // connectWebSocket();
})();
