import {
  Card,
  Col,
  InputNumber,
  Radio,
  Row,
  Typography,
} from 'antd';

import type { IGenerationForm } from '../../types';
import styles from './BodyParameters.module.css';

const { Text } = Typography;

type BodyValues = Pick<
  IGenerationForm,
  | 'gender'
  | 'height'
  | 'weight'
  | 'shoe_size'
  | 'chest'
  | 'waist'
  | 'hips'
>;

interface IBodyParametersProps {
  value: BodyValues;
  onChange: (
    field: keyof BodyValues,
    value: string | number | null,
  ) => void;
}

function BodyParameters({
  value,
  onChange,
}: IBodyParametersProps) {
  return (
    <div className={styles.root}>
      <Text className={styles.title}>
        Параметры тела <span style={{ color: 'var(--primary)' }}>*</span>
      </Text>

      <Card className={styles.card}>
        <Text className={styles.label}>
          Пол <span style={{ color: 'var(--primary)' }}>*</span>
        </Text>

        <Radio.Group
          value={value.gender}
          onChange={(event) => {
            onChange('gender', event.target.value);
          }}
          className={styles.gender}
        >
          <Radio.Button value="female">
            Женский
          </Radio.Button>

          <Radio.Button value="male">
            Мужской
          </Radio.Button>
        </Radio.Group>

        <Row gutter={[10, 0]} className={styles.fields}>
          <Col xs={12}>
            <Text className={styles.fieldLabel}>
              Рост / см <span style={{ color: 'var(--primary)' }}>*</span>
            </Text>

            <InputNumber
              value={value.height}
              controls={false}
              placeholder="—"
              onChange={(nextValue) => {
                onChange('height', nextValue);
              }}
              className={styles.input}
            />
          </Col>

          <Col xs={12}>
            <Text className={styles.fieldLabel}>
              Вес / кг <span style={{ color: 'var(--primary)' }}>*</span>
            </Text>

            <InputNumber
              value={value.weight}
              controls={false}
              placeholder="—"
              onChange={(nextValue) => {
                onChange('weight', nextValue);
              }}
              className={styles.input}
            />
          </Col>

          <Col xs={12}>
            <Text className={styles.fieldLabel}>
              Размер обуви / RU <span style={{ color: 'var(--primary)' }}>*</span>
            </Text>

            <InputNumber
              value={value.shoe_size}
              min={30}
              max={50}
              step={0.5}
                formatter={(value) =>
                  value == null
                    ? ''
                    : String(Number(value))
                }controls={false}
              placeholder="—"
              onChange={(nextValue) => {
                onChange('shoe_size', nextValue);
              }}
              className={styles.input}
            />
          </Col>

          <Col xs={12}>
            <Text className={styles.fieldLabel}>
              Обхват груди / см <span style={{ color: 'var(--primary)' }}>*</span>
            </Text>

            <InputNumber
              value={value.chest}
              controls={false}
              placeholder="—"
              onChange={(nextValue) => {
                onChange('chest', nextValue);
              }}
              className={styles.input}
            />
          </Col>

          <Col xs={12}>
            <Text className={styles.fieldLabel}>
              Обхват талии / см <span style={{ color: 'var(--primary)' }}>*</span>
            </Text>

            <InputNumber
              value={value.waist}
              controls={false}
              placeholder="—"
              onChange={(nextValue) => {
                onChange('waist', nextValue);
              }}
              className={styles.input}
            />
          </Col>

          <Col xs={12}>
            <Text className={styles.fieldLabel}>
              Обхват бёдер / см <span style={{ color: 'var(--primary)' }}>*</span>
            </Text>

            <InputNumber
              value={value.hips}
              controls={false}
              placeholder="—"
              onChange={(nextValue) => {
                onChange('hips', nextValue);
              }}
              className={styles.input}
            />
          </Col>
        </Row>
      </Card>
    </div>
  );
}

export default BodyParameters;
