import React, { useState, useEffect } from "react";
import DamlLedger from "@daml/react";
import { useParty, useLedger } from "@daml/react";
import { TestTemplate } from "@daml.js/projectdeux/lib/Test";
import { Party } from "@daml/types";
import { Button, Container, Text } from "@mantine/core";
import { Link } from "react-router-dom";

const MainApp: React.FC = () => {
  const [party, setParty] = useState<Party | null>(null);

  // Hardcoded token
  const token: string = "your-token-here";

  useEffect(() => {
    const fetchPartyIdentifier = async (): Promise<Party> => {
      // Hardcoded party identifier
      return "Alice::some-hash";
    };

    fetchPartyIdentifier().then(setParty);
  }, []);

  if (!party) {
    return (
      <Container size="lg">
        <Text>Loading...</Text>
      </Container>
    );
  }

  return (
    <DamlLedger token={token} party={party}>
      <Main />
    </DamlLedger>
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
    <Container size="lg" py="xl">
      <Text mt="xl">Connected to DAML Ledger as {party}</Text>
      <Button
        onClick={createTestContract}
        mt="md"
        variant="filled"
        color="darkGray"
      >
        Create Test Contract
      </Button>
      <Button
        component={Link}
        to="/"
        mt="md"
        variant="outline"
        color="darkGray"
      >
        Back to Home
      </Button>
    </Container>
  );
};
