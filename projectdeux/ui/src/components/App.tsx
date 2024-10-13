import React, { useState, useEffect } from "react";
import DamlLedger from "@daml/react";
import { useParty, useLedger } from "@daml/react";
import { TestTemplate } from "@daml.js/projectdeux/lib/Test";
import { Party } from "@daml/types";

// Get the party id from setup or login (replace 'Alice' with the full party identifier)
const fetchPartyIdentifier = async (): Promise<Party> => {
  return "Alice::12202ed475a768f08e2253eccd8a78b9e78cddec352438f28c51d7cca35e15809422"; // Replace with actual party identifier from DAML Navigator or setup
};

const App: React.FC = () => {
  const [party, setParty] = useState<Party | null>(null);
  const token: string =
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJodHRwczovL2RhbWwuY29tL2xlZGdlci1hcGkiOnsibGVkZ2VySWQiOiJzYW5kYm94IiwiYXBwbGljYXRpb25JZCI6Im15LWFwcCIsImFjdEFzIjpbIkFsaWNlOjoxMjIwMmVkNDc1YTc2OGYwOGUyMjUzZWNjZDhhNzhiOWU3OGNkZGVjMzUyNDM4ZjI4YzUxZDdjY2EzNWUxNTgwOTQyMiJdfSwiaWF0IjoxNzI4ODEyMjI1fQ.dxvReCYF91zmS9VVT9stm09kmrhPvbsumxLkeYA2cBI";

  useEffect(() => {
    // Fetch the correct party identifier
    fetchPartyIdentifier().then(setParty);
  }, []);

  if (!party) {
    return <div>Loading...</div>; // Render loading while waiting for party
  }

  return (
    <DamlLedger token={token} party={party}>
      <Main />
    </DamlLedger>
  );
};

const Main: React.FC = () => {
  const party = useParty();
  const ledger = useLedger();

  const createTestContract = async () => {
    try {
      await ledger.create(TestTemplate, { owner: party });
      alert("Test contract created successfully!");
    } catch (error) {
      console.error(error);
      alert(`Error creating test contract: ${error}`);
    }
  };

  return (
    <div>
      <h1>Connected to DAML Ledger as {party}</h1>
      <button onClick={createTestContract}>Create Test Contract</button>
    </div>
  );
};

export default App;
