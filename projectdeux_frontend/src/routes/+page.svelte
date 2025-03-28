<script>
  // No additional logic needed for the landing page
</script>

<svelte:head>
  <title>Project Deux</title>
  <link
    rel="stylesheet"
    href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&display=swap"
/>
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

<!-- BACKGROUND CONTAINER -->
<div class="background">
  <!-- SPLATTERED NAVBAR NEAR THE TOP -->
  <div class="navbar">
    <a href="/about">About</a>
    <a href="/research">Research</a>
    <a href="/contact">Contact</a>
    <a href="/playground">Playground</a>
    <a href="/bio">Bio</a>
    <a href="/hyper">Hyper</a>
  </div>

  <!-- MAIN CONTENT ABSOLUTE-CENTERED -->
  <div class="content">
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
    font-family: "Playfair Display", serif;
  }

  /* BACKGROUND STYLING */
  .background {
    position: relative;
    width: 100%;
    height: 100vh;
    background: url("/background.jpg") no-repeat center center fixed,
      linear-gradient(to bottom, rgba(59, 47, 43, 0.85), rgba(74, 44, 42, 0.85));
    background-size: cover;
    background-blend-mode: overlay;
  }

  /* NAVBAR: NEAR THE TOP, SPLATTERED BUTTONS */
  .navbar {
    position: absolute;
    top: 30px; /* Distance from top of screen */
    left: 0;
    right: 0;
    height: 350px; /* Increase if needed so buttons have room to spread out */
    margin: 0 auto;
    overflow: hidden; /* Hide any accidental overflow */
  }

  .navbar a {
    position: absolute;
    display: inline-block;
    text-decoration: none;
    font-size: 18px;
    color: #fff;
    padding: 10px 20px;
    text-transform: uppercase;
    letter-spacing: 2px;
    border: 1px solid #b8975b;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
    transition: transform 0.3s ease, box-shadow 0.3s ease;

    /* Subtle gray gradient overlay to reduce brightness */
    background-blend-mode: multiply;
    background-image: linear-gradient(
      rgba(128, 128, 128, 0.3),
      rgba(128, 128, 128, 0.3)
    );
  }

  /* CAREFUL PLACEMENT TO AVOID OVERLAP */
  .navbar a:nth-child(1) {
    top: 20px;
    left: 10%;
    background-color: #e74c3c; /* red */
    transform: rotate(-10deg);
  }
  .navbar a:nth-child(2) {
    top: 50px;
    left: 40%;
    background-color: #3498db; /* blue */
    transform: rotate(5deg);
  }
  .navbar a:nth-child(3) {
    top: 100px;
    left: 70%;
    background-color: #9b59b6; /* purple */
    transform: rotate(-4deg);
  }
  .navbar a:nth-child(4) {
    top: 160px;
    left: 15%;
    background-color: #1abc9c; /* teal */
    transform: rotate(12deg);
  }
  .navbar a:nth-child(5) {
    top: 210px;
    left: 45%;
    background-color: #f39c12; /* orange */
    transform: rotate(-5deg);
  }
  .navbar a:nth-child(6) {
    top: 260px;
    left: 75%;
    background-color: #e67e22; /* carrot */
    transform: rotate(5deg);
  }

  .navbar a:hover {
    transform: scale(1.05) rotate(0deg);
    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.4);
  }

  /* MAIN CONTENT: CENTERED */
  .content {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;
    color: #f5e8c7;
    padding: 0 20px;
  }

  /* HEADING & TYPEWRITER EFFECT */
  .content h1 {
    overflow: hidden;
    white-space: nowrap;
    border-right: 3px solid rgba(255, 255, 255, 0.75);
    font-family: "Pecita", Arial, sans-serif;
    font-size: 100px;
    margin: 0;
    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
    animation: typewriter 10s steps(30, end) infinite,
      blink-caret 0.75s step-end infinite;
  }

  @keyframes typewriter {
    0% {
      width: 0;
    }
    20% {
      width: 100%;
    }
    100% {
      width: 100%;
    }
  }

  @keyframes blink-caret {
    0%,
    100% {
      border-color: transparent;
    }
    50% {
      border-color: rgba(255, 255, 255, 0.75);
    }
  }

  /* SUBTEXT */
  .content p {
    font-family: "Pecita", Arial, sans-serif;
    font-size: 28px;
    margin: 10px 0 20px;
    color: #b8975b;
    text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.4);
  }

  /* CALL-TO-ACTION BUTTON */
  .art-deco-button {
    display: inline-block;
    padding: 15px 30px;
    font-size: 20px;
    text-decoration: none;
    color: #f5e8c7;
    background: linear-gradient(135deg, #4a2c2a, #5e3a36);
    border: 2px solid #b8975b;
    text-transform: uppercase;
    letter-spacing: 2px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
    transition: background 0.3s ease, transform 0.3s ease, box-shadow 0.3s ease;
  }

  .art-deco-button:hover {
    background: linear-gradient(135deg, #5e3a36, #4a2c2a);
    transform: translateY(-3px);
    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.4);
  }

  /* RESPONSIVE ADJUSTMENTS */
  @media (max-width: 768px) {
    .content h1 {
      font-size: 60px;
    }
    .content p {
      font-size: 20px;
    }
    .navbar {
      height: 300px; /* Increase on mobile so buttons don't overlap */
    }
    .navbar a {
      font-size: 16px;
      padding: 8px 16px;
    }
  }
</style>
