import { Radio, Typography } from 'antd';

import type { IGenerationOption } from '../../types';
import styles from './OptionSelector.module.css';

const { Text } = Typography;

interface IOptionSelectorProps {
    label: string;
    required?: boolean;
    value: string | null;
    options: IGenerationOption[];
    columns?: number;
    onChange: (value: string) => void;
}

function OptionSelector({
    label,
    required = false,
    value,
    options,
    columns,
    onChange,
}: IOptionSelectorProps) {
    return (
        <div className={styles.root}>
            <Text className={styles.label}>
                {label}
                {required && <span className={styles.required}> *</span>}
            </Text>

            <Radio.Group
                value={value}
                onChange={(event) => onChange(event.target.value)}
                className={styles.group}
                style={{
                    gridTemplateColumns: columns
                        ? `repeat(${columns}, 1fr)`
                        : undefined,
                }}
            >
                {options.map((option) => (
                    <Radio.Button
                        key={option.value}
                        value={option.value}
                        className={styles.option}
                    >
                        {option.label}
                    </Radio.Button>
                ))}
            </Radio.Group>
        </div>
    );
}

export default OptionSelector;
