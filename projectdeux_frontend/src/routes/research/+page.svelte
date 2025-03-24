<script>
  let activeSection = 'papers'; // Default section

  function setSection(section) {
    activeSection = section;
  }
</script>

<svelte:head>
  <title>Project Deux - Research</title>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Courier+New&family=Georgia&display=swap">
</svelte:head>

<div class="page-wrapper">
  <!-- Navigation -->
  <div class="nav-bar">
    <div class="nav-title">RESEARCH ARCHIVE</div>
    <a href="/" class="nav-link">> HOME</a>
    <a href="#" class="nav-link" class:active={activeSection === 'papers'} on:click|preventDefault={() => setSection('papers')}> > PAPERS</a>
    <a href="#" class="nav-link" class:active={activeSection === 'theses'} on:click|preventDefault={() => setSection('theses')}> > MASTER THESES</a>
    <a href="#" class="nav-link" class:active={activeSection === 'findings'} on:click|preventDefault={() => setSection('findings')}> > FINDINGS</a>
    <a href="#" class="nav-link" class:active={activeSection === 'choreography'} on:click|preventDefault={() => setSection('choreography')}> > CHOREOGRAPHY VS ORCHESTRATION</a>
  </div>

  <!-- Content Area -->
  <div class="content-area">
    {#if activeSection === 'papers'}
      <div class="content">
        <h2>[ PAPERS ]</h2>
        <p>Hard-hitting studies on tech and human crossover. Peer-reviewed and stacked for your brain, brah.</p>
      </div>
    {:else if activeSection === 'theses'}
      <div class="content">
        <h2>[ MASTER THESES ]</h2>
        <ul>
          <li>1. Master Thesis</li>
          <li>   1.1 Primer: A foundational dive into the core principles of autonomous systems and their interplay with human decision-making in complex environments.</li>
          <li>   1.2 Agent Economy: Exploring the emergent behaviors of AI-driven agents in simulated markets, with focus on resource allocation and adaptive strategies.</li>
          <li>   1.3 Collective Intel: Unpacking how networked minds—human and machine—amplify problem-solving, with case studies on swarm dynamics and data synthesis.</li>
        </ul>
      </div>
    {:else if activeSection === 'findings'}
      <div class="content">
        <h2>[ FINDINGS ]</h2>
        <p>Lab-fresh insights. No BS, just the real deal from our grind.</p>
      </div>
    {:else if activeSection === 'choreography'}
      <div class="content">
        <img src="https://res.cloudinary.com/grand-canyon-university/image/fetch/w_750,h_564,c_fill,g_faces,q_auto/https://www.gcu.edu/sites/default/files/2020-11/GettyImages-sb10063090k-001.jpg" 
             alt="Choreography vs Orchestration Header" 
             class="section-header">
        <h2>[ CHOREOGRAPHY VS ORCHESTRATION ]</h2>
        <p>Exploring the dance between distributed systems and centralized control. How do autonomous agents coordinate vs. being directed in tech ecosystems?</p>
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
    background: url('/column1.jpg') no-repeat center center fixed, #1a1a1a;
    background-size: cover;
    background-blend-mode: soft-light;
    font-family: 'Courier New', monospace;
  }

  .page-wrapper {
    position: relative;
    width: 100%;
    height: 100vh;
    background: rgba(235, 225, 205, 0.9);
    background-image: url('/parchment-texture.png');
    background-blend-mode: overlay;
  }

  .nav-bar {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    width: 220px;
    padding: 20px;
    background: #2b2b2b;
    border-right: 3px solid #666;
    box-shadow: 4px 0 10px rgba(0, 0, 0, 0.5);
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .nav-title {
    font-size: 24px;
    color: #ffaa00; /* Orange-gold for title */
    margin-bottom: 20px;
    padding-bottom: 10px;
    border-bottom: 2px solid #ffaa00;
    font-family: 'Georgia', serif;
    text-align: center;
  }

  .nav-link {
    font-size: 18px;
    color: #ffffff; /* All links white */
    text-decoration: none;
    transition: all 0.2s ease;
  }

  .nav-link.active {
    color: #ffffff; /* Active stays white */
    font-weight: bold;
    padding-left: 10px;
  }

  .nav-link:hover {
    color: #ffffff; /* Hover stays white */
    padding-left: 5px;
    text-shadow: 0 0 5px rgba(255, 255, 255, 0.8); /* Subtle glow for hover */
  }

  .content-area {
    position: absolute;
    left: 240px;
    top: 20px;
    right: 20px;
    bottom: 20px;
    padding: 30px;
    background: #f5f5f5;
    border: 2px solid #333;
    box-shadow: 6px 6px 0 #1a1a1a;
    overflow-y: auto;
  }

  .content h2 {
    font-size: 28px;
    color: #222;
    margin: 0 0 20px 0;
    border-bottom: 1px solid #666;
    font-family: 'Georgia', serif;
    text-align: center;
  }

  .content p, .content ul {
    font-size: 16px;
    color: #111;
    line-height: 1.7;
    margin: 15px 0;
  }

  .content ul {
    list-style: none;
    padding-left: 0;
  }

  .content li {
    margin: 10px 0;
  }

  .section-header {
    width: 100%;
    max-width: 750px;
    height: auto;
    margin: 0 auto 20px auto;
    display: block;
    border: 2px solid #333;
    box-shadow: 4px 4px 0 #1a1a1a;
  }
</style>