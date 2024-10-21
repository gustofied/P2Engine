// HeaderSimple.tsx
import React from "react";
import {
  Container,
  Group,
  Burger,
  Drawer,
  ScrollArea,
  useMantineTheme,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { Link, useLocation } from "react-router-dom";
import classes from "./HeaderSimple.module.css";

const links = [
  { link: "/", label: "HOME" },
  { link: "/app", label: "APP" },
];

export function HeaderSimple() {
  const [drawerOpened, { toggle: toggleDrawer, close: closeDrawer }] =
    useDisclosure(false);
  const location = useLocation();
  const theme = useMantineTheme();

  const items = links.map((link) => {
    const isActive = location.pathname === link.link;
    return (
      <Link
        key={link.label}
        to={link.link}
        className={classes.link}
        data-active={isActive || undefined}
        onClick={closeDrawer} // Close drawer on link click
      >
        {link.label}
      </Link>
    );
  });

  return (
    <header className={classes.header}>
      <Container className={classes.inner}>
        <Link to="/" className={classes.logo}>
          <img src="/logo.png" alt="Logo" height="30" />
        </Link>
        <Group spacing={5} className={classes.links}>
          {items}
        </Group>
        <Burger
          opened={drawerOpened}
          onClick={toggleDrawer}
          className={classes.burger}
          size="sm"
          aria-label="Toggle navigation"
        />
      </Container>

      <Drawer
        opened={drawerOpened}
        onClose={closeDrawer}
        padding="md"
        size="100%"
        className={classes.drawer}
        withCloseButton={false}
        zIndex={1000}
      >
        <div className={classes.drawerHeader}>
          <button className={classes.closeButton} onClick={closeDrawer}>
            &times;
          </button>
        </div>
        <ScrollArea style={{ height: "calc(100vh - 60px)" }}>
          <Container className={classes.drawerContent}>{items}</Container>
        </ScrollArea>
      </Drawer>
    </header>
  );
}
