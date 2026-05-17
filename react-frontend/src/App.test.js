import React from 'react';
import { render } from '@testing-library/react';
import App from './App';

// Mock ResizeObserver for Recharts/Radix components
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

test('renders without crashing', () => {
  // A simple test to prevent the "No tests found" error in CI
  const div = document.createElement('div');
  render(<App />, { container: div });
});
