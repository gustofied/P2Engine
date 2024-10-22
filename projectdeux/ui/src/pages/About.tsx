// pages/About.tsx
import React from "react";
import { Container, Title, Text, Image, Grid, Divider } from "@mantine/core";

const About: React.FC = () => {
  return (
    <Container size="lg" py="xl">
      <Title order={1} align="center" mb="md">
        About Us
      </Title>
      <Divider mb="xl" />
      <Grid gutter="lg" align="center">
        {/* Left Column: Image */}
        <Grid.Col xs={12} md={6}>
          <Image
            src="https://images.unsplash.com/photo-1534126511673-b6899657816a?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60"
            alt="About Image"
            radius="md"
            withPlaceholder
            style={{ width: "100%", height: "auto" }}
          />
        </Grid.Col>
        {/* Right Column: Text */}
        <Grid.Col xs={12} md={6}>
          <Text size="md" color="dimmed" align="center" px="md">
            We are a cutting-edge platform that connects traditional financial
            assets with blockchain-based solutions. Our mission is to bridge
            traditional assets with modern technology, providing a new way to
            invest and trade. Join us in revolutionizing the financial industry.
          </Text>
        </Grid.Col>
      </Grid>
    </Container>
  );
};

export default About;
