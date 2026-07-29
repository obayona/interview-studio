import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Switch } from './Switch';

describe('Switch', () => {
  it('exposes its state and responds to keyboard-accessible button activation', () => {
    const onChange = vi.fn();
    render(
      <Switch label="Voice responses" checked={false} onChange={onChange} />,
    );

    const control = screen.getByRole('switch', { name: 'Voice responses' });
    expect(control).toHaveAttribute('aria-checked', 'false');
    fireEvent.click(control);
    expect(onChange).toHaveBeenCalledWith(true);
  });
});
