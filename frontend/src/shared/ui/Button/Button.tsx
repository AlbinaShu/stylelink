import { Button as AntButton } from 'antd';
import type { ReactNode } from 'react';
import styles from './Button.module.css';

type ButtonHTMLType = 'button' | 'submit' | 'reset';

interface IButtonProps {
  title: string;
  onClick?: () => void;
  isDisabled?: boolean;
  isLoading?: boolean;
  htmlType?: ButtonHTMLType;
  icon?: ReactNode;
  suffix?: ReactNode;
  className?: string;
  block?: boolean;
}

function Button({
  title,
  onClick,
  isDisabled = false,
  isLoading = false,
  htmlType = 'button',
  icon,
  suffix,
  className = '',
  block = false,
}: IButtonProps) {
  return (
    <AntButton
      type="primary"
      htmlType={htmlType}
      onClick={onClick}
      disabled={isDisabled}
      loading={isLoading}
      icon={icon}
      block={block}
      className={`${styles.button} ${className}`}
    >
      {title}
      {suffix}
    </AntButton>
  );
}

export default Button;
