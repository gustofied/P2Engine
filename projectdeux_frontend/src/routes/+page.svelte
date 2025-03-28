<script>
    // No additional logic needed for the landing page
  </script>
  
  <svelte:head>
    <title>Project Deux</title>
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
  
  <div class="background">
    <div class="content">
      <div class="navbar">
        <a href="/about">About</a>
        <a href="/research">Research</a>
        <a href="/contact">Contact</a>
        <a href="/playground">Playground</a>
        <a href="/bio">Bio</a>
        <a href="/hyper">Hyper</a>
      </div>
      <h1>Project Deux</h1>
      <p>Just a master thesis project</p>
      <a href="/app" class="art-deco-button">Enter App</a>
    </div>
  </div>
  
  <style>
    :global(html),
    :global(body) {
      margin: 0;
      padding: 0;
      height: 100%;
    }
  
    .background {
      background: url("/background.jpg") no-repeat center center fixed, linear-gradient(to bottom, rgba(59, 47, 43, 0.8), rgba(74, 44, 42, 0.8)); /* Walnut-to-burgundy overlay */
      background-size: cover;
      background-blend-mode: overlay;
      width: 100%;
      height: 100vh;
      position: relative;
    }
  
    .content {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      text-align: center;
      color: #f5e8c7; /* Cream text */
      font-family: 'Playfair Display', serif;
      padding: 0 20px;
    }
  
    .navbar {
      margin-bottom: 30px;
      display: flex;
      justify-content: center;
      gap: 20px;
    }
  
    .navbar a {
      text-decoration: none;
      font-size: 18px;
      color: #f5e8c7;
      padding: 10px 20px;
      background: #3b2f2b; /* Dark walnut */
      border: 1px solid #b8975b; /* Aged gold */
      text-transform: uppercase;
      letter-spacing: 2px;
      transition: background 0.3s ease, transform 0.3s ease;
    }
  
    .navbar a:nth-child(1) { transform: rotate(-3deg); }
    .navbar a:nth-child(2) { transform: rotate(2deg); }
    .navbar a:nth-child(3) { transform: rotate(-1deg); }
  
    .navbar a:hover {
      background: #4a2c2a; /* Burgundy */
      transform: rotate(0deg) scale(1.05);
    }
  
    .content h1 {
      overflow: hidden;
      white-space: nowrap;
      border-right: 3px solid rgba(255, 255, 255, 0.75);
      font-family: 'Pecita', Arial, sans-serif; /* Pecita for logo */
      font-size: 100px;
      margin: 0;
      animation: typewriter 10s steps(30, end) infinite,
        blink-caret 0.75s step-end infinite;
    }
  
    @keyframes typewriter {
      0% { width: 0; }
      20% { width: 100%; }
      100% { width: 100%; }
    }
  
    @keyframes blink-caret {
      0%, 100% { border-color: transparent; }
      50% { border-color: rgba(255, 255, 255, 0.75); }
    }
  
    .content p {
      font-family: 'Pecita', Arial, sans-serif; /* Pecita for subtext */
      font-size: 28px;
      margin: 10px 0 20px;
      color: #b8975b; /* Aged gold for contrast */
    }
  
    .art-deco-button {
      display: inline-block;
      padding: 15px 30px;
      font-size: 20px;
      text-decoration: none;
      color: #f5e8c7;
      background: linear-gradient(135deg, #4a2c2a, #5e3a36); /* Burgundy gradient */
      border: 2px solid #b8975b;
      text-transform: uppercase;
      letter-spacing: 2px;
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
      transition: background 0.3s ease, transform 0.3s ease;
    }
  
    .art-deco-button:hover {
      background: linear-gradient(135deg, #5e3a36, #4a2c2a);
      transform: translateY(-3px);
    }
  </style>