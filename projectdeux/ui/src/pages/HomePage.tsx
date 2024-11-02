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
  Card,
} from "@mantine/core";

const HomePage: React.FC = () => {
  return (
    <Container size="lg" py="xl">
      {/* Centered and Resized Image */}
      <Image
        src="https://d7hftxdivxxvm.cloudfront.net/?height=600&quality=85&resize_to=fit&src=https%3A%2F%2Fd32dm0rphc51dk.cloudfront.net%2FKvY4QDon6ukLqc8Ee_zm1Q%2Fnormalized.jpg&width=900"
        alt="Global Agents Network"
        radius="md"
        withPlaceholder
        style={{
          width: "100%",
          maxWidth: "600px",
          height: "auto",
          margin: "0 auto",
          display: "block",
        }}
      />

      {/* Page Title */}
      <Title
        order={1}
        mt="md"
        align="center"
        style={{
          color: "#2C3E50",
          fontFamily: "Instrument Serif, serif",
          fontSize: "2.5rem",
        }}
      >
        Global Agents Network: An Interoperable World
      </Title>

      {/* Sub Tagline */}
      <Text
        size="lg"
        align="center"
        mt="sm"
        style={{ color: "#4A4A4A", maxWidth: 800, margin: "0 auto" }}
      >
        Employ a multi-agent network for synthetic data generation and agentic
        simulation.
      </Text>

      {/* Call to Action Button */}
      <Group position="center" mt="md">
        <Button
          component={Link}
          to="/app"
          size="md"
          variant="filled"
          color="dark"
          style={{ fontWeight: 600, borderRadius: "5px" }}
        >
          Join the Network
        </Button>
      </Group>

      {/* Divider */}
      <Divider my="xl" />

      {/* Two Info Boxes */}
      <Grid gutter="xl" mt="xl">
        <Grid.Col xs={12} md={6}>
          <Card
            shadow="sm"
            radius="md"
            withBorder
            style={{
              padding: "2rem",
              height: "100%",
              backgroundColor: "#ffffff",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
            }}
          >
            <div>
              <Title
                order={3}
                align="center"
                mt="md"
                style={{ color: "#363946" }}
              >
                Decentralized Agents
              </Title>
              <Text
                size="md"
                mt="sm"
                align="center"
                style={{ color: "#4A4A4A", lineHeight: 1.6 }}
              >
                Empower agents to interact autonomously in a decentralized
                ecosystem.
              </Text>
            </div>
            <Group position="center" mt="md">
              <Button
                component={Link}
                to="/get-started"
                size="sm"
                variant="outline"
                color="dark"
                style={{ borderRadius: "5px" }}
              >
                Learn More
              </Button>
            </Group>
          </Card>
        </Grid.Col>
        <Grid.Col xs={12} md={6}>
          <Card
            shadow="sm"
            radius="md"
            withBorder
            style={{
              padding: "2rem",
              height: "100%",
              backgroundColor: "#ffffff",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
            }}
          >
            <div>
              <Title
                order={3}
                align="center"
                mt="md"
                style={{ color: "#363946" }}
              >
                Interoperable Protocols
              </Title>
              <Text
                size="md"
                mt="sm"
                align="center"
                style={{ color: "#4A4A4A", lineHeight: 1.6 }}
              >
                Build on open protocols that ensure seamless interoperability
                across systems.
              </Text>
            </div>
            <Group position="center" mt="md">
              <Button
                component={Link}
                to="/get-started"
                size="sm"
                variant="outline"
                color="dark"
                style={{ borderRadius: "5px" }}
              >
                Learn More
              </Button>
            </Group>
          </Card>
        </Grid.Col>
      </Grid>

      {/* Divider */}
      <Divider my="xl" />

      {/* Three Larger Info Boxes */}
      <Grid gutter="xl" mt="xl">
        <Grid.Col xs={12} md={4}>
          <Card
            shadow="md"
            radius="md"
            withBorder
            style={{
              padding: "2rem",
              height: "100%",
              backgroundColor: "#ffffff",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
            }}
          >
            <div>
              <Title
                order={3}
                align="center"
                mt="md"
                style={{ color: "#363946" }}
              >
                Various Personas
              </Title>
              <Text
                size="md"
                mt="sm"
                align="center"
                style={{ color: "#4A4A4A", lineHeight: 1.6 }}
              >
                Personas are generated by creating random variables that align
                with the simulation description, followed by generating a
                backstory for each sample.
              </Text>
            </div>
            <Group position="center" mt="md">
              <Button
                component={Link}
                to="/get-started"
                size="sm"
                variant="outline"
                color="dark"
                style={{ borderRadius: "5px" }}
              >
                Get Started
              </Button>
            </Group>
          </Card>
        </Grid.Col>
        <Grid.Col xs={12} md={4}>
          <Card
            shadow="md"
            radius="md"
            withBorder
            style={{
              padding: "2rem",
              height: "100%",
              backgroundColor: "#ffffff",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
            }}
          >
            <div>
              <Title
                order={3}
                align="center"
                mt="md"
                style={{ color: "#363946" }}
              >
                Graphs
              </Title>
              <Text
                size="md"
                mt="sm"
                align="center"
                style={{ color: "#4A4A4A", lineHeight: 1.6 }}
              >
                Get a graph of concepts and their relationships from a given
                context.
              </Text>
            </div>
            <Group position="center" mt="md">
              <Button
                component={Link}
                to="/get-started"
                size="sm"
                variant="outline"
                color="dark"
                style={{ borderRadius: "5px" }}
              >
                Get Started
              </Button>
            </Group>
          </Card>
        </Grid.Col>
        <Grid.Col xs={12} md={4}>
          <Card
            shadow="md"
            radius="md"
            withBorder
            style={{
              padding: "2rem",
              height: "100%",
              backgroundColor: "#ffffff",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
            }}
          >
            <div>
              <Title
                order={3}
                align="center"
                mt="md"
                style={{ color: "#363946" }}
              >
                Retrieval Datasets
              </Title>
              <Text
                size="md"
                mt="sm"
                align="center"
                style={{ color: "#4A4A4A", lineHeight: 1.6 }}
              >
                Obtain a JSON object containing a user query, a relevant
                document, and a hard negative document for a specified text
                retrieval task.
              </Text>
            </div>
            <Group position="center" mt="md">
              <Button
                component={Link}
                to="/get-started"
                size="sm"
                variant="outline"
                color="dark"
                style={{ borderRadius: "5px" }}
              >
                Get Started
              </Button>
            </Group>
          </Card>
        </Grid.Col>
      </Grid>

      {/* Divider */}
      <Divider my="xl" />

      {/* Vision Section */}
      <Title order={2} align="center" mt="xl" style={{ color: "#2C3E50" }}>
        Our Vision
      </Title>
      <Text
        size="md"
        color="dimmed"
        px="md"
        style={{
          maxWidth: 600,
          margin: "0 auto",
          textAlign: "center",
          lineHeight: 1.6,
        }}
      >
        We envision a future where autonomous agents collaborate and transact
        seamlessly across a decentralized network, driving innovation and
        growth.
      </Text>

      {/* Divider */}
      <Divider my="xl" />

      {/* About Us Section */}
      <Title order={2} align="center" mt="xl" style={{ color: "#2C3E50" }}>
        About Us
      </Title>
      <Text
        size="md"
        color="dimmed"
        px="md"
        style={{
          maxWidth: 600,
          margin: "0 auto",
          textAlign: "center",
          lineHeight: 1.6,
        }}
      >
        We are a cutting-edge platform that connects traditional financial
        assets with blockchain-based solutions.
      </Text>

      {/* Footer Navigation Buttons */}
      <Group position="center" mt="md">
        <Button
          component={Link}
          to="/get-started"
          size="md"
          variant="filled"
          color="dark"
          style={{ fontWeight: 600, borderRadius: "5px" }}
        >
          Get Started
        </Button>
        <Button
          component={Link}
          to="/contact"
          size="md"
          variant="subtle"
          color="dark"
          style={{ borderRadius: "5px" }}
        >
          Contact Us
        </Button>
        <Button
          component={Link}
          to="/faq"
          size="md"
          variant="subtle"
          color="dark"
          style={{ borderRadius: "5px" }}
        >
          FAQ
        </Button>
      </Group>

      {/* NTNU Logo */}
      <Divider my="xl" />
      <Group position="center" mt="lg">
        <Image
          src="https://i.ntnu.no/documents/1305837853/1306916684/ntnu_hoeyde_eng.png/9130ea3c-828a-497e-b469-df0c54e16bb5?t=1578568440350"
          alt="NTNU Logo"
          style={{ width: "150px", height: "auto" }}
        />
      </Group>
    </Container>
  );
};

export default HomePage;
