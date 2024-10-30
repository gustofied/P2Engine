import React, { useState } from "react";
import { Container, Title, Grid, Text, Card, Stack } from "@mantine/core";
import ReactFlow, {
  Background,
  addEdge,
  Edge,
  Node,
  Connection,
} from "react-flow-renderer";

import "../index.css"; // Assuming the CSS file is named styles.css

// TypeScript interface for FlowCard props
interface FlowCardProps {
  title: string;
  description: string;
  flow: {
    nodes: Node[];
    edges: Edge[];
  };
}

// Biological System Flow (Square Nodes)
const createBioSystemFlow = () => ({
  nodes: [
    {
      id: "1",
      data: { label: "Cell Signaling" },
      position: { x: 150, y: 50 },
      style: { background: "#d4edda", padding: 10, borderRadius: "5px" },
    },
    {
      id: "2",
      data: { label: "Molecular Interactions" },
      position: { x: 300, y: 50 },
      style: { background: "#d4edda", padding: 10, borderRadius: "5px" },
    },
    {
      id: "3",
      data: { label: "System Adaptation" },
      position: { x: 225, y: 150 },
      style: { background: "#d4edda", padding: 10, borderRadius: "5px" },
    },
  ] as Node[],
  edges: [
    { id: "e1-2", source: "1", target: "2", animated: true },
    { id: "e2-3", source: "2", target: "3", animated: true },
    { id: "e1-3", source: "1", target: "3", animated: true },
  ] as Edge[],
});

// AI Agent Network Flow (Square Nodes)
const createAISystemFlow = () => ({
  nodes: [
    {
      id: "1",
      data: { label: "AI Agents" },
      position: { x: 150, y: 50 },
      style: { background: "#cce5ff", padding: 10, borderRadius: "5px" },
    },
    {
      id: "2",
      data: { label: "Smart Contracts" },
      position: { x: 300, y: 50 },
      style: { background: "#cce5ff", padding: 10, borderRadius: "5px" },
    },
    {
      id: "3",
      data: { label: "Decentralized Tasks" },
      position: { x: 225, y: 150 },
      style: { background: "#cce5ff", padding: 10, borderRadius: "5px" },
    },
  ] as Node[],
  edges: [
    { id: "e1-2", source: "1", target: "2", animated: true },
    { id: "e2-3", source: "2", target: "3", animated: true },
    { id: "e1-3", source: "1", target: "3", animated: true },
  ] as Edge[],
});

// Marketplace Interaction Flow
const createMarketplaceInteractionFlow = () => ({
  nodes: [
    {
      id: "1",
      data: { label: "Agent" },
      position: { x: 150, y: 50 },
      style: { background: "#c3f3fa", padding: 10, borderRadius: "50%" },
    },
    {
      id: "2",
      data: { label: "Smart Contract" },
      position: { x: 300, y: 50 },
      style: { background: "#fae3d9", padding: 10, borderRadius: "5px" },
    },
    {
      id: "3",
      data: { label: "Resource Pool" },
      position: { x: 225, y: 150 },
      style: { background: "#c3f3fa", padding: 10, borderRadius: "50%" },
    },
  ] as Node[],
  edges: [
    { id: "e1-2", source: "1", target: "2", animated: true },
    { id: "e2-3", source: "2", target: "3", animated: true },
  ] as Edge[],
});

// Tokenized Workflow Flow
const createTokenizedWorkflowFlow = () => ({
  nodes: [
    {
      id: "1",
      data: { label: "Task Initiator" },
      position: { x: 150, y: 50 },
      style: { background: "#b3e5fc", padding: 10, borderRadius: "50%" },
    },
    {
      id: "2",
      data: { label: "Workflow Smart Contract" },
      position: { x: 300, y: 50 },
      style: { background: "#ffcdd2", padding: 10, borderRadius: "5px" },
    },
    {
      id: "3",
      data: { label: "Task Executor" },
      position: { x: 225, y: 150 },
      style: { background: "#b3e5fc", padding: 10, borderRadius: "50%" },
    },
  ] as Node[],
  edges: [
    { id: "e1-2", source: "1", target: "2", animated: true },
    { id: "e2-3", source: "2", target: "3", animated: true },
  ] as Edge[],
});

