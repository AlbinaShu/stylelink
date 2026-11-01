import {
  CheckCircleOutlined,
  ExportOutlined,
  InfoCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { Collapse, Image, Tag, Typography, message } from 'antd';
import type { MouseEvent, ReactNode } from 'react';
import { useState } from 'react';
import { sendBuyClick, sendSizeChanged, sendTooltipOpen, sendRecommendationView, sendExplanationView } from '../../../experiment-events/api/experiment-events.api';
import { getDeviceType, getSessionId } from '../../../../shared/utils/session';
import type { IOutfitItem } from '../../types';
import styles from './GenerationResultProduct.module.css';
import { isHalfVisible, useVisibleOnce } from '../../../../shared/hooks/useVisibleOnce';

const { Text } = Typography;

interface IGenerationResultProductProps {
  item: IOutfitItem;
  outfitId: string;
  shoeSize: number | null;
}

interface IFitConfig { label: string; icon: ReactNode; className: string; }

const FIT_CONFIG: Record<string, IFitConfig> = {
  runs_small: {
    label: 'Маломерит',
    icon: <WarningOutlined />,
    className: styles.fitWarning
  },
  true_to_size: {
    label: 'Соответствует размеру',
    icon: <CheckCircleOutlined />,
    className: styles.fitSuccess
  },
  runs_large: {
    label: 'Большемерит',
    icon: <InfoCircleOutlined />,
    className: styles.fitInfo
  },
};

function getConfidenceLabel(confidence: number | null | undefined): string | null {
  if (confidence == null || !Number.isFinite(confidence) || confidence < 0 || confidence > 1) {
    return null;
  }

  return `Уверенность: ${Math.round(confidence * 100)}%`;
}

function getReviewsLabel(count: number): string {
  const mod10 = count % 10;
  const mod100 = count % 100;

  if (mod10 === 1 && mod100 !== 11) {
    return `${count} отзыв`;
  }

  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
    return `${count} отзыва`;
  }

  return `${count} отзывов`;
}

function getMarketplaceLabel(marketplace: string): string {
  switch (marketplace.toLowerCase()) {
    case 'yandex_market':
    case 'yandex market':
      return 'Яндекс Маркет';
    default:
      return marketplace;
  }
}

