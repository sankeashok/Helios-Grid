import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva } from "class-variance-authority"
import { motion } from "framer-motion"
import { cn, hapticFeedback } from "../../lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
        // Premium variants
        glow: "glow-button shadow-glow hover:shadow-glow-lg",
        neon: "bg-black text-energy-neon border border-energy-neon shadow-neon hover:bg-energy-neon hover:text-black transition-all duration-300",
        glass: "glass-card text-white hover:bg-white/20",
        gradient: "gradient-energy text-white font-semibold shadow-lg hover:shadow-xl",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        xl: "h-14 rounded-xl px-10 text-lg",
        icon: "h-10 w-10",
        // Mobile-optimized sizes
        mobile: "h-12 px-6 text-base rounded-xl touch-target",
        "mobile-lg": "h-14 px-8 text-lg rounded-2xl touch-target",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

const Button = React.forwardRef(({ 
  className, 
  variant, 
  size, 
  asChild = false, 
  haptic = "light",
  animate = true,
  children,
  onClick,
  ...props 
}, ref) => {
  const Comp = asChild ? Slot : "button"
  
  const handleClick = (e) => {
    hapticFeedback(haptic);
    if (onClick) onClick(e);
  };

  const buttonContent = (
    <Comp
      className={cn(buttonVariants({ variant, size, className }))}
      ref={ref}
      onClick={handleClick}
      {...props}
    >
      {children}
    </Comp>
  );

  if (!animate) return buttonContent;

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      transition={{ type: "spring", stiffness: 400, damping: 17 }}
    >
      {buttonContent}
    </motion.div>
  );
})
Button.displayName = "Button"

export { Button, buttonVariants }