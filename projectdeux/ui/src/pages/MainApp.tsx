import React, { useState, useEffect } from "react";
import DamlLedger from "@daml/react";
import { useParty, useLedger } from "@daml/react";
import { TestTemplate } from "@daml.js/projectdeux/lib/Test";
import { Party } from "@daml/types";
import { Button, Container, Title, Text } from "@mantine/core";
import { Link } from "react-router-dom";

const MainApp: React.FC = () => {
  const [party, setParty] = useState<Party | null>(null);

  // Hardcoded token
  const token: string =
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJodHRwczovL2RhbWwuY29tL2xlZGdlci1hcGkiOnsibGVkZ2VySWQiOiJzYW5kYm94IiwiYXBwbGljYXRpb25JZCI6Im15LWFwcCIsImFjdEFzIjpbIkFsaWNlOjoxMjIwMmVkNDc1YTc2OGYwOGUyMjUzZWNjZDhhNzhiOWU3OGNkZGVjMzUyNDM4ZjI4YzUxZDdjY2EzNWUxNTgwOTQyMiJdfSwiaWF0IjoxNzI4ODEyMjI1fQ.dxvReCYF91zmS9VVT9stm09kmrhPvbsumxLkeYA2cBI";

  useEffect(() => {
    const fetchPartyIdentifier = async (): Promise<Party> => {
      // Hardcoded party identifier
      return "Alice::12202ed475a768f08e2253eccd8a78b9e78cddec352438f28c51d7cca35e15809422";
    };

    fetchPartyIdentifier().then(setParty);
  }, []);

  if (!party) {
    return (
      <Container>
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
    <Container>
      <p mt="xl">Connected to DAML Ledger as {party}</p>
      <Button onClick={createTestContract} mt="md" variant="filled">
        Create Test Contract
      </Button>
      <Button component={Link} to="/" mt="md" variant="outline">
        Back to Home
      </Button>
    </Container>
  );
};
