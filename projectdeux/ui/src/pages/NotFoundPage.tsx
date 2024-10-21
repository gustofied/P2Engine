// pages/NotFoundPage.tsx
import React from "react";
import { Link } from "react-router-dom";
import { Container, Title, Text, Button } from "@mantine/core";

const NotFoundPage: React.FC = () => {
  return (
    <Container size="md" py="xl" style={{ textAlign: "center" }}>
      <Title order={1} mt="md">
        404 - Page Not Found
      </Title>
      <Text size="md" color="dimmed" mt="sm">
        The page you're looking for doesn't exist.
      </Text>
      <Link to="/">
        <Button mt="xl">Go to Home</Button>
      </Link>
    </Container>
  );
};

export default NotFoundPage;
