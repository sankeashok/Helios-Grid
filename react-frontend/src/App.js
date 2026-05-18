import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Toaster, toast } from 'react-hot-toast';
import { 
  Sun, 
  Zap, 
  TrendingUp, 
  Activity, 
  Smartphone, 
  Monitor,
  BarChart3,
  Settings,
  Home,
  BookOpen,
  Sparkles,
  Moon
} from 'lucide-react';
import EnergyPredictor from './components/EnergyPredictor';
import Dashboard from './components/Dashboard';
import MobileNav from './components/MobileNav';
import { Button } from './components/ui/button';
import { cn, isMobileDevice, hapticFeedback } from './lib/utils';
import './index.css';

function App() {
  const [activeTab, setActiveTab] = useState('predictor');
  const [isMobile, setIsMobile] = useState(false);
  const [theme, setTheme] = useState('dark-premium');
  const [systemHealth, setSystemHealth] = useState({
    status: 'healthy',
    version: '1.0.0',
    responseTime: '2.1ms'
  });

  // Detect mobile device and screen size
  useEffect(() => {
    const checkMobile = () => {
      const isMobileScreen = window.innerWidth < 768;
      const isMobileUA = isMobileDevice();
      setIsMobile(isMobileScreen || isMobileUA);
    };
    
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Apply theme to document
  useEffect(() => {
    document.documentElement.className = theme;
  }, [theme]);

  // Check system health
  useEffect(() => {
    const checkHealth = async () => {
      try {
        // Try production server first
        const response = await fetch('http://localhost:3002/health');
        if (response.ok) {
          const data = await response.json();
          setSystemHealth({
            status: data.model_loaded ? 'healthy' : 'unhealthy',
            version: data.model_version || '1.0.0',
            responseTime: '< 200ms',
            mlflow_tracking: data.mlflow_tracking
          });
        }
      } catch (error) {
        // Fallback to mock data if server not available
        console.log('Production server not available - using mock data');
        setSystemHealth({
          status: 'offline',
          version: '1.0.0',
          responseTime: 'N/A'
        });
      }
    };
    
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const tabs = [
    { id: 'predictor', label: 'Predictor', icon: Zap, component: EnergyPredictor },
    { id: 'dashboard', label: 'Dashboard', icon: BarChart3, component: Dashboard },
  ];

  const currentComponent = tabs.find(tab => tab.id === activeTab)?.component || EnergyPredictor;
  const CurrentComponent = currentComponent;

  const toggleTheme = () => {
    const newTheme = theme === 'dark-premium' ? 'dark' : theme === 'dark' ? '' : 'dark-premium';
    setTheme(newTheme);
    hapticFeedback('light');
    
    const themeNames = {
      'dark-premium': '🌟 Premium Dark',
      'dark': '🌙 Dark',
      '': '☀️ Light'
    };
    
    toast.success(`Switched to ${themeNames[newTheme]}`, {
      icon: newTheme === 'dark-premium' ? '🌟' : newTheme === 'dark' ? '🌙' : '☀️',
    });
  };

  return (
    <div className={cn(
      "min-h-screen transition-all duration-500",
      theme === 'dark-premium' ? 'bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900' :
      theme === 'dark' ? 'bg-gradient-to-br from-gray-900 to-gray-800' :
      'bg-gradient-to-br from-blue-50 via-white to-orange-50'
    )}>
      <Toaster 
        position={isMobile ? "top-center" : "top-right"}
        toastOptions={{
          duration: 3000,
          style: {
            background: theme === '' ? '#ffffff' : '#1f2937',
            color: theme === '' ? '#000000' : '#ffffff',
            borderRadius: '12px',
            border: theme === 'dark-premium' ? '1px solid rgba(0, 255, 136, 0.3)' : 'none',
            boxShadow: theme === 'dark-premium' ? '0 0 20px rgba(0, 255, 136, 0.1)' : undefined,
          },
        }}
      />
      
      {/* Enhanced Header */}
      <motion.header 
        className={cn(
          "sticky top-0 z-50 border-b backdrop-blur-md transition-all duration-300",
          theme === 'dark-premium' ? 'bg-black/20 border-white/10' :
          theme === 'dark' ? 'bg-gray-900/80 border-gray-700' :
          'bg-white/80 border-gray-200'
        )}
        initial={{ y: -100 }}
        animate={{ y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Enhanced Logo */}
            <motion.div 
              className="flex items-center space-x-3"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <div className="relative">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                >
                  <Sun className={cn(
                    "h-8 w-8",
                    theme === 'dark-premium' ? 'text-energy-neon' : 'text-orange-500'
                  )} />
                </motion.div>
                <motion.div
                  className="absolute inset-0"
                  animate={{ rotate: -360 }}
                  transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
                >
                  <Sparkles className={cn(
                    "h-8 w-8 opacity-50",
                    theme === 'dark-premium' ? 'text-purple-400' : 'text-orange-300'
                  )} />
                </motion.div>
              </div>
              <div>
                <h1 className={cn(
                  "text-xl font-bold",
                  theme === 'dark-premium' ? 'text-energy-neon animate-neon-glow' :
                  theme === 'dark' ? 'text-white' :
                  'bg-gradient-to-r from-orange-500 to-blue-600 bg-clip-text text-transparent'
                )}>
                  Helios-Grid
                </h1>
                {!isMobile && (
                  <p className={cn(
                    "text-xs",
                    theme === 'dark-premium' ? 'text-gray-400' :
                    theme === 'dark' ? 'text-gray-400' :
                    'text-gray-500'
                  )}>
                    Energy MLOps Pipeline
                  </p>
                )}
              </div>
            </motion.div>

            {/* Desktop Navigation */}
            {!isMobile && (
              <nav className="flex space-x-1">
                {tabs.map((tab) => {
                  const Icon = tab.icon;
                  const isActive = activeTab === tab.id;
                  return (
                    <motion.div key={tab.id}>
                      <Button
                        variant={isActive ? (theme === 'dark-premium' ? 'neon' : 'default') : 'ghost'}
                        onClick={() => {
                          setActiveTab(tab.id);
                          hapticFeedback('light');
                        }}
                        className={cn(
                          "flex items-center space-x-2",
                          isActive && theme === 'dark-premium' && 'shadow-neon'
                        )}
                      >
                        <Icon className="h-4 w-4" />
                        <span className="font-medium">{tab.label}</span>
                      </Button>
                    </motion.div>
                  );
                })}
              </nav>
            )}

            {/* Enhanced System Status & Controls */}
            <div className="flex items-center space-x-3">
              {/* Theme Toggle */}
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleTheme}
                className={cn(
                  "relative overflow-hidden",
                  theme === 'dark-premium' && 'hover:bg-white/10'
                )}
              >
                <AnimatePresence mode="wait">
                  {theme === 'dark-premium' ? (
                    <motion.div
                      key="premium"
                      initial={{ rotate: -90, opacity: 0 }}
                      animate={{ rotate: 0, opacity: 1 }}
                      exit={{ rotate: 90, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      <Sparkles className="h-4 w-4 text-energy-neon" />
                    </motion.div>
                  ) : theme === 'dark' ? (
                    <motion.div
                      key="dark"
                      initial={{ rotate: -90, opacity: 0 }}
                      animate={{ rotate: 0, opacity: 1 }}
                      exit={{ rotate: 90, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      <Moon className="h-4 w-4" />
                    </motion.div>
                  ) : (
                    <motion.div
                      key="light"
                      initial={{ rotate: -90, opacity: 0 }}
                      animate={{ rotate: 0, opacity: 1 }}
                      exit={{ rotate: 90, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      <Sun className="h-4 w-4" />
                    </motion.div>
                  )}
                </AnimatePresence>
              </Button>

              {/* System Health */}
              <motion.div
                className="flex items-center space-x-2"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
              >
                <div className={cn(
                  "w-2 h-2 rounded-full animate-pulse",
                  systemHealth.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'
                )} />
                {!isMobile && (
                  <span className={cn(
                    "text-sm",
                    theme === 'dark-premium' ? 'text-gray-300' :
                    theme === 'dark' ? 'text-gray-300' :
                    'text-gray-600'
                  )}>
                    {systemHealth.responseTime}
                  </span>
                )}
              </motion.div>
              
              {/* Device Indicator */}
              <motion.div
                className={cn(
                  "p-2 rounded-lg transition-colors",
                  theme === 'dark-premium' ? 'bg-white/10 text-gray-300' :
                  theme === 'dark' ? 'bg-gray-800 text-gray-300' :
                  'bg-gray-100 text-gray-600'
                )}
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
              >
                {isMobile ? <Smartphone className="h-4 w-4" /> : <Monitor className="h-4 w-4" />}
              </motion.div>
            </div>
          </div>
        </div>
      </motion.header>

      {/* Main Content */}
      <main className={cn(
        "transition-all duration-300",
        isMobile ? "pb-20" : "pb-6" // Account for mobile nav
      )}>
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            <CurrentComponent isMobile={isMobile} theme={theme} />
          </motion.div>
        </AnimatePresence>
      </main>

      {/* Enhanced Mobile Navigation */}
      {isMobile && (
        <MobileNav 
          tabs={tabs}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          theme={theme}
        />
      )}

      {/* Enhanced Footer */}
      {!isMobile && (
        <footer className={cn(
          "border-t mt-12 transition-colors",
          theme === 'dark-premium' ? 'bg-black/20 border-white/10' :
          theme === 'dark' ? 'bg-gray-900 border-gray-700' :
          'bg-gray-50 border-gray-200'
        )}>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="flex flex-col sm:flex-row justify-between items-center space-y-4 sm:space-y-0">
              <div className="flex items-center space-x-4">
                <span className={cn(
                  "text-sm",
                  theme === 'dark-premium' ? 'text-gray-300' :
                  theme === 'dark' ? 'text-gray-300' :
                  'text-gray-600'
                )}>
                  Powered by Helios-Grid MLOps Pipeline
                </span>
                <div className="flex items-center space-x-2">
                  <Activity className={cn(
                    "h-4 w-4",
                    systemHealth.status === 'healthy' ? 'text-green-500' : 'text-red-500'
                  )} />
                  <span className={cn(
                    "text-xs",
                    theme === 'dark-premium' ? 'text-gray-400' :
                    theme === 'dark' ? 'text-gray-400' :
                    'text-gray-500'
                  )}>
                    v{systemHealth.version}
                  </span>
                </div>
              </div>
              
              <div className="flex items-center space-x-4">
                <a 
                  href="https://github.com/sankeashok/Helios-Grid" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className={cn(
                    "text-sm transition-colors hover:underline",
                    theme === 'dark-premium' ? 'text-energy-neon hover:text-energy-neon/80' :
                    theme === 'dark' ? 'text-blue-400 hover:text-blue-300' :
                    'text-blue-600 hover:text-blue-800'
                  )}
                >
                  GitHub
                </a>
                <a 
                  href="https://hub.docker.com/r/sankeashok/helios-grid" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className={cn(
                    "text-sm transition-colors hover:underline",
                    theme === 'dark-premium' ? 'text-energy-neon hover:text-energy-neon/80' :
                    theme === 'dark' ? 'text-blue-400 hover:text-blue-300' :
                    'text-blue-600 hover:text-blue-800'
                  )}
                >
                  Docker Hub
                </a>
              </div>
            </div>
          </div>
        </footer>
      )}
    </div>
  );
}

export default App;