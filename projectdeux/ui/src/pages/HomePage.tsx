import React from "react";
import { Link } from "react-router-dom";
import {
  Container,
  Title,
  Text,
  Image,
  Grid,
  Divider,
  Button,
  Group,
  Stack,
} from "@mantine/core";

const HomePage: React.FC = () => {
  return (
    <Container size="lg" py="xl">
      <Grid gutter="lg" align="center">
        {/* Left Column: Image */}
        <Grid.Col xs={12} md={6}>
          <Image
            src="https://d7hftxdivxxvm.cloudfront.net/?height=533&quality=85&resize_to=fit&src=https%3A%2F%2Fd32dm0rphc51dk.cloudfront.net%2FKvY4QDon6ukLqc8Ee_zm1Q%2Fnormalized.jpg&width=800"
            alt="Architectural Design"
            radius="md"
            withPlaceholder
            style={{ width: "100%", height: "auto" }}
          />
        </Grid.Col>

        {/* Right Column: Text and Buttons */}
        <Grid.Col xs={12} md={6}>
          <div style={{ textAlign: "center" }}>
            <Title order={1} mt="md">
              Secondary Market for Tokenized Assets
            </Title>
            <Divider my="sm" variant="solid" />
            <Text size="md" color="dimmed" px="md">
              Bridging traditional assets with modern technology. Explore a new
              way to invest and trade.
            </Text>
            <Group mt="lg" position="center">
              <Button component={Link} to="/app" size="md" color="darkgray">
                Go to Market
              </Button>
              <Button component={Link} to="/about" size="md" color="darkgray">
                Learn More
              </Button>
            </Group>
          </div>
        </Grid.Col>
      </Grid>

      <Divider my="xl" />

      {/* Additional Section: About Us */}
      <Stack align="center" spacing="xl">
        <Title order={2}>About Us</Title>
        <Text size="sm" color="dimmed" px="md">
          We are a cutting-edge platform that connects traditional financial
          assets with blockchain-based solutions.
        </Text>
        <Button component={Link} to="/get-started" size="md" color="darkgray">
          Get Started
        </Button>
      </Stack>

      <Divider my="xl" />

      {/* Footer Navigation Buttons */}
      <Group position="center" mt="xl">
        <Button component={Link} to="/contact" size="md" color="darkgray">
          Contact Us
        </Button>
        <Button component={Link} to="/faq" size="md" color="darkgray">
          FAQ
        </Button>
      </Group>
    </Container>
  );
};

export default HomePage;
