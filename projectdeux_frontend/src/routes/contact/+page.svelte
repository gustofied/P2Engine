<script>
  import { onMount } from 'svelte';
  import Chart from 'chart.js/auto';

  // Navigation state
  let activeSection = 'dashboard'; // Default section

  function setSection(section) {
    activeSection = section;
  }

  // Chart References
  let networkTPSCanvas;
  let solPriceCanvas;
  let clientDistCanvas;
  let nodeVersionCanvas;

  // Chart Data
  const networkTPSData = {
    labels: ['Time 1', 'Time 2', 'Time 3', 'Time 4', 'Time 5'],
    datasets: [{ label: 'TPS', data: [800, 900, 1000, 950, 850], backgroundColor: '#FF6200' }],
  };
  const solPriceData = {
    labels: ['8:00 PM', '9:00 PM', '10:00 PM', '11:00 PM', '12:00 AM'],
    datasets: [{ label: 'SOL Price', data: [122.1, 122.15, 122.2, 122.25, 122.3], borderColor: '#FF6200', fill: false }],
  };
  const clientDistData = {
    labels: ['Agave', 'Jito', 'Firedancer'],
    datasets: [{ label: 'Distribution', data: [100, 0, 0], backgroundColor: ['#FF6200', '#A0A0A0', '#A0A0A0'] }],
  };
  const nodeVersionData = {
    labels: ['Jito 2.1.14', 'Agave 2.1.14'],
    datasets: [{ data: [81, 19], backgroundColor: ['#FF6200', '#A0A0A0'] }],
  };

  // Chart Options
  const chartOptions = {
    scales: { y: { beginAtZero: true, ticks: { color: '#FFFFFF' } }, x: { ticks: { color: '#FFFFFF' } } },
    plugins: { legend: { display: false } },
  };
  const clientDistOptions = { ...chartOptions, indexAxis: 'y' };
  const nodeVersionOptions = { plugins: { legend: { display: true, position: 'bottom', labels: { color: '#FFFFFF' } } } };

  // Initialize Charts on Mount
  onMount(() => {
    // Network TPS (Bar Chart)
    new Chart(networkTPSCanvas, {
      type: 'bar',
      data: networkTPSData,
      options: chartOptions,
    });

    // SOL Price (Line Chart)
    new Chart(solPriceCanvas, {
      type: 'line',
      data: solPriceData,
      options: chartOptions,
    });

    // Client Distribution (Horizontal Bar Chart)
    new Chart(clientDistCanvas, {
      type: 'bar',
      data: clientDistData,
      options: clientDistOptions,
    });

    // Node Versions (Doughnut Chart)
    new Chart(nodeVersionCanvas, {
      type: 'doughnut',
      data: nodeVersionData,
      options: nodeVersionOptions,
    });
  });
</script>

<svelte:head>
  <title>Solana Dashboard</title>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap">
</svelte:head>

