// pages/MainApp.tsx

import React, { useState, useEffect } from "react";
import {
  Container,
  Text,
  Loader,
  Image,
  Title,
  Paper,
  Box,
} from "@mantine/core";

const MainApp: React.FC = () => {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate loading process for a brief moment
    const timer = setTimeout(() => setLoading(false), 1000);
    return () => clearTimeout(timer);
  }, []);

  if (loading) {
    return (
      <Container size="lg" style={{ textAlign: "center", marginTop: "10%" }}>
        <Loader size="lg" variant="bars" />
        <Text mt="md" size="md" color="dimmed">
          Connecting to Testnet...
        </Text>
      </Container>
    );
  }

  return (
    <Container
      size="lg"
      py="xl"
      style={{ display: "flex", justifyContent: "center" }}
    >
      <Paper
        shadow="md"
        p="xl"
        style={{
          width: "120%",
          minHeight: "70vh",
          textAlign: "center",
          backgroundColor: "#ffffff",
          border: "1px solid #e0e0e0",
          borderRadius: "8px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
        }}
      >
        <Title order={1} mb="lg">
          Testnet Under Development{" "}
        </Title>
        <Text size="md" color="dimmed" mb="xl">
          Built with DAML, deployed on the Canton Network. Stay tuned, we’re
          going live on testnet soon!
        </Text>
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <Box style={{ width: "auto", paddingRight: "4px" }}>
            <a
              href="https://www.digitalasset.com/developers"
              target="_blank"
              rel="noopener noreferrer"
            >
              <Image
                src="https://store-images.s-microsoft.com/image/apps.34431.e186ae4b-0bb8-4c56-b62f-73adbc782b49.e173908c-9376-445d-9cf2-5582e82b5b55.6897edf1-de16-4d72-959e-035ebb037727"
                alt="DAML Logo"
                height={75}
                fit="contain"
              />
            </a>
          </Box>
          <Box style={{ width: "auto", paddingLeft: "4px" }}>
            <a
              href="https://www.canton.network/"
              target="_blank"
              rel="noopener noreferrer"
            >
              <Image
                src="https://pbs.twimg.com/profile_images/1654160655975342080/Eev_0MNs_400x400.png"
                alt="Canton Network Logo"
                height={75}
                fit="contain"
              />
            </a>
          </Box>
        </div>
      </Paper>
    </Container>
  );
};

export default MainApp;
