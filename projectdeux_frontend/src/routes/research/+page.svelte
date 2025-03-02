<script>
  let activeSection = 'papers'; // Default section

  function setSection(section) {
    activeSection = section;
  }
</script>

<svelte:head>
  <title>Project Deux - Research</title>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&display=swap">
  <style>
    @font-face {
      font-family: "Pecita";
      src: url("/pecita.otf") format("opentype");
      font-weight: normal;
      font-style: normal;
      font-display: swap;
    }
  </style>
</svelte:head>

<div class="page-wrapper">
  <!-- Greek Column as a bookmark-like element -->
  <div class="greek-column">
    <div class="greek-text">Research</div>
  </div>
  <!-- Navigation Buttons (Right of Column, Vertical) -->
  <div class="nav-buttons">
    <a href="/" class="nav-button">Back Home</a>
    <button class:active={activeSection === 'papers'} on:click={() => setSection('papers')}>Papers</button>
    <button class:active={activeSection === 'methods'} on:click={() => setSection('methods')}>Methods</button>
    <button class:active={activeSection === 'findings'} on:click={() => setSection('findings')}>Findings</button>
  </div>
  <!-- Content Area -->
  <div class="content-area">
    {#if activeSection === 'papers'}
      <div class="content fade-in">
        <h2>Papers</h2>
        <p>Explore our published works on technology and human interaction.</p>
      </div>
    {:else if activeSection === 'methods'}
      <div class="content fade-in">
        <h2>Methods</h2>
        <p>Learn about our research methodologies and experimental designs.</p>
      </div>
    {:else if activeSection === 'findings'}
      <div class="content fade-in">
        <h2>Findings</h2>
        <p>Key insights and results from our ongoing studies.</p>
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
    background: #f5e8c7;
    font-family: 'Playfair Display', serif;
  }

  .page-wrapper {
    position: relative;
    width: 100%;
    height: 100vh;
    overflow: hidden;
  }

  .greek-column {
    position: fixed;
    left: 10%;
    top: 0;
    bottom: 0;
    width: 15%;
    background: url('/column1.jpg') no-repeat center center, linear-gradient(to bottom, #3b2f2b, #4a2c2a);
    background-size: cover;
    background-blend-mode: overlay;
    display: flex;
    align-items: center;
    justify-content: center;
    border-right: 2px solid #b8975b;
    box-shadow: 2px 0 10px rgba(0, 0, 0, 0.2);
    z-index: 10;
  }

  .greek-text {
    writing-mode: vertical-rl;
    text-orientation: mixed;
    font-size: 40px;
    color: #f5e8c7;
    transform: rotate(180deg);
    text-transform: uppercase;
    letter-spacing: 2px;
    text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.6);
  }

  .nav-buttons {
    position: fixed;
    left: 25%;
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
    color: #f5e8c7;
    background: linear-gradient(135deg, #4a2c2a, #5e3a36);
    border: 2px solid #b8975b;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    text-decoration: none;
    cursor: pointer;
    transition: background 0.3s ease, transform 0.3s ease;
    text-align: left;
    position: relative;
  }

  .nav-buttons button.active {
    background: linear-gradient(135deg, #5e3a36, #4a2c2a);
    transform: scale(1.05);
  }

  .nav-buttons a.nav-button:hover,
  .nav-buttons button:hover:not(.active) {
    background: linear-gradient(135deg, #5e3a36, #4a2c2a);
    transform: translateX(3px);
  }

  .nav-buttons a.nav-button:not(:last-child)::after,
  .nav-buttons button:not(:last-child)::after {
    content: '····················';
    position: absolute;
    bottom: -10px;
    left: 28px;
    color: #b8975b;
    font-size: 12px;
    letter-spacing: 2px;
  }

  .content-area {
    position: absolute;
    left: 45%;
    top: 40px;
    right: 0;
    bottom: 0;
    padding: 30px 50px;
    overflow-y: auto;
    background: rgba(245, 232, 199, 0.9);
    z-index: 5;
  }

  .content {
    color: #3b2f2b;
  }

  .content h2 {
    font-size: 32px;
    letter-spacing: 1.5px;
    margin: 0 0 25px 0;
  }

  .content p {
    font-size: 20px;
    line-height: 1.6;
  }

  .fade-in {
    animation: fadeIn 0.5s ease-in;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
</style>