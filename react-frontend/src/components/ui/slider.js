import * as React from "react"
import * as SliderPrimitive from "@radix-ui/react-slider"
import { motion } from "framer-motion"
import { cn, hapticFeedback } from "../../lib/utils"

const Slider = React.forwardRef(({ 
  className, 
  variant = "default",
  haptic = true,
  showValue = true,
  label,
  unit = "",
  ...props 
}, ref) => {
  const [value, setValue] = React.useState(props.value || props.defaultValue || [0]);
  
  const variants = {
    default: "",
    neon: "slider-neon",
    glow: "slider-glow",
  };

  const handleValueChange = (newValue) => {
    setValue(newValue);
    if (haptic) hapticFeedback('light');
    if (props.onValueChange) props.onValueChange(newValue);
  };

  return (
    <div className="space-y-3">
      {label && (
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-foreground">
            {label}
          </label>
          {showValue && (
            <motion.span 
              key={value[0]}
              initial={{ scale: 1.2 }}
              animate={{ scale: 1 }}
              className="text-sm font-bold text-primary"
            >
              {value[0]}{unit}
            </motion.span>
          )}
        </div>
      )}
      
      <SliderPrimitive.Root
        ref={ref}
        className={cn(
          "relative flex w-full touch-none select-none items-center mobile-slider",
          className
        )}
        value={value}
        onValueChange={handleValueChange}
        {...props}
      >
        <SliderPrimitive.Track className="relative h-3 w-full grow overflow-hidden rounded-full bg-secondary">
          <SliderPrimitive.Range className="absolute h-full bg-gradient-to-r from-energy-orange to-energy-blue" />
        </SliderPrimitive.Track>
        
        <SliderPrimitive.Thumb className="block h-6 w-6 rounded-full border-2 border-primary bg-background ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 shadow-lg hover:shadow-xl active:scale-110 touch-target" />
      </SliderPrimitive.Root>
      
      {/* Value indicators */}
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{props.min || 0}</span>
        <span>{props.max || 100}</span>
      </div>
    </div>
  )
})
Slider.displayName = SliderPrimitive.Root.displayName

export { Slider }