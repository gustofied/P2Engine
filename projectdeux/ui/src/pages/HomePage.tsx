// pages/HomePage.tsx

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
  Card,
} from "@mantine/core";

const HomePage: React.FC = () => {
  return (
    <Container size="lg" py="xl">
      <Stack align="center" spacing="xl">
        {/* Centered and Enlarged Image */}
        <Image
          src="https://d7hftxdivxxvm.cloudfront.net/?height=800&quality=85&resize_to=fit&src=https%3A%2F%2Fd32dm0rphc51dk.cloudfront.net%2FKvY4QDon6ukLqc8Ee_zm1Q%2Fnormalized.jpg&width=1200"
          alt="Global Agents Network"
          radius="md"
          withPlaceholder
          style={{ width: "100%", maxWidth: "800px", height: "auto" }}
        />
        {/* New Title Under Image */}
        <Title order={1} mt="md" align="center">
          Global Agents Network: An Interoperable World
        </Title>
        {/* Call to Action Button */}
        <Button
          component={Link}
          to="/app"
          size="md"
          variant="filled"
          color="darkGray"
          mt="md"
        >
          Join the Network
        </Button>

        {/* Divider between sections */}
        <Divider my="xl" color="gray" />

        {/* Two Info Boxes Side by Side */}
        <Grid gutter="xl" mt="xl">
          <Grid.Col xs={12} md={6}>
            <Card shadow="md" radius="md" withBorder>
              <Title order={3} align="center" mt="md">
                Decentralized Agents
              </Title>
              <Text size="md" mt="sm" align="center">
                Empower agents to interact autonomously in a decentralized
                ecosystem.
              </Text>
            </Card>
          </Grid.Col>
          <Grid.Col xs={12} md={6}>
            <Card shadow="md" radius="md" withBorder>
              <Title order={3} align="center" mt="md">
                Interoperable Protocols
              </Title>
              <Text size="md" mt="sm" align="center">
                Build on open protocols that ensure seamless interoperability
                across systems.
              </Text>
            </Card>
          </Grid.Col>
        </Grid>

        {/* Divider between sections */}
        <Divider my="xl" color="gray" />

        {/* Additional Information Section */}
        <Stack align="center" spacing="xl">
          <Title order={2}>Our Vision</Title>
          <Text size="md" color="dimmed" px="md" maw={600} align="center">
            We envision a future where autonomous agents collaborate and
            transact seamlessly across a decentralized network, driving
            innovation and growth.
          </Text>
        </Stack>

        {/* Divider between sections */}

        {/* Existing About Us Section */}
        <Stack align="center" spacing="xl">
          <Title order={2}>About Us</Title>
          <Text size="md" color="dimmed" px="md" maw={600} align="center">
            We are a cutting-edge platform that connects traditional financial
            assets with blockchain-based solutions.
          </Text>
          <Button
            component={Link}
            to="/get-started"
            size="md"
            variant="filled"
            color="darkGray"
          >
            Get Started
          </Button>
        </Stack>

        {/* Divider between sections */}
        <Divider my="xl" color="gray" />

        {/* Footer Navigation Buttons */}
        <Group position="center" mt="xl">
          <Button
            component={Link}
            to="/contact"
            size="md"
            variant="subtle"
            color="darkGray"
          >
            Contact Us
          </Button>
          <Button
            component={Link}
            to="/faq"
            size="md"
            variant="subtle"
            color="darkGray"
          >
            FAQ
          </Button>
        </Group>
      </Stack>
    </Container>
  );
};

export default HomePage;
