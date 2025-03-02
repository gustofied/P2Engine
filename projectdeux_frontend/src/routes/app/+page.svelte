<script>
  import { goto } from '$app/navigation';
  import { onMount, afterUpdate } from 'svelte';
  import * as d3 from 'd3';

  let scenarioName = '';
  let htmlSummary = '';
  let isLoading = false;
  let errorMessage = '';
  let status = 'Ready';
  let scenarios = [];
  let activeTab = 'simulation';

  onMount(async () => {
    try {
      const response = await fetch('http://localhost:8001/list-scenarios');
      if (!response.ok) {
        throw new Error(`Failed to fetch scenarios: ${response.status}`);
      }
      const data = await response.json();
      scenarios = data.scenarios;
      if (scenarios.length > 0) {
        scenarioName = scenarios[0];
      }
    } catch (error) {
      errorMessage = `Error loading scenarios: ${error.message}`;
    }
  });

  afterUpdate(() => {
    if (htmlSummary) {
      const scripts = document.querySelectorAll('.playground-content script');
      scripts.forEach((script) => {
        const newScript = document.createElement('script');
        newScript.textContent = script.textContent;
        document.body.appendChild(newScript);
        document.body.removeChild(newScript);
      });
    }
  });

  async function runScenario() {
    if (!scenarioName) {
      errorMessage = 'Please select a scenario.';
      return;
    }
    isLoading = true;
    errorMessage = '';
    status = 'Loading';
    try {
      const response = await fetch('http://localhost:8001/run-scenario', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ scenario_name: scenarioName }),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      htmlSummary = data.html_summary;
      status = 'Success';
    } catch (error) {
      errorMessage = `Error: ${error.message}`;
      status = 'Error';
    } finally {
      isLoading = false;
    }
  }

  function goHome() {
    goto('/');
  }

  function setActiveTab(tab) {
    activeTab = tab;
  }
</script>

<svelte:head>
  <title>Project Deux Playground</title>
</svelte:head>

<div class="home-button" on:click={goHome}>Home</div>

