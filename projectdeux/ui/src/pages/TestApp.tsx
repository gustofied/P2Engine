// pages/MainApp.tsx
import React, { useState, useEffect } from "react";
import DamlLedger from "@daml/react";
import { useParty, useLedger } from "@daml/react";
import { TestTemplate } from "@daml.js/projectdeux/lib/Test";
import { Party } from "@daml/types";
import {
  Button,
  Container,
  Text,
  Group,
  Loader,
  Title,
  Paper,
} from "@mantine/core";
import { Link } from "react-router-dom";

const TestApp: React.FC = () => {
  const [party, setParty] = useState<Party | null>(null);

  // Hardcoded token
  const token: string = "your-token-here";

  useEffect(() => {
    const fetchPartyIdentifier = async (): Promise<Party> => {
      // Hardcoded party identifier
      return "Alice::some-hashhashvhashhashhashhashhash";
    };

    fetchPartyIdentifier().then(setParty);
  }, []);

  if (!party) {
    return (
      <Container size="lg" style={{ textAlign: "center", marginTop: "10%" }}>
        <Loader size="lg" variant="bars" />
        <Text mt="md" size="md" color="dimmed">
          Connecting to DAML Ledger...
        </Text>
      </Container>
    );
  }

  return (
    <>
      <DamlLedger token={token} party={party}>
        <Main />
      </DamlLedger>
    </>
  );
};

export default TestApp;

const Main: React.FC = () => {
  const party = useParty();
  const ledger = useLedger();

  const createTestContract = async () => {
    try {
      await ledger.create(TestTemplate, { owner: party });
      alert("Test contract created successfully!");
    } catch (error) {
      console.error("Error creating test contract:", error);
      alert(`Error creating test contract: ${error}`);
    }
  };

  return (
    <Container size="lg" py="xl" style={{ textAlign: "center" }}>
      <Paper
        shadow="sm"
        p="md"
        style={{
          height: "80vh",
          width: "120%",
          marginLeft: "-10%",
          marginRight: "-10%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          backgroundColor: "transparent",
          border: "1px solid #ccc",
          borderRadius: "8px",
        }}
      >
        <div>
          <Title order={2} mt="xl">
            Welcome, {party}!
          </Title>
          <Text mt="md" size="md" color="dimmed">
            You are connected to the DAML Ledger as <strong>{party}</strong>.
            Use the buttons below to interact with the ledger.
          </Text>
        </div>
        <Group position="center" spacing="md" mt="xl">
          <Button onClick={createTestContract}>Create Test Contract</Button>
          <Button component={Link} to="/">
            Back to Home
          </Button>
        </Group>
      </Paper>
    </Container>
  );
};
