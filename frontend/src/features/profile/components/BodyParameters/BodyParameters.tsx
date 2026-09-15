import { useEffect, useState } from 'react';
import {
  Button,
  Col,
  Collapse,
  Form,
  InputNumber,
  Radio,
  Row,
  Space,
  Typography,
} from 'antd';

import { useProfile } from '../../hooks/useProfile';
import type {
  IProfile,
  IUpdateProfileRequest,
} from '../../types';

import styles from './BodyParameters.module.css';

const { Text } = Typography;

interface IBodyParametersProps {
  profile: IProfile;
}

function BodyParameters({
  profile,
}: IBodyParametersProps) {
  const [form] = Form.useForm<IUpdateProfileRequest>();

  const [isOpen, setIsOpen] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const { updateProfile } = useProfile();

  const setFormValues = () => {
    form.setFieldsValue({
      gender: profile?.gender ?? null,
      height: profile?.height ?? null,
      weight: profile?.weight ?? null,
      chest: profile?.chest ?? null,
      waist: profile?.waist ?? null,
      hips: profile?.hips ?? null,
    });
  };

  useEffect(() => {
    setFormValues();
  }, [profile, form]);

  const handleEdit = () => {
    setFormValues();
    setIsEditing(true);
    setIsOpen(true);
  };

  const handleCancel = () => {
    setFormValues();
    setIsEditing(false);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();

      setIsSaving(true);

      await updateProfile(values);

      setIsEditing(false);
    } finally {
      setIsSaving(false);
    }
  };

  const content = (
    <>
      <Form
        form={form}
        layout="vertical"
        disabled={!isEditing}
        className={styles.form}
      >
        <Form.Item
          label="Пол"
          name="gender"
          className={styles.genderField}
        >
          <Radio.Group
            optionType="button"
            buttonStyle="solid"
            className={styles.gender}
          >
            <Radio.Button value="female">
              Женский
            </Radio.Button>

            <Radio.Button value="male">
              Мужской
            </Radio.Button>
          </Radio.Group>
        </Form.Item>

        <Row gutter={[10, 0]}>
          <Col xs={12} span={12}>
            <Form.Item
              label="Рост / см"
              name="height"
            >
              <InputNumber
                min={0}
                max={300}
                controls={false}
                placeholder="—"
                className={styles.input}
              />
            </Form.Item>
          </Col>

          <Col xs={12} span={12}>
            <Form.Item
              label="Вес / кг"
              name="weight"
            >
              <InputNumber
                min={0}
                max={500}
                controls={false}
                placeholder="—"
                className={styles.input}
              />
            </Form.Item>
          </Col>

          <Col xs={12} span={12}>
            <Form.Item
              label="Обхват груди / см"
              name="chest"
            >
              <InputNumber
                min={0}
                max={300}
                controls={false}
                placeholder="—"
                className={styles.input}
              />
            </Form.Item>
          </Col>

          <Col xs={12} span={12}>
            <Form.Item
              label="Обхват талии / см"
              name="waist"
            >
              <InputNumber
                min={0}
                max={300}
                controls={false}
                placeholder="—"
                className={styles.input}
              />
            </Form.Item>
          </Col>

          <Col xs={12} span={12}>
            <Form.Item
              label="Обхват бёдер / см"
              name="hips"
            >
              <InputNumber
                min={0}
                max={300}
                controls={false}
                placeholder="—"
                className={styles.input}
              />
            </Form.Item>
          </Col>
        </Row>
      </Form>

      {!isEditing ? (
        <Button
          block
          onClick={handleEdit}
          className={styles.editButton}
        >
          Изменить
        </Button>
      ) : (
        <div className={styles.actions}>
          <Button
            type="primary"
            loading={isSaving}
            onClick={handleSave}
            className={styles.saveButton}
          >
            Сохранить
          </Button>

          <Button
            disabled={isSaving}
            onClick={handleCancel}
            className={styles.cancelButton}
          >
            Отмена
          </Button>
        </div>
      )}
    </>
  );

  return (
    <Collapse
      activeKey={isOpen ? ['body'] : []}
      onChange={(keys) => {
        setIsOpen(keys.includes('body'));
      }}
      className={styles.collapse}
      items={[
        {
          key: 'body',
          label: (
            <Space size={8}>
              <Text>Параметры тела</Text>

              <span className={styles.optional}>
                Необязательно
              </span>
            </Space>
          ),
          children: content,
        },
      ]}
    />
  );
}

export default BodyParameters;