// FlowCard component with square alignment and no zoom or movement
const FlowCard: React.FC<FlowCardProps> = ({ title, description, flow }) => {
  const [nodes] = useState<Node[]>(flow.nodes);
  const [edges, setEdges] = useState<Edge[]>(flow.edges);

  const onConnect = (params: Edge | Connection) =>
    setEdges((eds) => addEdge(params, eds));

  return (
    <Card
      shadow="lg"
      radius="xl"
      withBorder
      style={{
        borderColor: "#4F8A8B",
        borderWidth: "2px",
        background: "#F4FFFD",
        width: 400, // Square card dimensions
        height: 400,
        textAlign: "center",
      }}
    >
      <Stack spacing="xs">
        <Title order={3} style={{ fontWeight: "700", color: "#4F8A8B" }}>
          {title}
        </Title>
        <div
          style={{
            height: 200,
            width: "100%",
            position: "relative",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onConnect={onConnect}
            zoomOnScroll={false}
            zoomOnPinch={false}
            zoomOnDoubleClick={false}
            panOnScroll={false}
            panOnDrag={false}
            preventScrolling={true}
            fitView
            minZoom={1}
            maxZoom={1}
            style={{ pointerEvents: "none" }}
          >
            <Background color="#ddd" gap={16} />
          </ReactFlow>
        </div>
        <Text size="sm" mt="md">
          {description}
        </Text>
      </Stack>
    </Card>
  );
};

// Main About Component with improved layout and styles
const About = () => {
  return (
    <Container size="xl" py="xl">
      <Stack spacing="xl" align="center">
        <Title
          align="center"
          order={1}
          style={{
            fontSize: "2.5rem",
            color: "#2C7A7B",
            marginBottom: "1rem",
          }}
        >
          The Agentic Web: AI Systems Biology
        </Title>
        <Text
          align="center"
          size="lg"
          mx="auto"
          maw={800}
          style={{ color: "#4A5568" }}
        >
          Machine intelligence needs protocols to coordinate and grow. These
          protocols, like nature, should be open, permissionless, and neutral.
        </Text>

        <Grid gutter="xl" justify="center">
          <Grid.Col xs={12} sm={6} lg={4}>
            <FlowCard
              title="Biological Systems"
              description="Natural systems demonstrate how individual components work in networks to create emergent behaviors."
              flow={createBioSystemFlow()}
            />
          </Grid.Col>
          <Grid.Col xs={12} sm={6} lg={4}>
            <FlowCard
              title="AI Agent Network"
              description="AI agents operate on blockchain infrastructure, allowing autonomous transactions and resource allocation."
              flow={createAISystemFlow()}
            />
          </Grid.Col>
          <Grid.Col xs={12} sm={6} lg={4}>
            <FlowCard
              title="Marketplace Interaction Flow"
              description="Agents interact with smart contracts to access marketplace resources autonomously."
              flow={createMarketplaceInteractionFlow()}
            />
          </Grid.Col>
          <Grid.Col xs={12} sm={6} lg={4}>
            <FlowCard
              title="Tokenized Workflow Flow"
              description="Tasks initiated by agents are managed by workflow smart contracts and completed by assigned executors."
              flow={createTokenizedWorkflowFlow()}
            />
          </Grid.Col>
        </Grid>

        <Card
          shadow="lg"
          radius="md"
          withBorder
          style={{
            background: "#f7fafc",
            borderColor: "#CBD5E0",
            marginTop: "2rem",
          }}
        >
          <Title order={2} style={{ color: "#2A4365", fontWeight: "700" }}>
            The Future of AI Systems
          </Title>
          <Text size="md" mt="md" style={{ color: "#4A5568" }}>
            AI agents can become significant drivers of economic growth,
            creating an ecosystem where:
          </Text>
          <Stack spacing="md">
            <Text>Agents autonomously transact and fulfill user intents</Text>
            <Text>Blockchain provides structured, transparent data</Text>
            <Text>Smart contracts enable trustless coordination</Text>
            <Text>Tokenized workflows allow for modular processes</Text>
          </Stack>
        </Card>
      </Stack>
    </Container>
  );
};

export default About;
