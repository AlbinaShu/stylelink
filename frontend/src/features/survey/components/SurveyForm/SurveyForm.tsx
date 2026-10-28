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
import { useEffect, useMemo, useState } from 'react';

import type {
  ISurveyAnswerItem,
  ISurveyItem,
  ISurveyProgress,
} from '../../types';
import { isSurveyAnswerValid } from '../../configurations/survey-validation';
import SurveyProduct from '../SurveyProduct/SurveyProduct';

import styles from './SurveyForm.module.css';
import { useVisibleOnce } from '../../../../shared/hooks/useVisibleOnce';
import type { ReactNode } from 'react';

function VisibleHeader({ productId, onVisible, children }: { productId: string; onVisible?: (id: string) => void; children: ReactNode }) {
  const ref = useVisibleOnce<HTMLDivElement>(productId, () => onVisible?.(productId));
  return <div ref={ref}>{children}</div>;
}

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

  onSkip?: (meta: ISurveyProgress) => Promise<void> | void;
  onProgress?: (meta: ISurveyProgress) => void;
  onItemVisible?: (productId: string) => void;
}

type DraftMap = Record<
  string,
  Partial<ISurveyAnswerItem>
>;

type LastQuestion = {
  productId: string;
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
  onItemVisible,
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
            !['product_id', 'fit_scope', 'tried_size'].includes(key) &&
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
    setSaved((current) => { const next = { ...current }; delete next[productId]; return next; });
    setDrafts((current) => {
      const previous =
        current[productId] ?? items.find((item) => item.product_id === productId)?.answer ?? {
          product_id: productId,
          fit_scope: 'recommended_only',
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
        (value === 'in_transit' || value === 'not_tried' || value === 'not_ordered')
      ) {
        delete next.tried_size;
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
        productId,
        key,
        value,
      };

      setLastQuestion(nextLastQuestion);


    }
  };

  useEffect(() => {
    if (!lastQuestion) return;
    onProgress?.({
      questionsAnswered,
      lastProductId: lastQuestion.productId,
      lastQuestionKey: lastQuestion.key,
      lastQuestionValue: lastQuestion.value,
    });
  }, [lastQuestion, questionsAnswered, onProgress]);

  const saveProduct = (productId: string) => {
    const answer = drafts[productId] ?? items.find((item) => item.product_id === productId)?.answer;

    const recommendedSize = items.find((item) => item.product_id === productId)?.recommended_size ?? null;
    if (!isSurveyAnswerValid(answer, recommendedSize)) {
      void message.warning(
        'Заполните обязательные вопросы по этому товару.',
      );

      return;
    }

    setSaved((current) => ({
      ...current,
      [productId]: { ...answer, fit_scope: 'recommended_only' },
    }));

    setActiveKey([]);
  };

  const collapseItems = items.map((item) => {
    const answer =
      drafts[item.product_id] ??
      saved[item.product_id] ?? item.answer ?? {
        product_id: item.product_id,
      };

    const isSaved =
      Boolean(saved[item.product_id]) ||
      item.status === 'answered';

    return {
      key: item.product_id,

      label: (
        <VisibleHeader productId={item.product_id} onVisible={onItemVisible}>
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
        </VisibleHeader>
      ),

      children: (
        <SurveyProduct
          answer={answer}
          recommendedSize={item.recommended_size}
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
                lastProductId: lastQuestion?.productId ?? null,
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