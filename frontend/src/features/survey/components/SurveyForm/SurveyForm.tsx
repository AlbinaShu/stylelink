import {
  Button,
  Collapse,
  Typography,
  message,
} from 'antd';
import {
  CheckCircleFilled,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import { useMemo, useState } from 'react';

import type {
  ISurveyAnswerItem,
  ISurveyItem,
} from '../../types';
import { isSurveyAnswerValid } from '../../configurations/survey-validation';
import SurveyProduct from '../SurveyProduct/SurveyProduct';

import styles from './SurveyForm.module.css';

const { Text, Title } = Typography;

interface ISurveyFormProps {
  items: ISurveyItem[];
  total: number;
  hasMore: boolean;
  loadingMore?: boolean;
  submitting?: boolean;

  onLoadMore: () => Promise<void> | void;

  onSubmit: (
    answers: ISurveyAnswerItem[],
  ) => Promise<void>;

  onSkip?: (meta: {
    questionsAnswered: number;
    lastQuestionKey: string | null;
    lastQuestionValue: string | null;
  }) => Promise<void> | void;

  onProgress?: (meta: {
    questionsAnswered: number;
    lastQuestionKey: string | null;
    lastQuestionValue: string | null;
  }) => void;
}

type DraftMap = Record<
  string,
  Partial<ISurveyAnswerItem>
>;

type LastQuestion = {
  key: string;
  value: string;
};

function SurveyForm({
  items,
  total,
  hasMore,
  loadingMore = false,
  submitting = false,
  onLoadMore,
  onSubmit,
  onSkip,
  onProgress,
}: ISurveyFormProps) {
  const [drafts, setDrafts] =
    useState<DraftMap>({});

  const [saved, setSaved] = useState<
    Record<string, ISurveyAnswerItem>
  >({});

  const [activeKey, setActiveKey] = useState<
    string | string[]
  >([]);

  const [lastQuestion, setLastQuestion] =
    useState<LastQuestion | null>(null);

  const answeredCount = Object.keys(saved).length;

  const questionsAnswered = useMemo(() => {
    return Object.values(drafts).reduce(
      (count, draft) => {
        const answeredFields = Object.entries(
          draft,
        ).filter(
          ([key, value]) =>
            key !== 'product_id' &&
            value !== null &&
            value !== undefined &&
            value !== '',
        );

        return count + answeredFields.length;
      },
      0,
    );
  }, [drafts]);

  const updateDraft = (
    productId: string,
    key: keyof ISurveyAnswerItem,
    value: string | null,
  ) => {
    setDrafts((current) => {
      const previous =
        current[productId] ?? {
          product_id: productId,
        };

      let next: Partial<ISurveyAnswerItem> = {
        ...previous,
        [key]: value,
      };

      if (key === 'order_placed') {
        next = {
          product_id: productId,
          order_placed:
            value as ISurveyAnswerItem['order_placed'],
        };
      }

      if (
        key === 'sizes_ordered' &&
        value !== '1'
      ) {
        delete next.purchased_size;
      }

      if (
        key === 'added_to_cart' &&
        value !== 'yes'
      ) {
        delete next.sizes_in_cart;
        delete next.cart_size;
      }

      if (
        key === 'sizes_in_cart' &&
        value !== '1'
      ) {
        delete next.cart_size;
      }

      if (
        key === 'fit_result' &&
        value === 'unknown'
      ) {
        delete next.action;
        delete next.return_reason;
        delete next.return_reason_text;
      }

      if (
        key === 'action' &&
        value !== 'returned'
      ) {
        delete next.return_reason;
        delete next.return_reason_text;
      }

      if (
        key === 'return_reason' &&
        value !== 'other'
      ) {
        delete next.return_reason_text;
      }

      return {
        ...current,
        [productId]: next,
      };
    });

    if (value !== null) {
      const nextLastQuestion = {
        key,
        value,
      };

      setLastQuestion(nextLastQuestion);

      onProgress?.({
        questionsAnswered:
          questionsAnswered + 1,
        lastQuestionKey:
          nextLastQuestion.key,
        lastQuestionValue:
          nextLastQuestion.value,
      });
    }
  };

  const saveProduct = (productId: string) => {
    const answer = drafts[productId];

    if (!isSurveyAnswerValid(answer)) {
      void message.warning(
        'Заполните обязательные вопросы по этому товару.',
      );

      return;
    }

    setSaved((current) => ({
      ...current,
      [productId]: answer,
    }));

    setActiveKey([]);
  };

  const collapseItems = items.map((item) => {
    const answer =
      drafts[item.product_id] ??
      saved[item.product_id] ?? {
        product_id: item.product_id,
      };

    const isSaved =
      Boolean(saved[item.product_id]) ||
      item.status === 'answered';

    return {
      key: item.product_id,

      label: (
        <div className={styles.itemHeader}>
          <span
            className={
              isSaved
                ? styles.statusDone
                : styles.statusPending
            }
          >
            {isSaved ? (
              <CheckCircleFilled />
            ) : (
              <QuestionCircleOutlined />
            )}
          </span>

          {item.image_url && (
            <img
              className={styles.thumb}
              src={item.image_url}
              alt={item.name || 'Товар'}
            />
          )}

          <div className={styles.itemText}>
            <Text
              strong
              className={styles.itemName}
            >
              {item.name || 'Товар'}
            </Text>

            {item.recommended_size && (
              <Text
                className={
                  styles.recommendedSize
                }
              >
                Рекомендованный размер:{' '}
                {item.recommended_size}
              </Text>
            )}
          </div>
        </div>
      ),

      children: (
        <SurveyProduct
          answer={answer}
          onChange={(key, value) =>
            updateDraft(
              item.product_id,
              key,
              value,
            )
          }
          onSave={() =>
            saveProduct(item.product_id)
          }
        />
      ),
    };
  });

  return (
    <div className={styles.form}>
      <div className={styles.heading}>
        <Title
          level={2}
          className={styles.title}
        >
          Помогите нам стать лучше
        </Title>

        <Text className={styles.subtitle}>
          Вы недавно переходили к покупке этих товаров.
          Расскажите, подошли ли размеры.
        </Text>
      </div>

      <Collapse
        accordion
        activeKey={activeKey}
        onChange={setActiveKey}
        items={collapseItems}
        expandIconPosition="end"
        className={styles.collapse}
      />

      {hasMore && (
        <Button
          type="text"
          block
          className={styles.loadMoreButton}
          loading={loadingMore}
          onClick={() => void onLoadMore()}
        >
          Показать ещё
        </Button>
      )}

      <div className={styles.footer}>
        <Text className={styles.counter}>
          Отвечено: {answeredCount} из {total}
        </Text>

        <Button
          type="primary"
          size="large"
          block
          disabled={answeredCount === 0}
          loading={submitting}
          className={styles.submitButton}
          onClick={() =>
            void onSubmit(
              Object.values(saved),
            )
          }
        >
          Отправить
        </Button>

        {onSkip && (
          <Button
            type="text"
            block
            className={styles.skipButton}
            onClick={() =>
              void onSkip({
                questionsAnswered,
                lastQuestionKey:
                  lastQuestion?.key ?? null,
                lastQuestionValue:
                  lastQuestion?.value ?? null,
              })
            }
          >
            Пропустить
          </Button>
        )}
      </div>
    </div>
  );
}

export default SurveyForm;