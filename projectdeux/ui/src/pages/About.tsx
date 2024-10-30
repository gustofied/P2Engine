import React, { useState } from "react";
import { Container, Title, Stack } from "@mantine/core";
import ReactFlow, {
  Background,
  addEdge,
  Edge,
  Connection,
  Node,
} from "react-flow-renderer";
import "react-flow-renderer/dist/style.css";

// Define `Elements` as a union type of `Node` and `Edge` arrays
type Elements = (Node | Edge)[];

const About: React.FC = () => {
  const initialElements: Elements = [
    {
      id: "1",
      type: "input",
      data: { label: "Welcome to React Flow!" },
      position: { x: 250, y: 0 },
    } as Node,
    {
      id: "2",
      data: { label: "This is a default node" },
      position: { x: 100, y: 100 },
    } as Node,
    {
      id: "3",
      data: { label: "Custom style node" },
      position: { x: 400, y: 100 },
      style: {
        background: "#D6D5E6",
        color: "#333",
        border: "1px solid #222138",
        width: 180,
      },
    } as Node,
    {
      id: "4",
      data: { label: "Another default node" },
      position: { x: 250, y: 200 },
    } as Node,
    {
      id: "5",
      data: { label: "Node ID: 5" },
      position: { x: 250, y: 325 },
    } as Node,
    {
      id: "6",
      type: "output",
      data: { label: "Output node" },
      position: { x: 100, y: 480 },
    } as Node,
    {
      id: "7",
      type: "output",
      data: { label: "Another output node" },
      position: { x: 400, y: 450 },
    } as Node,
    { id: "e1-2", source: "1", target: "2", label: "Edge label" } as Edge,
    { id: "e1-3", source: "1", target: "3" } as Edge,
    {
      id: "e3-4",
      source: "3",
      target: "4",
      animated: true,
      label: "Animated edge",
    } as Edge,
    {
      id: "e4-5",
      source: "4",
      target: "5",
      arrowHeadType: "arrowclosed",
      label: "Edge with arrow",
    } as Edge,
    {
      id: "e5-6",
      source: "5",
      target: "6",
      type: "smoothstep",
      label: "Smooth step edge",
    } as Edge,
    {
      id: "e5-7",
      source: "5",
      target: "7",
      type: "step",
      style: { stroke: "#f6ab6c" },
      label: "Step edge",
      animated: true,
      labelStyle: { fill: "#f6ab6c", fontWeight: 700 },
    } as Edge,
  ];

  const [nodes, setNodes] = useState<Node[]>(
    initialElements.filter((el) => "position" in el) as Node[]
  );
  const [edges, setEdges] = useState<Edge[]>(
    initialElements.filter((el) => "source" in el) as Edge[]
  );

  const onConnect = (params: Edge | Connection) =>
    setEdges((eds) => addEdge(params, eds));

  return (
    <Container size="lg" py="xl">
      <style>
        {`
          .react-flow__attribution {
            display: none;
          }
        `}
      </style>
      <Stack align="center" spacing="xl" py="xl">
        <Title order={2}>Trading Workflow</Title>
        <Container size="md" style={{ width: "100%", height: 500 }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onConnect={onConnect}
            deleteKeyCode="Delete" // Use "Delete" key to delete elements
            fitView
          >
            <Background color="#aaa" gap={16} />
          </ReactFlow>
        </Container>
      </Stack>
    </Container>
  );
};

export default About;