<div class="page-wrapper">
  <!-- Right Sidebar with Background Image -->
  <div class="sidebar">
    <div class="sidebar-text">Solana</div>
  </div>

  <!-- Navigation Buttons (Left of Sidebar, Vertical) -->
  <div class="nav-buttons">
    <a href="/" class="nav-button">Back Home</a>
    <button class:active={activeSection === 'dashboard'} on:click={() => setSection('dashboard')}>Dashboard</button>
    <button class:active={activeSection === 'validators'} on:click={() => setSection('validators')}>Validators</button>
    <button class:active={activeSection === 'stats'} on:click={() => setSection('stats')}>Stats</button>
  </div>

  <!-- Content Area -->
  <div class="content-area">
    {#if activeSection === 'dashboard'}
      <div class="content fade-in">
        <h2>Solana Dashboard</h2>
        <div class="grid">
          <!-- Progress -->
          <div class="card">
            <h3>EPOCH 578</h3>
            <div class="progress-bar">
              <div class="progress" style="width: 28.8%;"></div>
            </div>
            <p>28.8%</p>
            <p>13 d elapsed</p>
            <p>Start: May 18, 2023, 05:39 AM GMT+4</p>
            <p>End: May 31, 2023, 05:39 AM GMT+4</p>
            <p>Id: 29 62N</p>
          </div>
          <!-- Slot Info -->
          <div class="card">
            <h3>Slot Information</h3>
            <p>Slot: 327,406,000</p>
            <p>Block Time: 0.4s</p>
            <p>Epoch Time: 432,000</p>
            <p>Epoch Progress: 123,434</p>
          </div>
          <!-- Epoch Stats -->
          <div class="card">
            <h3>Epoch Stats</h3>
            <p>Epoch Fee: 0.000</p>
            <p>Epoch Time: 432,000</p>
            <p>Slot Time: 0.4s</p>
          </div>
          <!-- Network TPS -->
          <div class="card">
            <h3>Network TPS</h3>
            <p>T1: True TPS</p>
            <canvas bind:this={networkTPSCanvas}></canvas>
          </div>
          <!-- SOL Price -->
          <div class="card">
            <h3>SOL Price: <span class="text-orange">$122.07</span></h3>
            <canvas bind:this={solPriceCanvas}></canvas>
          </div>
          <!-- Validators -->
          <div class="card">
            <h3>Validators: <span class="text-orange">1,504</span></h3>
            <p>20 validators (33% of stake)</p>
          </div>
          <!-- Client Distribution -->
          <div class="card">
            <h3>Client Distribution</h3>
            <canvas bind:this={clientDistCanvas}></canvas>
          </div>
          <!-- Node Versions -->
          <div class="card">
            <h3>Node Versions</h3>
            <canvas bind:this={nodeVersionCanvas}></canvas>
          </div>
        </div>
      </div>
    {:else if activeSection === 'validators'}
      <div class="content fade-in">
        <h2>Active Validators</h2>
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Validator</th>
              <th>Active Stake (SOL)</th>
              <th>Stake Weight</th>
              <th>Commission</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>1</td>
              <td>mSOL</td>
              <td>13,214,307.009</td>
              <td>3.47%</td>
              <td>0%</td>
            </tr>
            <tr>
              <td>2</td>
              <td>Galaxy</td>
              <td>10,804,102.008</td>
              <td>2.84%</td>
              <td>0%</td>
            </tr>
          </tbody>
        </table>
      </div>
    {:else if activeSection === 'stats'}
      <div class="content fade-in">
        <h2>Network Stats</h2>
        <p>[Insert additional stats here]</p>
      </div>
    {/if}
  </div>
</div>

<style>
  :global(html),
  :global(body) {
    margin: 0;
    padding: 0;
    height: 100%;
    background: #000000;
    font-family: 'Roboto', sans-serif;
  }

  .page-wrapper {
    width: 100%;
    height: 100vh;
    position: relative;
  }

  .sidebar {
    position: fixed;
    right: 10%;
    top: 0;
    bottom: 0;
    width: 15%;
    background: linear-gradient(to bottom, #1C2526, #0A0F11);
    display: flex;
    align-items: center;
    justify-content: center;
    border-left: 2px solid #FF6200;
    box-shadow: -2px 0 10px rgba(0, 0, 0, 0.5);
    z-index: 10;
  }

  .sidebar-text {
    writing-mode: vertical-rl;
    text-orientation: mixed;
    font-size: 40px;
    color: #FFFFFF;
    transform: rotate(180deg);
    text-transform: uppercase;
    letter-spacing: 2px;
    text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.6);
  }

  .nav-buttons {
    position: fixed;
    right: 25%;
    top: 40px;
    display: flex;
    flex-direction: column;
    gap: 20px;
    width: 200px;
    z-index: 12;
  }

  .nav-buttons a.nav-button,
  .nav-buttons button {
    padding: 14px 28px;
    font-size: 20px;
    color: #FFFFFF;
    background: linear-gradient(135deg, #1C2526, #0A0F11);
    border: 2px solid #FF6200;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    text-decoration: none;
    cursor: pointer;
    transition: background 0.3s ease, transform 0.3s ease;
    text-align: left;
    position: relative;
  }

  .nav-buttons button.active {
    background: linear-gradient(135deg, #FF6200, #CC4D00);
    transform: scale(1.05);
  }

  .nav-buttons a.nav-button:hover,
  .nav-buttons button:hover:not(.active) {
    background: linear-gradient(135deg, #CC4D00, #FF6200);
    transform: translateX(-3px);
  }

  .nav-buttons a.nav-button:not(:last-child)::after,
  .nav-buttons button:not(:last-child)::after {
    content: '····················';
    position: absolute;
    bottom: -10px;
    left: 28px;
    color: #FF6200;
    font-size: 12px;
    letter-spacing: 2px;
  }

  .content-area {
    position: absolute;
    left: 0;
    top: 40px;
    right: 45%;
    bottom: 0;
    padding: 30px 50px;
    overflow-y: auto;
    background: #1C2526;
    z-index: 5;
  }

  .content {
    color: #FFFFFF;
  }

  .content h2 {
    font-size: 32px;
    letter-spacing: 1.5px;
    margin: 0 0 25px 0;
    color: #FF6200;
  }

  .content h3 {
    font-size: 20px;
    margin-bottom: 10px;
    color: #FFFFFF;
  }

  .content p {
    font-size: 16px;
    line-height: 1.6;
    margin: 5px 0;
  }

  .text-orange {
    color: #FF6200;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 20px;
  }

  .card {
    background: #0A0F11;
    padding: 20px;
    border-radius: 8px;
    border: 1px solid #FF6200;
  }

  .progress-bar {
    width: 100%;
    background: #2D3748;
    border-radius: 5px;
    height: 15px;
    margin: 10px 0;
  }

  .progress {
    height: 100%;
    background: #FF6200;
    border-radius: 5px;
  }

  canvas {
    max-width: 100%;
    height: 200px;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
  }

  th, td {
    padding: 10px;
    border-bottom: 1px solid #FF6200;
  }

  th {
    text-align: left;
    color: #A0A0A0;
  }

  td {
    color: #FFFFFF;
  }

  .fade-in {
    animation: fadeIn 0.5s ease-in;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
</style>