function GenerationResultProduct({
  item,
  outfitId,
  shoeSize,
}: IGenerationResultProductProps) {
  const isAccessory = item.category === 'accessory';

  // Категории обуви, которые могут прийти с backend/marketplace.
  const normalizedCategory = item.category?.trim().toLowerCase() ?? '';
  const isShoe = [
    'shoes',
    'shoe',
    'footwear',
    'обувь',
  ].includes(normalizedCategory);

  const showFit = item.fit != null;
  const showSizes = !isAccessory && Boolean(item.available_sizes?.length);

  // Нормализация нужна, чтобы 39.0 совпадал с "39",
  // а 38.5 продолжал совпадать с "38.5".
  const normalizedShoeSize =
    shoeSize == null ? null : String(Number(shoeSize));

  const shoeSizeFromAvailable =
    isShoe && normalizedShoeSize !== null
      ? item.available_sizes?.find(
          (size) => String(Number(size)) === normalizedShoeSize,
        ) ?? null
      : null;

  const recommendedSize = isAccessory ? null : (item.recommended_size ?? shoeSizeFromAvailable);
  const initialSize = recommendedSize && item.available_sizes?.includes(recommendedSize) ? recommendedSize : null;
  const fitConfig = item.fit?.fit_signal != null ? FIT_CONFIG[item.fit.fit_signal] : undefined;
  const isInsufficientFit = item.fit?.status === 'insufficient_evidence';
  const fitTitle = isInsufficientFit
    ? 'Недостаточно данных о посадке'
    : (fitConfig?.label ?? 'Есть информация о посадке');
  const fitExplanation = isInsufficientFit
    ? `${item.fit?.explanation ?? ''} Размер подобран по размерной таблице.`.trim()
    : item.fit?.explanation;
  const confidenceLabel = getConfidenceLabel(item.fit?.confidence);
  const reviewsLabel = item.fit ? getReviewsLabel(item.fit.num_reviews) : null;


  const fitViewRef = useVisibleOnce<HTMLDivElement>(item.id + ':fit', () => {
    if (!showFit || !item.product_id) return;
    void sendExplanationView({
      session_id: getSessionId(), timestamp: new Date().toISOString(), device_type: getDeviceType(),
      outfitItems: [{ product_id: item.product_id, outfit_id: outfitId, outfit_item_id: item.id,
        initial_selected_size: initialSize, explanation_visible: true, explanation_summary: 'По отзывам: ' + fitTitle }],
    }).catch(() => undefined);
  });
  const viewRef = useVisibleOnce<HTMLDivElement>(item.id, () => {
    if (!item.product_id) return;
    void sendRecommendationView({
      session_id: getSessionId(), timestamp: new Date().toISOString(), device_type: getDeviceType(),
      outfitItems: [{ product_id: item.product_id, outfit_id: outfitId, outfit_item_id: item.id,
        initial_selected_size: initialSize, explanation_visible: showFit && isHalfVisible(fitViewRef.current),
        explanation_summary: showFit && isHalfVisible(fitViewRef.current) ? 'По отзывам: ' + fitTitle : null }],
    }).catch(() => undefined);
  });

  const selectionKey = item.id + ':' + initialSize;
  const [selection, setSelection] = useState({ key: selectionKey, value: initialSize });
  const selectedSize = selection.key === selectionKey ? selection.value : initialSize;


  const changeSize = (size: string) => {
    const previousSize = selectedSize;
    setSelection({ key: selectionKey, value: size });

    if (!previousSize || previousSize === size) return;

    void sendSizeChanged({
      session_id: getSessionId(),
      timestamp: new Date().toISOString(),
      product_id: item.product_id,
      outfit_id: outfitId,
      outfit_item_id: item.id,
      recommended_size: recommendedSize,
      previous_size: previousSize,
      selected_size: size,
    }).catch(() => undefined);
  };

  const openFit = (keys: string | string[]) => {
    const isOpen = Array.isArray(keys) ? keys.includes('fit') : keys === 'fit';

    if (!isOpen) return;

    void sendTooltipOpen({
      session_id: getSessionId(),
      product_id: item.product_id,
      tooltip_type: 'fit',
      explanation_summary: 'По отзывам: ' + fitTitle,
      explanation_text: item.fit?.explanation ?? null,
      explanation_meta: confidenceLabel ? `${confidenceLabel} · ${reviewsLabel}` : reviewsLabel,
      outfit_id: outfitId,
      outfit_item_id: item.id,
      timestamp: new Date().toISOString(),
    }).catch(() => undefined);
  };

  const handleBuy = (event: MouseEvent<HTMLAnchorElement>) => {
    const sizeForEvent = isAccessory ? 'not_applicable' : selectedSize;

    if (!sizeForEvent) {
      event.preventDefault();
      void message.warning('Выберите размер перед переходом к покупке.');
      return;
    }

    void sendBuyClick({
      session_id: getSessionId(),
      timestamp: new Date().toISOString(),
      product_id: item.product_id,
      recommended_size: recommendedSize,
      price: item.price,
      outfit_id: outfitId,
      selected_size: sizeForEvent,
      match: recommendedSize !== null && sizeForEvent === recommendedSize,
    }).catch(() => undefined);
  };

  return (
    <article className={styles.card}>
      <div className={styles.layout}>
        <div className={styles.imageWrapper}>
          <Image src={item.image || undefined} alt={item.name} preview={false} className={styles.image} />
        </div>

        <div ref={viewRef} className={styles.content}>
          <div className={styles.productHeader}>
            <div className={styles.productInfo}>
              <div className={styles.meta}>
                <Tag className={styles.marketplace}>{getMarketplaceLabel(item.marketplace)}</Tag>
                {item.brand && <Text className={styles.brand} ellipsis>{item.brand}</Text>}
              </div>
              <Text strong className={styles.name}>{item.name}</Text>
              <Text strong className={styles.price}>{Math.round(item.price).toLocaleString('ru-RU')} ₽</Text>
            </div>

            <a
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.external}
              aria-label={`Открыть ${item.name}`}
              onClick={handleBuy}
            >
              <ExportOutlined />
            </a>
          </div>

          {showSizes && (
            <div className={styles.sizes}>
              {item.available_sizes!.map((size) => {
                const isRecommended = recommendedSize !== null && size === recommendedSize;
                const isSelected = selectedSize === size;
                return (
                  <Tag
                    key={size}
                    role="button"
                    tabIndex={0}
                    onClick={() => changeSize(size)}
                    onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') changeSize(size); }}
                    className={[
                      styles.size,
                      isRecommended
                        ? styles.recommendedSize
                        : '',
                      isSelected ? styles.selectedSize : '',
                    ].filter(Boolean).join(' ')}
                  >
                    {size}
                  </Tag>
                );
              })}
            </div>
          )}

          {recommendedSize !== null && !item.available_sizes?.includes(recommendedSize) && (
            <div className={styles.recommendation}>Рекомендуемый размер: <strong>{recommendedSize}</strong></div>
          )}

          {showFit && (
            <div ref={fitViewRef}>
            <Collapse
              ghost
              expandIconPosition="end"
              className={styles.fitCollapse}
              onChange={openFit}
              items={[{
                key: 'fit',
                label: (
                  <span className={[styles.fitLabel, fitConfig?.className ?? styles.fitInfo].filter(Boolean).join(' ')}>
                    {fitConfig?.icon ?? <InfoCircleOutlined />}
                    <span>По отзывам: {fitTitle}</span>
                  </span>
                ),
                children: (
                  <div className={styles.fitDetails}>
                    {reviewsLabel && (
                      <Text className={styles.fitMeta}>
                        {confidenceLabel
                          ? `${confidenceLabel} · ${reviewsLabel}`
                          : reviewsLabel}
                      </Text>
                    )}

                    {fitExplanation && (
                      <Text className={styles.fitDescription}>
                        {fitExplanation}
                      </Text>
                    )}
                  </div>
                ),
              }]}
            />
            </div>
          )}
        </div>
      </div>
    </article>
  );
}

export default GenerationResultProduct;
