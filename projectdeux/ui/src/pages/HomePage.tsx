// HomePage.tsx
import React from "react";
import { Link } from "react-router-dom";
import {
  Button,
  Container,
  Title,
  Text,
  Image,
  Stack,
  Divider,
} from "@mantine/core";

const HomePage: React.FC = () => {
  return (
    <Container size="md" py="xl">
      <Stack align="center" spacing="lg">
        <Image
          src="https://d7hftxdivxxvm.cloudfront.net/?height=533&quality=85&resize_to=fit&src=https%3A%2F%2Fd32dm0rphc51dk.cloudfront.net%2FKvY4QDon6ukLqc8Ee_zm1Q%2Fnormalized.jpg&width=800" // Place your image in the public folder
          alt="Architectural Design"
          radius="md"
          style={{ maxWidth: 500, width: "100%", height: "auto" }}
        />
        <Title order={1} align="center" mt="md">
          Secondary Market for Tokenized Assets
        </Title>
        <Divider my="sm" variant="solid" />
        <Text align="center" size="md" color="dimmed" px="md">
          Bridging traditional assets with modern technology. Explore a new way
          to invest and trade.
        </Text>
        <Button component={Link} to="/app" size="md" variant="filled" mt="xl">
          Go to Market
        </Button>
      </Stack>
    </Container>
  );
};

export default HomePage;
