<script>
  import { onMount } from 'svelte';
  import { writable, get } from 'svelte/store';

  // Gradient definitions for the colorful text box
  const gradients = [
    'linear-gradient(to bottom, #1e90ff, #32cd32, #ffff00, #ff4500)',
    'linear-gradient(to bottom, #8a2be2, #ff8c00, #ff69b4)',
    'linear-gradient(to bottom, #00ced1, #ff00ff, #ffff00)',
    'linear-gradient(to bottom, #ff6347, #ffd700, #00ff7f, #4169e1)',
    'linear-gradient(to bottom, #ff4500, #9400d3, #00ffff)'
  ];

  // Stores for the terminal text box
  const textChars1 = writable([]); // Just characters
  const isPaused1 = writable(false);
  let textBox1;
  let pauseControl1 = { unpausePromise: null, unpauseResolver: null };

  // Stores for the colorful text box
  const textChars2 = writable([]); // Objects with char, gradient, delay
  const isPaused2 = writable(false);
  let textBox2;
  let pauseControl2 = { unpausePromise: null, unpauseResolver: null };

  let isActive = true;

  // Text generation function
  async function startTextGeneration(textChars, textBox, isPaused, pauseControl, isColorful) {
    const sentences = [
      'Hey there sexy ',
      'Smooth vibes only ',
      'Text that flows ',
      'Pure eye candy '
    ];
    let index = 0;
    while (isActive) {
      const sentence = sentences[index % sentences.length];
      for (const char of sentence) {
        if (get(isPaused)) {
          await pauseControl.unpausePromise;
        }
        if (isColorful) {
          const gradient = gradients[Math.floor(Math.random() * gradients.length)];
          textChars.update(chars => {
            if (chars.length > 1000) chars = chars.slice(-500);
            return [...chars, { char, gradient, delay: Math.random() * 1.5 }];
          });
        } else {
          textChars.update(chars => {
            if (chars.length > 1000) chars = chars.slice(-500);
            return [...chars, char];
          });
        }
        if (textBox) {
          const isAtBottom = textBox.scrollTop + textBox.clientHeight >= textBox.scrollHeight - 10;
          if (isAtBottom) {
            textBox.scrollTo({ top: textBox.scrollHeight, behavior: 'smooth' });
          }
        }
        await new Promise(resolve => setTimeout(resolve, 10));
      }
      index++;
    }
  }

  // Toggle pause for terminal text box
  function togglePause1() {
    if (get(isPaused1)) {
      if (pauseControl1.unpauseResolver) {
        pauseControl1.unpauseResolver();
        pauseControl1.unpauseResolver = null;
        pauseControl1.unpausePromise = null;
      }
      isPaused1.set(false);
    } else {
      isPaused1.set(true);
      pauseControl1.unpausePromise = new Promise(resolve => {
        pauseControl1.unpauseResolver = resolve;
      });
    }
  }

  // Toggle pause for colorful text box
  function togglePause2() {
    if (get(isPaused2)) {
      if (pauseControl2.unpauseResolver) {
        pauseControl2.unpauseResolver();
        pauseControl2.unpauseResolver = null;
        pauseControl2.unpausePromise = null;
      }
      isPaused2.set(false);
    } else {
      isPaused2.set(true);
      pauseControl2.unpausePromise = new Promise(resolve => {
        pauseControl2.unpauseResolver = resolve;
      });
    }
  }

  // Start generation on mount
  onMount(() => {
    startTextGeneration(textChars1, textBox1, isPaused1, pauseControl1, false); // Terminal
    startTextGeneration(textChars2, textBox2, isPaused2, pauseControl2, true); // Colorful
    return () => {
      isActive = false;
    };
  });
</script>

