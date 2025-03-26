<script>
  import { onMount, tick } from 'svelte';

  // Mock data for p2mas
  let agents = [
    { id: '1', type: 'llm_agent', state: 'Idle', capabilities: ['math', 'text_analysis'] },
    { id: '2', type: 'human_agent', state: 'Processing', capabilities: ['review'] },
    { id: '3', type: 'dummy_agent', state: 'Error', capabilities: ['testing'] },
  ];

  let tasks = [
    { id: 't1', agent: '1', data: 'Calculate something', status: 'Pending' },
    { id: 't2', agent: '2', data: 'Review this', status: 'Completed' },
  ];

  let workflows = [
    { name: 'plan_a_party', status: 'Not Started', steps: ['Step 1: Budget', 'Step 2: Plan'] },
    { name: 'tell_a_joke', status: 'Completed', steps: ['Step 1: Tell joke'] },
  ];

  let expandedWorkflow = null;

  // Tab management
  let currentTab = 'Agents';

  function setTab(tab) {
    currentTab = tab;
  }

  // Sidebar collapse
  let collapsed = false;

  function toggleSidebar() {
    collapsed = !collapsed;
  }

  // Mock functions for interactivity
  function createTask(taskData, targetAgent, requiredCapability, simulateFailure) {
    tasks = [...tasks, {
      id: `t${tasks.length + 1}`,
      agent: targetAgent || 'N/A',
      data: taskData,
      status: 'Pending'
    }];
  }

  function startWorkflow(workflowName) {
    workflows = workflows.map(w => w.name === workflowName ? { ...w, status: 'Running' } : w);
  }

  // Window dragging
  let isDragging = false;
  let windowPos = { x: 0, y: 0 };
  let offset = { x: 0, y: 0 };

  function startDragging(event) {
    isDragging = true;
    offset.x = event.clientX - windowPos.x;
    offset.y = event.clientY - windowPos.y;
  }

  function stopDragging() {
    isDragging = false;
  }

  function dragWindow(event) {
    if (isDragging) {
      windowPos.x = Math.max(0, Math.min(event.clientX - offset.x, window.innerWidth - 800));
      windowPos.y = Math.max(0, Math.min(event.clientY - offset.y, window.innerHeight - 600));
    }
  }

  // Clock in status bar
  let currentTime = new Date().toLocaleTimeString();

  function updateTime() {
    currentTime = new Date().toLocaleTimeString();
    tick();
  }

  // Live events for upper right window
  let events = [
    { time: '12:00:00', message: 'Agent 1 started task t1' },
    { time: '12:00:05', message: 'Agent 2 completed task t2' },
  ];

  function addEvent() {
    const newEvent = {
      time: new Date().toLocaleTimeString(),
      message: `Agent ${Math.floor(Math.random() * 3) + 1} performed an action`
    };
    events = [...events, newEvent].slice(-10);
  }

  // Designer view state
  let canvasElements = [];
  let connections = [];
  let nextId = 0;
  let connectMode = false;
  let selectedSource = null;
  let draggingElement = null;
  let dragOffset = { x: 0, y: 0 };
  let canvas;

  function addElement(type) {
    const newElement = {
      id: nextId++,
      type,
      x: 50,
      y: 50,
    };
    canvasElements = [...canvasElements, newElement];
  }

  function enterConnectMode() {
    connectMode = true;
    selectedSource = null;
  }

  function getCenter(id) {
    const element = canvasElements.find(el => el.id === id);
    return element ? { x: element.x + 50, y: element.y + 25 } : { x: 0, y: 0 };
  }

  function startDrag(event, id) {
    event.stopPropagation();
    if (connectMode) {
      if (selectedSource === null) {
        selectedSource = id;
      } else {
        connections = [...connections, [selectedSource, id]];
        connectMode = false;
        selectedSource = null;
      }
    } else {
      draggingElement = id;
      const rect = canvas.getBoundingClientRect();
      const element = canvasElements.find(el => el.id === id);
      dragOffset.x = event.clientX - rect.left - element.x;
      dragOffset.y = event.clientY - rect.top - element.y;
    }
  }

  function onMouseMove(event) {
    if (draggingElement !== null) {
      const rect = canvas.getBoundingClientRect();
      const element = canvasElements.find(el => el.id === draggingElement);
      if (element) {
        element.x = event.clientX - rect.left - dragOffset.x;
        element.y = event.clientY - rect.top - dragOffset.y;
        canvasElements = canvasElements;
      }
    } else {
      dragWindow(event);
    }
  }

  function onMouseUp() {
    draggingElement = null;
    stopDragging();
  }

  onMount(() => {
    const windowWidth = 800;
    const windowHeight = 600;
    windowPos.x = (window.innerWidth - windowWidth) / 2;
    windowPos.y = (window.innerHeight - windowHeight) / 2;

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);

    const timeInterval = setInterval(updateTime, 1000);
    const eventInterval = setInterval(addEvent, 5000);

    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      clearInterval(timeInterval);
      clearInterval(eventInterval);
    };
  });
