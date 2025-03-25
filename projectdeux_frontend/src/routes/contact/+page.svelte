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
  <div class="mac-window main-window" style="transform: translate({windowPos.x}px, {windowPos.y}px);">
    <!-- Menu Bar -->
    <div class="menu-bar">
      <div class="apple-menu"></div>
      <div class="menu-item">File</div>
      <div class="menu-item">Edit</div>
      <div class="menu-item">Agents</div>
      <div class="menu-item">Workflows</div>
      <div class="menu-item">Tools</div>
      <div class="menu-item">Help</div>
    </div>

    <!-- Title Bar -->
    <div class="title-bar" on:mousedown={startDragging}>
      <div class="window-controls">
        <div class="close-btn"></div>
        <div class="minimize-btn"></div>
        <div class="maximize-btn"></div>
      </div>
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
                    fill="#fff"
                    stroke="#000"
                    stroke-width="2"
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
  <div class="mac-window upper-right" style="transform: translate({windowPos.x + 800 + 10}px, {windowPos.y}px);">
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
  <div class="mac-window lower-right" style="transform: translate({windowPos.x + 800 + 10}px, {windowPos.y + 210 + 10}px);">
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
    background: #d3d3d3;
    font-family: 'Courier New', monospace;
    overflow: hidden;
    user-select: none;
  }

  .desktop {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: #d3d3d3;
    background-image: repeating-linear-gradient(45deg, #d3d3d3 0px, #d3d3d3 2px, #c0c0c0 2px, #c0c0c0 4px);
  }

  .mac-window {
    position: absolute;
    background: #fff;
    border: 2px solid #000;
    box-shadow: 4px 4px 0 #000;
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

  .menu-bar {
    height: 24px;
    background: #fff;
    border-bottom: 1px solid #000;
    display: flex;
    align-items: center;
    padding: 0 8px;
    font-size: 12px;
  }

  .apple-menu {
    margin-right: 12px;
    font-size: 16px;
    color: #000;
    filter: brightness(0);
  }

  .menu-item {
    margin-right: 12px;
    padding: 2px 4px;
    cursor: pointer;
  }

  .menu-item:hover {
    background: #000;
    color: #fff;
  }

  .title-bar {
    height: 24px;
    background: repeating-linear-gradient(90deg, #fff 0px, #fff 4px, #000 4px, #000 8px);
    display: flex;
    align-items: center;
    padding: 0 8px;
    border-bottom: 1px solid #000;
  }

  .main-window .title-bar {
    cursor: move;
  }

  .upper-right .title-bar,
  .lower-right .title-bar {
    cursor: default;
  }

  .window-controls {
    display: flex;
    gap: 6px;
  }

  .close-btn, .minimize-btn, .maximize-btn {
    width: 12px;
    height: 12px;
    border: 1px solid #000;
    background: #fff;
  }

  .close-btn:hover, .minimize-btn:hover, .maximize-btn:hover {
    background: #000;
  }

  .title {
    flex-grow: 1;
    text-align: center;
    font-size: 14px;
  }

  .content {
    display: flex;
    flex-grow: 1;
  }

  .upper-right .content,
  .lower-right .content {
    height: calc(100% - 24px);
    background: #fff;
    overflow: hidden;
  }

  .event-list {
    list-style: none;
    padding: 0;
    margin: 0;
    height: 100%;
    overflow-y: auto;
    font-size: 12px;
  }

  .event-list li {
    padding: 4px;
    border-bottom: 1px solid #ccc;
  }

  .report-placeholder {
    padding: 16px;
    font-size: 12px;
    text-align: center;
  }

  .sidebar {
    width: 150px;
    background: #fff;
    border-right: 1px solid #000;
    padding: 8px;
    transition: width 0.3s ease;
  }

  .sidebar.collapsed {
    width: 40px;
  }

  .toggle-btn {
    width: 100%;
    background: #fff;
    border: 1px solid #000;
    padding: 2px;
    cursor: pointer;
    font-size: 12px;
  }

  .toggle-btn:hover {
    background: #000;
    color: #fff;
  }

  .sidebar-item {
    padding: 4px;
    font-size: 12px;
  }

  .sidebar-item:hover {
    background: #000;
    color: #fff;
  }

  .main-area {
    flex-grow: 1;
    display: flex;
    flex-direction: column;
  }

  .tabs {
    display: flex;
    justify-content: flex-start;
    background: #fff;
    border-bottom: 1px solid #000;
    padding: 4px;
  }

  .tabs button {
    padding: 4px 8px;
    border: 1px solid #000;
    background: #fff;
    margin-right: 4px;
    cursor: pointer;
    font-size: 12px;
    transition: background 0.2s;
  }

  .tabs button.active {
    background: #000;
    color: #fff;
  }

  .tabs button:hover:not(.active) {
    background: #e0e0e0;
  }

  .badge {
    background: #000;
    color: #fff;
    padding: 2px 4px;
    font-size: 10px;
    border-radius: 50%;
    margin-left: 4px;
  }

  .tab-content {
    flex-grow: 1;
    padding: 16px;
    background: #fff;
    overflow-y: auto;
    font-size: 12px;
  }

  h2 {
    font-size: 16px;
    margin-bottom: 8px;
    border-bottom: 1px solid #000;
  }

  h3 {
    font-size: 14px;
    margin: 8px 0;
  }

  .agent-list ul, .task-list ul, .workflow-manager ul {
    list-style: none;
    padding: 0;
  }

  .agent-item, .task-item, .workflow-item {
    padding: 8px;
    border-bottom: 1px solid #000;
    transition: background 0.2s;
  }

  .agent-item:hover, .task-item:hover, .workflow-item:hover {
    background: #f0f0f0;
  }

  .state-indicator {
    display: inline-block;
    width: 10px;
    height: 10px;
    margin-right: 8px;
    border: 1px solid #000;
  }

  .state-indicator.idle {
    background: #fff;
  }

  .state-indicator.processing {
    background: repeating-linear-gradient(45deg, #fff 0px, #fff 2px, #000 2px, #000 4px);
  }

  .state-indicator.error {
    background: #000;
  }

  .capabilities {
    display: block;
    font-size: 10px;
    color: #666;
  }

  .task-section {
    display: flex;
    gap: 16px;
  }

  .task-creator, .task-list {
    flex: 1;
  }

  .task-creator form {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .task-creator label {
    display: flex;
    flex-direction: column;
    font-size: 12px;
  }

  .task-creator input, .task-creator select {
    margin-top: 4px;
    padding: 4px;
    border: 1px solid #000;
    font-family: 'Courier New', monospace;
    font-size: 12px;
  }

  .status {
    font-weight: bold;
  }

  .workflow-toggle {
    background: none;
    border: none;
    padding: 0;
    font-size: 12px;
    cursor: pointer;
    text-align: left;
  }

  .workflow-steps {
    margin: 8px 0 0 16px;
    list-style: square;
  }

  .monitoring-panel {
    display: flex;
    gap: 16px;
  }

  .metrics {
    flex: 1;
  }

  .graph {
    display: flex;
    gap: 4px;
    margin-top: 8px;
  }

  .bar {
    height: 20px;
    background: #000;
    transition: width 0.3s ease;
  }

  .action-btn {
    padding: 4px 8px;
    border: 1px solid #000;
    background: #fff;
    cursor: pointer;
    font-size: 12px;
    transition: background 0.2s;
  }

  .action-btn:hover {
    background: #000;
    color: #fff;
  }

  .status-bar {
    height: 24px;
    background: #fff;
    border-top: 1px solid #000;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 8px;
    font-size: 12px;
  }

  .designer {
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  .toolbar {
    display: flex;
    gap: 8px;
    padding: 8px;
    background: #fff;
    border-bottom: 1px solid #000;
  }

  .toolbar button {
    padding: 4px 8px;
    border: 1px solid #000;
    background: #fff;
    cursor: pointer;
    font-size: 12px;
  }

  .toolbar button:hover {
    background: #000;
    color: #fff;
  }

  .canvas {
    flex-grow: 1;
    background: repeating-linear-gradient(
      0deg,
      #e0e0e0 0px,
      #e0e0e0 2px,
      #f0f0f0 2px,
      #f0f0f0 4px
    );
  }

  svg text {
    font-family: 'Courier New', monospace;
    fill: #000;
  }
</style>