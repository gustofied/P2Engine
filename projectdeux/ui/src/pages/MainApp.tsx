import React, { useState, useEffect } from "react";
import DamlLedger from "@daml/react";
import { useParty, useLedger } from "@daml/react";
import { TestTemplate } from "@daml.js/projectdeux/lib/Test";
import { Party } from "@daml/types";
import {
  Button,
  Container,
  Text,
  Header,
  Group,
  Loader,
  Title,
  Space,
} from "@mantine/core";
import { Link } from "react-router-dom";

const MainApp: React.FC = () => {
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

export default MainApp;

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
    <Container size="md" py="xl" style={{ textAlign: "center" }}>
      <Title order={2} mt="xl">
        Welcome, {party}!
      </Title>
      <Text mt="md" size="md" color="dimmed">
        You are connected to the DAML Ledger as <strong>{party}</strong>. Use
        the button below to create a test contract.
      </Text>
      <Space h="lg" />
      <Group position="center" spacing="md">
        <Button onClick={createTestContract} mt="md" color="teal">
          Create Test Contract
        </Button>
        <Button component={Link} to="/" mt="md" variant="outline" color="gray">
          Back to Home
        </Button>
      </Group>
    </Container>
  );
};
