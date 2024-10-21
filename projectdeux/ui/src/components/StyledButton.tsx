// components/StyledButton.tsx
import React from "react";
import { Button, ButtonProps } from "@mantine/core";
import classes from "./StyledButton.module.css";

interface StyledButtonProps extends ButtonProps {
  // Additional custom props if needed
}

const StyledButton: React.FC<StyledButtonProps> = ({
  children,
  className,
  variant = "filled",
  color = "brand",
  radius = "md",
  size = "md",
  ...props
}) => {
  return (
    <Button
      className={`${classes.styledButton} ${className || ""}`}
      variant={variant}
      color={color}
      radius={radius}
      size={size}
      {...props}
    >
      {children}
    </Button>
  );
};

export default StyledButton;