<div class="playground-wrapper">
  <div class="navbar">
    <div class="playground-label">Playground</div>
    <div class="status">{status}</div>
  </div>

  <div class="tab-navigation">
    <button class={activeTab === 'configuration' ? 'active' : ''} on:click={() => setActiveTab('configuration')}>Configuration</button>
    <button class={activeTab === 'simulation' ? 'active' : ''} on:click={() => setActiveTab('simulation')}>Simulation/Scenario</button>
    <button class={activeTab === 'result' ? 'active' : ''} on:click={() => setActiveTab('result')}>Result</button>
  </div>

  {#if activeTab === 'configuration'}
    <div class="tab-content">Configuration tab coming soon...</div>
  {:else if activeTab === 'simulation'}
    <div class="tab-content">
      {#if htmlSummary}
        <div class="playground-content">{@html htmlSummary}</div>
      {:else if !isLoading}
        <div class="placeholder">Select a scenario from the dropdown and click "Run Scenario" to view the results.</div>
      {/if}
    </div>
  {:else if activeTab === 'result'}
    <div class="tab-content">Result tab coming soon...</div>
  {/if}

  {#if isLoading}
    <div class="loading-overlay">
      <div class="mosaic-grid">
        {#each Array(25) as _, i}
          <!-- Compute background-position: each tile shows its part of the image -->
          <div 
            class="mosaic-tile" 
            style="animation-delay: {i * 0.1}s; background-position: {(i % 5) * 25}% {(Math.floor(i / 5)) * 25}%;">
          </div>
        {/each}
      </div>
    </div>
  {/if}

  <div class="controls">
    <div class="select-wrapper">
      <select bind:value={scenarioName} disabled={isLoading} class="scenario-select">
        {#each scenarios as scenario}
          <option value={scenario}>{scenario}</option>
        {/each}
        {#if scenarios.length === 0}
          <option value="" disabled>No scenarios available</option>
        {/if}
      </select>
    </div>
    <button on:click={runScenario} disabled={isLoading} class="run-button">
      {isLoading ? 'Running...' : 'Run Scenario'}
    </button>
  </div>

  {#if errorMessage}
    <p class="error-message">{errorMessage}</p>
  {/if}
</div>
<style>
  :global(html),
  :global(body) {
    margin: 0;
    padding: 0;
    height: 100%;
    background: #f5e8c7; /* Cream background for warmth */
    font-family: 'Playfair Display', 'Cinzel', serif; /* Art Deco elegance */
  }

  .home-button {
    position: absolute;
    top: 10px;
    left: 10px;
    font-size: 14px;
    color: #f5e8c7;
    padding: 6px 12px;
    background: #3b2f2b; /* Dark walnut */
    border: 1px solid #b8975b; /* Aged gold border */
    border-radius: 4px;
    cursor: pointer;
    transition: background 0.2s ease, transform 0.2s ease;
    text-transform: uppercase;
    letter-spacing: 1px;
  }

  .home-button:hover {
    background: #4a2c2a; /* Deep burgundy */
    transform: scale(1.05);
  }

  .playground-wrapper {
    position: absolute;
    top: 5%;
    left: 5%;
    right: 5%;
    bottom: 5%;
    background: linear-gradient(135deg, #ffffff 0%, #f5e8c7 100%); /* Subtle cream gradient */
    border: 1px solid #b8975b;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .navbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 20px;
    background: #3b2f2b; /* Dark walnut */
    color: #f5e8c7;
    border-bottom: 2px solid #b8975b;
  }

  .playground-label {
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 1.5px;
  }

  .status {
    font-size: 12px;
    padding: 4px 10px;
    border-radius: 12px;
    background: #4a2c2a; /* Burgundy */
    border: 1px solid #b8975b;
  }

  .tab-navigation {
    display: flex;
    justify-content: center;
    padding: 10px 0;
    background: #f5e8c7;
    border-bottom: 1px solid #b8975b;
  }

  .tab-navigation button {
    padding: 8px 16px;
    font-size: 14px;
    color: #3b2f2b;
    background: none;
    border: none;
    cursor: pointer;
    transition: color 0.2s ease, border-bottom 0.2s ease;
    border-bottom: 2px solid transparent;
    text-transform: uppercase;
    letter-spacing: 1px;
  }

  .tab-navigation button.active {
    color: #b8975b; /* Aged gold */
    border-bottom: 2px solid #b8975b;
  }

  .tab-navigation button:hover:not(.active) {
    color: #4a2c2a; /* Burgundy hover */
  }

  .tab-content {
    flex: 1;
    padding: 20px;
    overflow: hidden;
    background: #ffffff;
  }

  .playground-content {
    padding: 20px;
    overflow-y: auto;
    flex: 1;
    font-size: 16px;
    line-height: 1.6;
    color: #3b2f2b;
    background: #f5e8c7;
    border: 1px solid #b8975b;
    border-radius: 6px;
  }

  .placeholder {
    padding: 20px;
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    color: #4a2c2a;
    text-align: center;
    font-style: italic;
  }

  .loading-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(59, 47, 43, 0.4); /* Dark walnut overlay */
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 5;
  }

  .mosaic-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 4px;
    width: 150px;
    height: 150px;
  }

  .mosaic-tile {
    width: 30px;
    height: 30px;
    background-image: url("/mosaique.png"); /* Reintroduced image */
    background-size: 500% 500%;
    background-position: calc(var(--i) % 5 * 25%) calc(var(--i) / 5 * 25%);
    animation: reveal 1.2s infinite;
    animation-delay: calc(var(--i) * 0.1s);
  }

  /* Define --i for each tile using a CSS custom property */
  .mosaic-tile:nth-child(1) { --i: 0; }
  .mosaic-tile:nth-child(2) { --i: 1; }
  .mosaic-tile:nth-child(3) { --i: 2; }
  .mosaic-tile:nth-child(4) { --i: 3; }
  .mosaic-tile:nth-child(5) { --i: 4; }
  .mosaic-tile:nth-child(6) { --i: 5; }
  .mosaic-tile:nth-child(7) { --i: 6; }
  .mosaic-tile:nth-child(8) { --i: 7; }
  .mosaic-tile:nth-child(9) { --i: 8; }
  .mosaic-tile:nth-child(10) { --i: 9; }
  .mosaic-tile:nth-child(11) { --i: 10; }
  .mosaic-tile:nth-child(12) { --i: 11; }
  .mosaic-tile:nth-child(13) { --i: 12; }
  .mosaic-tile:nth-child(14) { --i: 13; }
  .mosaic-tile:nth-child(15) { --i: 14; }
  .mosaic-tile:nth-child(16) { --i: 15; }
  .mosaic-tile:nth-child(17) { --i: 16; }
  .mosaic-tile:nth-child(18) { --i: 17; }
  .mosaic-tile:nth-child(19) { --i: 18; }
  .mosaic-tile:nth-child(20) { --i: 19; }
  .mosaic-tile:nth-child(21) { --i: 20; }
  .mosaic-tile:nth-child(22) { --i: 21; }
  .mosaic-tile:nth-child(23) { --i: 22; }
  .mosaic-tile:nth-child(24) { --i: 23; }
  .mosaic-tile:nth-child(25) { --i: 24; }

  @keyframes reveal {
    0% { opacity: 0.3; }
    50% { opacity: 1; }
    100% { opacity: 0.3; }
  }

  .controls {
    padding: 20px;
    border-top: 1px solid #b8975b;
    display: flex;
    gap: 15px;
    align-items: center;
    background: #f5e8c7;
  }

  .select-wrapper {
    flex: 1;
    position: relative;
  }

  .scenario-select {
    width: 100%;
    padding: 10px 14px;
    font-size: 14px;
    border: 1px solid #b8975b;
    border-radius: 4px;
    background: #ffffff;
    color: #3b2f2b;
    outline: none;
    cursor: pointer;
    transition: border-color 0.2s ease;
    font-family: 'Playfair Display', serif;
  }

  .scenario-select:focus {
    border-color: #4a2c2a; /* Burgundy focus */
  }

  .scenario-select:disabled {
    background: #f5e8c7;
    color: #7f6a5e;
    cursor: not-allowed;
  }

  .select-wrapper::after {
    content: '▼';
    position: absolute;
    right: 10px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 10px;
    color: #b8975b;
    pointer-events: none;
  }

  .run-button {
    padding: 10px 20px;
    font-size: 14px;
    color: #f5e8c7;
    background: #4a2c2a; /* Burgundy */
    border: 1px solid #b8975b;
    border-radius: 4px;
    cursor: pointer;
    transition: background 0.2s ease, transform 0.2s ease;
    text-transform: uppercase;
    letter-spacing: 1px;
  }

  .run-button:hover:not(:disabled) {
    background: #5e3a36;
    transform: scale(1.02);
  }

  .run-button:disabled {
    background: #7f6a5e;
    cursor: not-allowed;
  }

  .error-message {
    margin: 15px 20px 0;
    padding: 10px;
    background: #f8d7da;
    color: #4a2c2a;
    border: 1px solid #b8975b;
    border-radius: 4px;
    font-size: 14px;
  }

  @media (max-width: 600px) {
    .playground-wrapper {
      top: 2%;
      left: 2%;
      right: 2%;
      bottom: 2%;
    }

    .navbar {
      flex-direction: column;
      align-items: flex-start;
      gap: 8px;
    }

    .controls {
      flex-direction: column;
      gap: 10px;
    }

    .scenario-select,
    .run-button {
      width: 100%;
    }
  }
</style>