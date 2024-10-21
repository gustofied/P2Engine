// components/StyledButton.tsx
import React from "react";
import { Button, ButtonProps } from "@mantine/core";

interface StyledButtonProps extends ButtonProps {
  // Additional custom props if needed
}

const StyledButton: React.FC<StyledButtonProps> = ({
  children,
  variant = "filled",
  color = "darkGray", // Set darkGray as default color
  radius = "md",
  size = "md",
  ...props
}) => {
  return (
    <Button
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