</script>

<div class="desktop">
  <!-- Main Window -->
  <div class="main-window" style="transform: translate({windowPos.x}px, {windowPos.y}px);">
    <!-- Title Bar -->
    <div class="title-bar" on:mousedown={startDragging}>
      <div class="title">p2mas - Control Panel</div>
    </div>

    <!-- Main Content -->
    <div class="content">
      <!-- Sidebar -->
      <div class="sidebar" class:collapsed>
        <button on:click={toggleSidebar} class="toggle-btn">{collapsed ? '>' : '<'}</button>
        {#if !collapsed}
          <h3>Agents</h3>
          <ul>
            {#each agents as agent}
              <li class="sidebar-item">{agent.id} - {agent.type}</li>
            {/each}
          </ul>
        {/if}
      </div>

      <!-- Tabbed Interface -->
      <div class="main-area">
        <div class="tabs">
          <button on:click={() => setTab('Agents')} class:active={currentTab === 'Agents'}>
            Agents <span class="badge">{agents.length}</span>
          </button>
          <button on:click={() => setTab('Tasks')} class:active={currentTab === 'Tasks'}>
            Tasks <span class="badge">{tasks.filter(t => t.status === 'Pending').length}</span>
          </button>
          <button on:click={() => setTab('Workflows')} class:active={currentTab === 'Workflows'}>
            Workflows <span class="badge">{workflows.filter(w => w.status === 'Running').length}</span>
          </button>
          <button on:click={() => setTab('Monitoring')} class:active={currentTab === 'Monitoring'}>
            Monitoring
          </button>
          <button on:click={() => setTab('Designer')} class:active={currentTab === 'Designer'}>Designer</button>
        </div>
        <div class="tab-content">
          {#if currentTab === 'Agents'}
            <div class="agent-list">
              <h2>Agents</h2>
              <ul>
                {#each agents as agent}
                  <li class="agent-item">
                    <span class="state-indicator {agent.state.toLowerCase()}"></span>
                    <strong>{agent.id}</strong> - {agent.type} - {agent.state}
                    <span class="capabilities">Capabilities: {agent.capabilities.join(', ')}</span>
                  </li>
                {/each}
              </ul>
              <button class="action-btn" on:click={() => console.log('Create New Agent')}>Create New Agent</button>
            </div>
          {:else if currentTab === 'Tasks'}
            <div class="task-section">
              <div class="task-creator">
                <h2>Create Task</h2>
                <form on:submit|preventDefault={e => {
                  const formData = new FormData(e.target);
                  createTask(
                    formData.get('taskData'),
                    formData.get('targetAgent'),
                    formData.get('requiredCapability'),
                    formData.get('simulateFailure') === 'on'
                  );
                  e.target.reset();
                }}>
                  <label>
                    Task Data:
                    <input type="text" name="taskData" required placeholder="Enter task description" />
                  </label>
                  <label>
                    Target Agent:
                    <select name="targetAgent">
                      <option value="">Select Agent</option>
                      {#each agents as agent}
                        <option value={agent.id}>{agent.id} - {agent.type}</option>
                      {/each}
                    </select>
                  </label>
                  <label>
                    Required Capability:
                    <select name="requiredCapability">
                      <option value="">Select Capability</option>
                      <option value="math">Math</option>
                      <option value="text_analysis">Text Analysis</option>
                      <option value="review">Review</option>
                      <option value="testing">Testing</option>
                    </select>
                  </label>
                  <label>
                    Simulate Failure:
                    <input type="checkbox" name="simulateFailure" />
                  </label>
                  <button type="submit" class="action-btn">Create Task</button>
                </form>
              </div>
              <div class="task-list">
                <h2>Tasks</h2>
                <ul>
                  {#each tasks as task}
                    <li class="task-item">{task.id} - Agent: {task.agent} - {task.data} - <span class="status">{task.status}</span></li>
                  {/each}
                </ul>
              </div>
            </div>
          {:else if currentTab === 'Workflows'}
            <div class="workflow-manager">
              <h2>Workflows</h2>
              <ul>
                {#each workflows as workflow}
                  <li class="workflow-item">
                    <button class="workflow-toggle" on:click={() => expandedWorkflow = expandedWorkflow === workflow.name ? null : workflow.name}>
                      {workflow.name} - {workflow.status}
                    </button>
                    {#if expandedWorkflow === workflow.name}
                      <ul class="workflow-steps">
                        {#each workflow.steps as step}
                          <li>{step}</li>
                        {/each}
                      </ul>
                    {/if}
                    <button class="action-btn" on:click={() => startWorkflow(workflow.name)}>Start Workflow</button>
                  </li>
                {/each}
              </ul>
            </div>
          {:else if currentTab === 'Monitoring'}
            <div class="monitoring-panel">
              <h2>Monitoring</h2>
              <div class="metrics">
                <h3>Agent States</h3>
                <ul>
                  {#each agents as agent}
                    <li>{agent.id}: {agent.state}</li>
                  {/each}
                </ul>
              </div>
              <div class="metrics">
                <h3>Task Queues</h3>
                <ul>
                  {#each tasks as task}
                    <li>{task.id}: {task.status}</li>
                  {/each}
                </ul>
              </div>
              <div class="metrics">
                <h3>System Metrics</h3>
                <p>Average Task Completion Time: 5s</p>
                <p>Errors in Last Hour: 2</p>
                <div class="graph">
                  <div class="bar" style="width: 50%;"></div>
                  <div class="bar" style="width: 30%;"></div>
                  <div class="bar" style="width: 70%;"></div>
                </div>
              </div>
            </div>
          {:else if currentTab === 'Designer'}
            <div class="designer">
              <div class="toolbar">
                <button on:click={() => addElement('agent')}>Add Agent</button>
                <button on:click={() => addElement('task')}>Add Task</button>
                <button on:click={enterConnectMode}>Connect</button>
              </div>
              <svg bind:this={canvas} class="canvas" width="100%" height="100%">
                {#each canvasElements as element (element.id)}
                  <rect
                    x={element.x}
                    y={element.y}
                    width="100"
                    height="50"
                    fill="#fffbe6"
                    stroke="#000"
                    stroke-width="2"
                    rx="8"
                    ry="8"
                    on:mousedown={e => startDrag(e, element.id)}
                    on:dblclick={() => console.log(`Edit element ${element.id}`)}
                  />
                  <text x={element.x + 10} y={element.y + 30} font-size="12">{element.type}</text>
                {/each}
                {#each connections as conn}
                  <line
                    x1={getCenter(conn[0]).x}
                    y1={getCenter(conn[0]).y}
                    x2={getCenter(conn[1]).x}
                    y2={getCenter(conn[1]).y}
                    stroke="#000"
                    stroke-width="2"
                  />
                {/each}
              </svg>
            </div>
          {/if}
        </div>
      </div>
    </div>

    <!-- Status Bar -->
    <div class="status-bar">
      <span>System Status: Running</span>
      <span>Agents: {agents.length}</span>
      <span>{currentTime}</span>
    </div>
  </div>

  <!-- Upper Right Window: Live Environment View -->
  <div class="upper-right" style="transform: translate({windowPos.x + 800 + 10}px, {windowPos.y}px);">
    <div class="title-bar">
      <div class="title">Live Environment View</div>
    </div>
    <div class="content">
      <ul class="event-list">
        {#each events as event}
          <li>{event.time} - {event.message}</li>
        {/each}
      </ul>
    </div>
  </div>

  <!-- Lower Right Window: Report Viewer -->
  <div class="lower-right" style="transform: translate({windowPos.x + 800 + 10}px, {windowPos.y + 210 + 10}px);">
    <div class="title-bar">
      <div class="title">Report Viewer</div>
    </div>
    <div class="content">
      <div class="report-placeholder">
        <p>Here will be the report, possibly using D3.js for visualization.</p>
        <p>For now, imagine a beautiful bar chart showing task completion rates.</p>
      </div>
    </div>
  </div>
</div>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    background: #f5f0e1; /* Light beige */
    background-image: url('path-to-watercolor-texture.png'); /* Subtle watercolor texture */
    background-size: cover;
    font-family: 'Handwritten', sans-serif; /* Replace with an actual handwritten font */
    overflow: hidden;
    user-select: none;
  }

  /* Define the handwritten font (replace with your font file) */
  @font-face {
    font-family: 'Handwritten';
    src: url('path-to-handwritten-font.woff2') format('woff2');
  }

  .desktop {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: #f5f0e1;
    background-image: url('path-to-watercolor-texture.png');
    background-size: cover;
  }

  .main-window, .upper-right, .lower-right {
    position: absolute;
    background: #fffbe6; /* Slightly off-white beige */
    border: 2px solid #000;
    border-radius: 10px;
    display: flex;
    flex-direction: column;
  }

  .main-window {
    width: 800px;
    height: 600px;
  }

  .upper-right {
    width: 240px;
    height: 210px;
  }

  .lower-right {
    width: 240px;
    height: 390px;
  }

  .title-bar {
    height: 30px;
    background: #fffbe6;
    display: flex;
    align-items: center;
    padding: 0 12px;
    border-bottom: 2px solid #000;
    border-radius: 10px 10px 0 0;
    cursor: move;
  }

  .title {
    flex-grow: 1;
    text-align: center;
    font-size: 16px;
    color: #000;
  }

  .content {
    display: flex;
    flex-grow: 1;
    background: #fffbe6;
    border-radius: 0 0 10px 10px;
  }

  .upper-right .content,
  .lower-right .content {
    height: calc(100% - 30px);
    background: #fffbe6;
    overflow: hidden;
    border-radius: 0 0 10px 10px;
  }

  .event-list {
    list-style: none;
    padding: 8px;
    margin: 0;
    height: 100%;
    overflow-y: auto;
    font-size: 12px;
    color: #000;
  }

  .event-list li {
    padding: 6px;
    border-bottom: 1px solid #ccc;
  }

  .report-placeholder {
    padding: 20px;
    font-size: 12px;
    text-align: center;
    color: #000;
  }

  .sidebar {
    width: 150px;
    background: #f5e8c7; /* Slightly darker beige */
    border-right: 2px solid #000;
    padding: 12px;
    transition: width 0.3s ease;
    border-radius: 0 10px 10px 0;
  }

  .sidebar.collapsed {
    width: 40px;
  }

  .toggle-btn {
    width: 100%;
    background: #d3c7e5; /* Light purple */
    border: 2px solid #000;
    border-radius: 8px;
    padding: 4px;
    cursor: pointer;
    font-size: 14px;
    color: #000;
  }

  .toggle-btn:hover {
    background: #b8a9d1; /* Darker purple */
  }

  .sidebar h3 {
    font-size: 16px;
    margin-bottom: 12px;
    border-bottom: 1px solid #000;
    color: #000;
  }

  .sidebar-item {
    padding: 6px;
    font-size: 12px;
    color: #000;
    border-bottom: 1px solid #ccc;
  }

  .sidebar-item:hover {
    background: #e8d9a9; /* Light yellow */
  }

  .main-area {
    flex-grow: 1;
    display: flex;
    flex-direction: column;
  }

  .tabs {
    display: flex;
    justify-content: flex-start;
    background: #fffbe6;
    padding: 8px;
    border-bottom: 2px solid #000;
  }

  .tabs button {
    padding: 6px 12px;
    border: 2px solid #000;
    background: #d3e5c7; /* Light green */
    margin-right: 8px;
    cursor: pointer;
    font-size: 12px;
    color: #000;
    border-radius: 8px;
    transition: background 0.2s;
  }

  .tabs button.active {
    background: #b8d1a9; /* Darker green */
  }

  .tabs button:hover:not(.active) {
    background: #c7d9b8; /* Slightly darker green */
  }

  .badge {
    background: #a9c7d1; /* Light teal */
    color: #000;
    padding: 2px 6px;
    font-size: 10px;
    border-radius: 50%;
    margin-left: 6px;
  }

  .tab-content {
    flex-grow: 1;
    padding: 20px;
    background: #fffbe6;
    overflow-y: auto;
    font-size: 12px;
    color: #000;
  }

  h2 {
    font-size: 18px;
    margin-bottom: 12px;
    border-bottom: 1px solid #000;
    color: #000;
  }

  h3 {
    font-size: 14px;
    margin: 12px 0;
    color: #000;
  }

  .agent-list ul, .task-list ul, .workflow-manager ul {
    list-style: none;
    padding: 0;
  }

  .agent-item, .task-item, .workflow-item {
    padding: 10px;
    border-bottom: 1px solid #ccc;
    transition: background 0.2s;
  }

  .agent-item:hover, .task-item:hover, .workflow-item:hover {
    background: #e8d9a9; /* Light yellow */
  }

  .state-indicator {
    display: inline-block;
    width: 12px;
    height: 12px;
    margin-right: 10px;
    border: 2px solid #000;
    border-radius: 50%;
  }

  .state-indicator.idle {
    background: #fffbe6; /* Off-white */
  }

  .state-indicator.processing {
    background: #d3e5c7; /* Light green */
  }

  .state-indicator.error {
    background: #a9c7d1; /* Light teal */
  }

  .capabilities {
    display: block;
    font-size: 10px;
    color: #666;
  }

  .task-section {
    display: flex;
    gap: 20px;
  }

  .task-creator, .task-list {
    flex: 1;
  }

  .task-creator form {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .task-creator label {
    display: flex;
    flex-direction: column;
    font-size: 12px;
    color: #000;
  }

  .task-creator input, .task-creator select {
    margin-top: 6px;
    padding: 6px;
    border: 2px solid #000;
    border-radius: 8px;
    font-family: 'Handwritten', sans-serif;
    font-size: 12px;
    background: #fffbe6;
    color: #000;
  }

  .status {
    font-weight: bold;
    color: #000;
  }

  .workflow-toggle {
    background: none;
    border: none;
    padding: 0;
    font-size: 12px;
    cursor: pointer;
    text-align: left;
    color: #000;
  }

  .workflow-steps {
    margin: 12px 0 0 20px;
    list-style: square;
    color: #000;
  }

  .monitoring-panel {
    display: flex;
    gap: 20px;
  }

  .metrics {
    flex: 1;
  }

  .graph {
    display: flex;
    gap: 6px;
    margin-top: 12px;
  }

  .bar {
    height: 24px;
    background: #a9c7d1; /* Light teal */
    border: 2px solid #000;
    border-radius: 6px;
    transition: width 0.3s ease;
  }

  .action-btn {
    padding: 6px 12px;
    border: 2px solid #000;
    background: #d3c7e5; /* Light purple */
    cursor: pointer;
    font-size: 12px;
    color: #000;
    border-radius: 8px;
    transition: background 0.2s;
  }

  .action-btn:hover {
    background: #b8a9d1; /* Darker purple */
  }

  .status-bar {
    height: 30px;
    background: #f5e8c7; /* Slightly darker beige */
    border-top: 2px solid #000;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 12px;
    font-size: 12px;
    color: #000;
    border-radius: 0 0 10px 10px;
  }

  .designer {
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  .toolbar {
    display: flex;
    gap: 12px;
    padding: 12px;
    background: #f5e8c7;
    border-bottom: 2px solid #000;
  }

  .toolbar button {
    padding: 6px 12px;
    border: 2px solid #000;
    background: #d3e5c7; /* Light green */
    cursor: pointer;
    font-size: 12px;
    color: #000;
    border-radius: 8px;
  }

  .toolbar button:hover {
    background: #b8d1a9; /* Darker green */
  }

  .canvas {
    flex-grow: 1;
    background: #e8d9a9; /* Light yellow */
  }

  svg text {
    font-family: 'Handwritten', sans-serif;
    fill: #000;
  }
</style>