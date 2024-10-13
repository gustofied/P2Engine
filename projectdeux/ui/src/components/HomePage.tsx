import React from "react";
import { Link } from "react-router-dom";
import { Button, Container, Title, Text } from "@mantine/core";

const HomePage: React.FC = () => {
  return (
    <Container>
      <Title order={1} align="center" mt="xl">
        Welcome to My Application
      </Title>
      <Text align="center" mt="md">
        This is the homepage of your application.
      </Text>
      <Button component={Link} to="/app" size="md" mt="xl" variant="filled">
        Go to App Page
      </Button>
    </Container>
  );
};

export default HomePage;
