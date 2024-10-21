// HeaderSimple.tsx
import React from "react";
import {
  Container,
  Group,
  Burger,
  Paper,
  Transition,
  Image,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { Link, useLocation } from "react-router-dom";
import classes from "./HeaderSimple.module.css";

const links = [
  { link: "/", label: "HOME" },
  { link: "/app", label: "APP" },
];

export function HeaderSimple() {
  const [opened, { toggle }] = useDisclosure(false);
  const location = useLocation();

  const items = links.map((link) => {
    const isActive = location.pathname === link.link;
    return (
      <Link
        key={link.label}
        to={link.link}
        className={classes.link}
        data-active={isActive || undefined}
        onClick={() => {
          if (opened) toggle();
        }}
      >
        {link.label}
      </Link>
    );
  });

  return (
    <header className={classes.header}>
      <Container size="lg" className={classes.inner}>
        <Link to="/" className={classes.logo}>
          <Image src="/logo.png" alt="Logo" height={30} />
        </Link>
        <Group className={classes.linksDesktop}>{items}</Group>
        <Burger
          opened={opened}
          onClick={toggle}
          className={classes.burgerIcon}
          size="sm"
        />
      </Container>

      {/* Mobile menu */}
      <Transition
        mounted={opened}
        transition="slide-down"
        duration={200}
        timingFunction="ease"
      >
        {(styles) => (
          <Paper className={classes.mobileMenu} style={styles}>
            {items}
          </Paper>
        )}
      </Transition>
    </header>
  );
}
