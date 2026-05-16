import React from 'react';
import { motion } from 'framer-motion';
import { cn, hapticFeedback } from '../lib/utils';

const MobileNav = ({ tabs, activeTab, setActiveTab, theme }) => {
  return (
    <motion.div
      className={cn(
        "fixed bottom-0 left-0 right-0 z-50 border-t backdrop-blur-md transition-all duration-300 mobile-safe-area",
        theme === 'dark-premium' ? 'bg-black/40 border-white/10' :
        theme === 'dark' ? 'bg-gray-900/90 border-gray-700' :
        'bg-white/90 border-gray-200'
      )}
      initial={{ y: 100 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.3, type: "spring", stiffness: 300, damping: 30 }}
    >
      <div className="flex justify-around items-center px-4 py-2">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          
          return (
            <motion.button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id);
                hapticFeedback('medium');
              }}
              className={cn(
                "flex flex-col items-center space-y-1 px-3 py-2 rounded-xl transition-all duration-200 touch-target relative overflow-hidden",
                isActive ? (
                  theme === 'dark-premium' ? 'text-energy-neon bg-energy-neon/10' :
                  theme === 'dark' ? 'text-blue-400 bg-blue-400/10' :
                  'text-orange-600 bg-orange-50'
                ) : (
                  theme === 'dark-premium' ? 'text-gray-400 hover:text-gray-300' :
                  theme === 'dark' ? 'text-gray-400 hover:text-gray-300' :
                  'text-gray-500 hover:text-gray-700'
                )
              )}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              {/* Background glow for active state */}
              {isActive && theme === 'dark-premium' && (
                <motion.div
                  className="absolute inset-0 bg-energy-neon/5 rounded-xl"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  layoutId="activeBackground"
                />
              )}
              
              {/* Icon with enhanced styling */}
              <motion.div
                className="relative"
                animate={isActive ? { scale: [1, 1.2, 1] } : { scale: 1 }}
                transition={{ duration: 0.3 }}
              >
                <Icon className={cn(
                  "h-5 w-5 transition-all duration-200",
                  isActive && theme === 'dark-premium' && 'drop-shadow-[0_0_8px_rgba(0,255,136,0.6)]'
                )} />
                
                {/* Pulse effect for active icon */}
                {isActive && theme === 'dark-premium' && (
                  <motion.div
                    className="absolute inset-0"
                    animate={{ scale: [1, 1.5, 1], opacity: [0.5, 0, 0.5] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  >
                    <Icon className="h-5 w-5 text-energy-neon" />
                  </motion.div>
                )}
              </motion.div>
              
              {/* Label */}
              <span className={cn(
                "text-xs font-medium transition-all duration-200",
                isActive && theme === 'dark-premium' && 'text-shadow-[0_0_8px_rgba(0,255,136,0.8)]'
              )}>
                {tab.label}
              </span>
              
              {/* Active indicator */}
              {isActive && (
                <motion.div
                  className={cn(
                    "absolute -top-1 left-1/2 w-1 h-1 rounded-full transform -translate-x-1/2",
                    theme === 'dark-premium' ? 'bg-energy-neon shadow-neon' :
                    theme === 'dark' ? 'bg-blue-400' :
                    'bg-orange-600'
                  )}
                  layoutId="activeIndicator"
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: "spring", stiffness: 500, damping: 30 }}
                />
              )}
              
              {/* Ripple effect */}
              <motion.div
                className="absolute inset-0 rounded-xl"
                initial={{ scale: 0, opacity: 0.5 }}
                whileTap={{ scale: 2, opacity: 0 }}
                transition={{ duration: 0.3 }}
                style={{
                  background: theme === 'dark-premium' ? 
                    'radial-gradient(circle, rgba(0,255,136,0.3) 0%, transparent 70%)' :
                    theme === 'dark' ?
                    'radial-gradient(circle, rgba(59,130,246,0.3) 0%, transparent 70%)' :
                    'radial-gradient(circle, rgba(249,115,22,0.3) 0%, transparent 70%)'
                }}
              />
            </motion.button>
          );
        })}
      </div>
      
      {/* Bottom safe area for devices with home indicator */}
      <div className="h-safe-area-inset-bottom" />
    </motion.div>
  );
};

export default MobileNav;