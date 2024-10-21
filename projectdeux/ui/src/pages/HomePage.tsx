// HomePage.tsx
import React from "react";
import { Link } from "react-router-dom";
import {
  Button,
  Container,
  Title,
  Text,
  Image,
  Grid,
  Divider,
} from "@mantine/core";

const HomePage: React.FC = () => {
  return (
    <Container size="md" py="xl">
      <Grid gutter="lg" align="center">
        <Grid.Col xs={12} md={6}>
          <Image
            src="https://d7hftxdivxxvm.cloudfront.net/?height=533&quality=85&resize_to=fit&src=https%3A%2F%2Fd32dm0rphc51dk.cloudfront.net%2FKvY4QDon6ukLqc8Ee_zm1Q%2Fnormalized.jpg&width=800"
            alt="Architectural Design"
            radius="md"
            withPlaceholder
          />
        </Grid.Col>
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
            <Button
              component={Link}
              to="/app"
              size="md"
              mt="xl"
              sx={{
                backgroundColor: "#363946",
                color: "#fff", // Text color to be white
                "&:hover": {
                  backgroundColor: "#4b4f5e", // Slightly lighter gray on hover
                },
              }}
            >
              Go to Market
            </Button>
          </div>
        </Grid.Col>
      </Grid>
    </Container>
  );
};

export default HomePage;
