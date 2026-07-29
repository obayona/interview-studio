import type { ButtonHTMLAttributes, ReactNode } from 'react';

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  variant?: 'primary' | 'secondary' | 'danger';
};

export function Button({
  children,
  variant = 'secondary',
  className = '',
  ...props
}: Props) {
  return (
    <button
      className={`ui-button ui-button--${variant} ${className}`.trim()}
      {...props}
    >
      {children}
    </button>
  );
}
