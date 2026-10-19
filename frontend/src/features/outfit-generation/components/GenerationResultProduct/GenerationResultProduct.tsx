import {
  CheckCircleOutlined,
  ExportOutlined,
  InfoCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { Collapse, Image, Tag, Typography, message } from 'antd';
import type { MouseEvent, ReactNode } from 'react';
import { useState } from 'react';
import { sendBuyClick, sendSizeChanged, sendTooltipOpen } from '../../../experiment-events/api/experiment-events.api';
import { getSessionId } from '../../../../shared/utils/session';
import type { IOutfitItem } from '../../types';
import styles from './GenerationResultProduct.module.css';

const { Text } = Typography;

interface IGenerationResultProductProps {
  item: IOutfitItem;
  outfitId: string;
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

function getFitDescription(item: IOutfitItem): string {
  if (!item.fit) return '';

  const { fit_signal: fitSignal, confidence } = item.fit;
  const confidencePercent = confidence !== null ? Math.round(confidence * 100) : null;

  switch (fitSignal) {
    case 'runs_small':
      return confidencePercent !== null
        ? `${confidencePercent}% отзывов указывают на маломерность.`
        : 'По отзывам товар маломерит. Учитывайте это при выборе размера.';
    case 'true_to_size':
      return confidencePercent !== null
        ? `${confidencePercent}% отзывов подтверждают соответствие стандартной размерной сетке.`
        : 'По отзывам размер соответствует стандартной размерной сетке.';
    case 'runs_large':
      return confidencePercent !== null
        ? `${confidencePercent}% отзывов указывают на большемерность.`
        : 'По отзывам товар большемерит. Учитывайте это при выборе размера.';
    default:
      return 'Информация о посадке рассчитана на основе отзывов покупателей.';
  }
}

function getMarketplaceLabel(marketplace: string): string {
  switch (marketplace.toLowerCase()) {
    case 'yandex_market':
    case 'yandex market':
      return 'ЯМ';
    default:
      return marketplace;
  }
}

function GenerationResultProduct({ item, outfitId }: IGenerationResultProductProps) {
  const isAccessory = item.category === 'accessory';
  const showFit = item.fit != null;
  const showSizes = !isAccessory && Boolean(item.available_sizes?.length);
  const recommendedSize = !isAccessory ? item.recommended_size : null;
  const [selectedSize, setSelectedSize] = useState<string | null>(recommendedSize);

  const fitConfig = item.fit?.fit_signal != null ? FIT_CONFIG[item.fit.fit_signal] : undefined;
  const fitDescription = getFitDescription(item);

  const changeSize = (size: string) => {
    const previousSize = selectedSize;
    setSelectedSize(size);

    if (!previousSize || previousSize === size) return;

    void sendSizeChanged({
      session_id: getSessionId(),
      timestamp: new Date().toISOString(),
      item_id: item.id,
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
      timestamp: new Date().toISOString(),
    }).catch(() => undefined);
  };

  const handleBuy = async (event: MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();

    const sizeForEvent = isAccessory ? 'not_applicable' : selectedSize;

    if (!sizeForEvent) {
      void message.warning('Выберите размер перед переходом к покупке.');
      return;
    }

    try {
      await sendBuyClick({
        session_id: getSessionId(),
        timestamp: new Date().toISOString(),
        product_id: item.product_id,
        recommended_size: recommendedSize,
        price: item.price,
        outfit_id: outfitId,
        selected_size: sizeForEvent,
        match: recommendedSize !== null && sizeForEvent === recommendedSize,
      });
    } catch {}

    window.open(item.url, '_blank', 'noopener,noreferrer');
  };

  return (
    <article className={styles.card}>
      <div className={styles.layout}>
        <div className={styles.imageWrapper}>
          <Image src={item.image || undefined} alt={item.name} preview={false} className={styles.image} />
        </div>

        <div className={styles.content}>
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
                      isRecommended ? styles.recommendedSize : '',
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
                    <span>По отзывам: {fitConfig?.label ?? 'есть информация о посадке'}</span>
                  </span>
                ),
                children: <Text className={styles.fitDescription}>{fitDescription}</Text>,
              }]}
            />
          )}
        </div>
      </div>
    </article>
  );
}

export default GenerationResultProduct;
