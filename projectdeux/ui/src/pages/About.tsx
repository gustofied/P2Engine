// pages/About.tsx
import React, { useState } from "react";
import {
  Container,
  Title,
  Text,
  Image,
  Grid,
  Divider,
  Paper,
  Button,
  Group,
  ThemeIcon,
  Card,
  Avatar,
} from "@mantine/core";
import {
  FaRocket,
  FaCheck,
  FaUsers,
  FaArrowRight,
  FaRegStar,
} from "react-icons/fa";

const testimonials = [
  "This platform has completely transformed my investment journey. I feel more confident and secure in every trade. Thank you for building something so impactful! - Emily L.",
  "The user experience is fantastic, and the support team is always there to help. I’ve recommended this platform to many of my friends. - Michael B.",
  "Secure, efficient, and innovative. This platform is exactly what I was looking for to diversify my investments. - Sarah T.",
];

const About: React.FC = () => {
  const [activeIndex, setActiveIndex] = useState(0);

  const handleNext = () => {
    setActiveIndex((prevIndex) => (prevIndex + 1) % testimonials.length);
  };

  const handlePrev = () => {
    setActiveIndex(
      (prevIndex) => (prevIndex - 1 + testimonials.length) % testimonials.length
    );
  };

  return (
    <Container size="lg" py="xl">
      <Title order={1} align="center" mb="md">
        About Us
      </Title>
      <Divider mb="xl" />

      {/* Our Story Section */}
      <Title order={2} align="center" mt="xl" mb="md">
        Our Story
      </Title>
      <Text size="md" color="dimmed" align="center" px="xl" mb="xl">
        Founded in 2020, our platform was born out of a vision to bridge the gap
        between traditional finance and the rapidly evolving world of
        blockchain. What started as a small team with a big idea has grown into
        a trusted and innovative platform, transforming the financial landscape.
        We’re dedicated to providing secure, transparent, and efficient
        solutions for investors around the globe.
      </Text>

      <Divider my="xl" />

      {/* Our Vision Section */}
      <Title order={2} align="center" mt="xl" mb="md">
        Our Vision
      </Title>
      <Text size="md" color="dimmed" align="center" px="xl" mb="xl">
        Our vision is to empower individuals and businesses with accessible,
        trustworthy, and efficient tools that redefine financial freedom and
        opportunity. We envision a world where every financial interaction is
        seamless, secure, and rewarding.
      </Text>

      <Divider my="xl" />

      {/* Image Section */}
      <Grid gutter="lg" align="center" mb="xl">
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
            We are a cutting-edge platform that bridges traditional financial
            assets with blockchain technology. Our mission is to revolutionize
            financial systems, providing innovative ways for individuals and
            institutions to invest and trade securely and efficiently.
          </Text>
          <Text size="md" color="dimmed" align="center" mt="md" px="md">
            By combining robust technological expertise with a deep
            understanding of financial markets, we aim to empower users with a
            seamless, secure, and dynamic investment experience.
          </Text>
        </Grid.Col>
      </Grid>

      <Divider my="xl" />

      {/* Values Section */}
      <Title order={2} align="center" mt="xl" mb="lg">
        Our Values
      </Title>
      <Grid gutter="lg" align="center">
        {/* Innovation Card */}
        <Grid.Col xs={12} md={4}>
          <Paper withBorder shadow="md" p="md" radius="md">
            <Group align="center" position="center">
              <ThemeIcon color="blue" radius="xl" size="xl">
                <FaRocket size={30} />
              </ThemeIcon>
            </Group>
            <Text align="center" weight={700} size="lg" mt="md">
              Innovation
            </Text>
            <Text size="sm" color="dimmed" align="center" mt="sm">
              We strive to stay at the forefront of technology, continually
              innovating to provide the best solutions for modern finance.
            </Text>
          </Paper>
        </Grid.Col>

        {/* Integrity Card */}
        <Grid.Col xs={12} md={4}>
          <Paper withBorder shadow="md" p="md" radius="md">
            <Group align="center" position="center">
              <ThemeIcon color="green" radius="xl" size="xl">
                <FaCheck size={30} />
              </ThemeIcon>
            </Group>
            <Text align="center" weight={700} size="lg" mt="md">
              Integrity
            </Text>
            <Text size="sm" color="dimmed" align="center" mt="sm">
              We prioritize transparency and honesty, ensuring that every
              decision and solution serves the best interest of our clients.
            </Text>
          </Paper>
        </Grid.Col>

        {/* Community Card */}
        <Grid.Col xs={12} md={4}>
          <Paper withBorder shadow="md" p="md" radius="md">
            <Group align="center" position="center">
              <ThemeIcon color="purple" radius="xl" size="xl">
                <FaUsers size={30} />
              </ThemeIcon>
            </Group>
            <Text align="center" weight={700} size="lg" mt="md">
              Community
            </Text>
            <Text size="sm" color="dimmed" align="center" mt="sm">
              Our platform is built for people, and we believe in creating a
              supportive and inclusive financial community.
            </Text>
          </Paper>
        </Grid.Col>
      </Grid>

      <Divider my="xl" />

      {/* Impact Section */}
      <Title order={2} align="center" mt="xl" mb="md">
        Our Impact
      </Title>
      <Text size="sm" color="dimmed" align="center" mb="xl">
        <ul>
          <li>Over 1 million trades executed</li>
          <li>Trusted by 10,000+ users worldwide</li>
          <li>Achieved 99.9% uptime and secure transactions</li>
        </ul>
      </Text>

      <Divider my="xl" />

      {/* Testimonials Section */}
      <Title order={2} align="center" mt="xl" mb="lg">
        What Our Users Say
      </Title>
      <Group position="center" mb="md">
        <Button variant="outline" onClick={handlePrev}>
          Previous
        </Button>
        <Button variant="outline" onClick={handleNext}>
          Next
        </Button>
      </Group>
      <Paper shadow="md" p="md" radius="md" withBorder>
        <Text size="sm" color="dimmed" align="center">
          {testimonials[activeIndex]}
        </Text>
      </Paper>

      <Divider my="xl" />

      {/* Customer Support Section */}
      <Title order={2} align="center" mt="xl" mb="md">
        Dedicated Customer Support
      </Title>
      <Text size="md" color="dimmed" align="center" px="xl" mb="lg">
        Our team is here to help every step of the way. We are committed to
        providing reliable, round-the-clock support to answer questions and
        resolve issues quickly and efficiently.
      </Text>

      <Divider my="xl" />

      {/* Call to Action */}
      <Title order={2} align="center" mt="xl" mb="lg">
        Get in Touch
      </Title>
      <Text size="md" color="dimmed" align="center" px="xl" mb="lg">
        Want to learn more about our platform, get involved, or collaborate with
        us? Reach out, and let’s build the future of finance together.
      </Text>

      <Group position="center">
        <Button
          rightIcon={<FaArrowRight />}
          variant="gradient"
          gradient={{ from: "indigo", to: "cyan" }}
        >
          Contact Us
        </Button>
      </Group>
    </Container>
  );
};

export default About;