<div class="page-wrapper">
  <div class="background-container">
    <div class="background-right"></div>
    <div class="background-left"></div>
  </div>
  <div class="left-container">
    <div class="terminal-container">
      <div class="terminal-text-box" class:paused={$isPaused1} on:click={togglePause1} bind:this={textBox1}>
        <p>
          {#each $textChars1 as char, i (i)}
            <span>{char}</span>
          {/each}
          <span class="cursor">|</span>
        </p>
      </div>
    </div>
  </div>
  <div class="right-container">
    <div class="colorful-container">
      <div class="colorful-text-box" class:paused={$isPaused2} on:click={togglePause2} bind:this={textBox2}>
        <p>
          {#each $textChars2 as { char, gradient, delay }, i (i)}
            <span class={$isPaused2 ? 'paused' : ''} style={!$isPaused2 ? `background: ${gradient} 0% 0% / 100% 400%; --delay: ${delay}s` : ''}>{char}</span>
          {/each}
          <span class="cursor">|</span>
        </p>
      </div>
    </div>
  </div>
</div>

<style>
  /* Full-page wrapper */
  .page-wrapper {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    overflow: hidden;
  }

  /* Background container */
  .background-container {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 0; /* Behind the content */
  }

  /* Right background (covers the entire area) */
  .background-right {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-image: url('https://e3.365dm.com/23/03/2048x1152/skynews-pablo-picasso-maya_6074971.jpg');
    background-size: cover;
    background-position: center;
  }

  /* Left background (60% with single zag) */
  .background-left {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-image: url('https://f8n-production-collection-assets.imgix.net/0x7C1bd459dae8eC0Bb45FE3172Fd58A2B53972e5C/2/nft.gif');
    background-size: cover;
    background-position: center;
    clip-path: polygon(0% 0%, 60% 0%, 55% 50%, 60% 100%, 0% 100%);
  }

  /* Left container (60% width) */
  .left-container {
    position: absolute;
    top: 0;
    left: 0;
    width: 60%;
    height: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1;
  }

  /* Right container (40% width) */
  .right-container {
    position: absolute;
    top: 0;
    right: 0;
    width: 40%;
    height: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1;
  }

  /* Terminal Container (larger box) */
  .terminal-container {
    width: 80%;
    height: 80%;
    position: relative;
    background: rgba(0, 0, 0, 0.5); /* Reduced opacity */
  }

  /* Terminal Text Box (smaller inside) */
  .terminal-text-box {
    position: absolute;
    bottom: 20px;
    left: 20px;
    width: 40%;
    height: 40%;
    overflow-y: auto;
    background: rgba(0, 0, 0, 0.8);
    color: #0f0; /* Bright green when running */
    font-family: 'Courier New', Courier, monospace;
    font-size: 16px;
    padding: 15px;
    border: 1px solid #333;
    box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
    cursor: pointer;
  }

  .terminal-text-box span {
    color: #0f0;
    transition: color 0.3s, text-shadow 0.3s;
  }

  .terminal-text-box.paused span {
    color: #060; /* Dimmer green when paused */
    text-shadow: 1px 1px 2px rgba(0, 255, 0, 0.5); /* Shadowy effect */
  }

  .terminal-text-box .cursor {
    color: #0f0;
    animation: blink 1s step-end infinite;
  }

  .terminal-text-box.paused .cursor {
    animation: none;
    opacity: 1; /* Solid cursor when paused */
  }

  /* Colorful Container (larger box) */
  .colorful-container {
    width: 80%;
    height: 80%;
    position: relative;
    background: rgba(255, 255, 255, 0.5); /* Reduced opacity */
  }

  /* Colorful Text Box (smaller inside) */
  .colorful-text-box {
    position: absolute;
    bottom: 20px;
    left: 20px;
    width: 40%;
    height: 40%;
    overflow-y: auto;
    background: rgba(255, 255, 255, 0.8);
    padding: 15px;
    border-radius: 15px;
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
    cursor: pointer;
  }

  .colorful-text-box span {
    background-clip: text;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: flow 3s ease-in-out infinite;
    animation-delay: var(--delay);
  }

  .colorful-text-box span.paused {
    background: none;
    -webkit-text-fill-color: #000; /* Black text when paused */
    animation: none;
  }

  .colorful-text-box .cursor {
    -webkit-text-fill-color: #000;
    animation: blink 1s step-end infinite;
  }

  .colorful-text-box.paused .cursor {
    animation: none;
    opacity: 1; /* Solid cursor when paused */
  }

  /* Animations */
  @keyframes flow {
    0% { background-position: 0% 0%; }
    50% { background-position: 0% 100%; }
    100% { background-position: 0% 0%; }
  }

  @keyframes blink {
    50% { opacity: 0; }
  }
</style>