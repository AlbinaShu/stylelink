import { ExportOutlined } from '@ant-design/icons';
// STYLELINK_UNIVERSAL_SIZE_SELECTION_V1
/* STYLELINK_YANDEX_STRIP_V1 */
import http from '../../../../shared/api/http-client';
import {
  CheckCircleOutlined,
  InfoCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { Collapse, Image, Tag, Typography, message } from 'antd';
import type { MouseEvent, ReactNode } from 'react';
import { useEffect, useState } from 'react';
import type { CSSProperties } from 'react';
import { sendBuyClick, sendSizeChanged, sendTooltipOpen, sendRecommendationView, sendExplanationView } from '../../../experiment-events/api/experiment-events.api';
import { getDeviceType, getSessionId } from '../../../../shared/utils/session';
import type { IOutfitItem } from '../../types';
import styles from './GenerationResultProduct.module.css';
import { isHalfVisible, useVisibleOnce } from '../../../../shared/hooks/useVisibleOnce';
import { useLanguage } from '../../../../shared/i18n/LanguageContext';

const { Text } = Typography;

interface IGenerationResultProductProps {
  item: IOutfitItem;
  outfitId: string;
  shoeSize: number | null;
}



// STYLELINK_PRODUCT_CARD_CLEANUP_V2
const sortMarketplaceSizes = (sizes: string[]): string[] =>
  [...sizes].sort((a, b) =>
    a.localeCompare(b, 'ru', {
      numeric: true,
      sensitivity: 'base',
    }),
  );

interface MarketplaceOffer {
  marketplace: string;
  name: string;
  brand: string | null;
  price: number;
  currency: string;
  image: string | null;
  url: string;
  available_sizes: string[];
  match_type: 'similar' | 'exact';
  match_score: number;
  size_match_status?: 'match' | 'mismatch' | 'unknown';
  recommended_size?: string | null;
}

export interface AlternativesResponse {
  source_marketplace: string;
  offers: MarketplaceOffer[];
  marketplace_status: Record<string, string>;
}


// STYLELINK_UNIFIED_MARKETPLACES_V3

// STYLELINK_RESTORE_LOCAL_FETCH_V2
function MarketplaceAlternatives({
  item,
  onAvailabilityChange,
}: {
  item: IOutfitItem;
  onAvailabilityChange: (available: boolean) => void;
}) {
  const [data, setData] = useState<AlternativesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;

    setLoading(true);
    setError(false);

    // STYLELINK_YANDEX_REQUEST_DIAGNOSTICS_V1
    const requestStarted = performance.now();
    const requestNumber = 1;

    console.info('[StyleLink YM] START', {
      itemId: item.id,
      requestNumber,
      trigger: 'automatic',
    });

    // STYLELINK_YM_AUTO_RETRY_V3
    void (async () => {
      const maxAttempts = 3;
      let lastError: unknown = null;
      let receivedResponse = false;

      try {
        for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
          if (!active || controller.signal.aborted) return;

          const attemptStarted = performance.now();

          console.info('[StyleLink YM] ATTEMPT', {
            itemId: item.id,
            requestNumber,
            attempt,
            maxAttempts,
          });

          try {
            const response = await http.get<AlternativesResponse>(
              `/api/v1/marketplaces/outfit-items/${item.id}/alternatives`,
              {
                signal: controller.signal,
                timeout: 95000,
              },
            );

            if (!active || controller.signal.aborted) return;

            receivedResponse = true;
            lastError = null;

            const next = response.data?.offers?.find(
              offer => offer.marketplace === 'yandex_market'
            );

            console.info('[StyleLink YM] SUCCESS', {
              itemId: item.id,
              requestNumber,
              attempt,
              httpStatus: response.status,
              attemptDurationMs: Math.round(
                performance.now() - attemptStarted
              ),
              durationMs: Math.round(
                performance.now() - requestStarted
              ),
              yandexStatus:
                response.data?.marketplace_status?.yandex_market,
              offersCount: response.data?.offers?.length ?? 0,
              yandexOffers: (response.data?.offers ?? [])
                .filter(offer => offer.marketplace === 'yandex_market')
                .map(offer => ({
                  name: offer.name,
                  url: offer.url,
                  price: offer.price,
                  score: offer.match_score,
                  matchType: offer.match_type,
                })),
            });

            setData(previous => {
              const old = previous?.offers?.find(
                offer => offer.marketplace === 'yandex_market'
              );

              if (!next && old) return previous;

              if (
                old &&
                next &&
                old.url !== next.url &&
                next.match_type !== 'exact'
              ) {
                return previous;
              }

              return response.data;
            });

            if (next) {
              onAvailabilityChange(true);
              console.info('[StyleLink YM] FOUND', {
                itemId: item.id,
                attempt,
              });
              return;
            }

            if (
              response.data?.marketplace_status?.yandex_market
                === 'not_configured'
            ) {
              return;
            }
          } catch (error: unknown) {
            if (!active || controller.signal.aborted) return;

            lastError = error;

            const failure = error as {
              message?: string;
              code?: string;
              response?: { status?: number };
            };

            console.warn('[StyleLink YM] ATTEMPT_ERROR', {
              itemId: item.id,
              requestNumber,
              attempt,
              httpStatus: failure?.response?.status ?? null,
              code: failure?.code ?? null,
              message: failure?.message ?? String(error),
            });
          }

          if (attempt < maxAttempts) {
            await new Promise<void>(resolve => {
              if (controller.signal.aborted) {
                resolve();
                return;
              }

              const onAbort = () => {
                clearTimeout(timer);
                resolve();
              };

              const timer = setTimeout(() => {
                controller.signal.removeEventListener(
                  'abort',
                  onAbort,
                );
                resolve();
              }, 1200);

              controller.signal.addEventListener(
                'abort',
                onAbort,
                { once: true },
              );
            });
          }
        }

        if (!active || controller.signal.aborted) return;

        if (!receivedResponse && lastError !== null) {
          console.error('[StyleLink YM] ERROR', {
            itemId: item.id,
            requestNumber,
            durationMs: Math.round(
              performance.now() - requestStarted
            ),
            message: 'All attempts failed',
          });
          setError(true);
        } else {
          console.info('[StyleLink YM] FINISHED_WITHOUT_MATCH', {
            itemId: item.id,
            requestNumber,
            attempts: maxAttempts,
          });
        }
      } finally {
        if (active) setLoading(false);
      }
    })();

    return () => {
      active = false;
      controller.abort();
    };
  }, [item.id, onAvailabilityChange]);


  const offers = (data?.offers ?? []).filter(
    offer => offer.marketplace === 'yandex_market'
  );

  const status = data?.marketplace_status?.yandex_market;

  const statusText = error
    ? 'Не удалось получить предложения'
    : status === 'not_configured'
      ? 'Источник не настроен'
      : status === 'unavailable'
        ? 'Источник временно недоступен'
        : 'Подходящий товар не найден';

  const stripStyle: CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: 12,
    padding: 14,
    border: '1px solid #e5e7eb',
    borderRadius: 12,
  };


  if (!offers.length) {
    return (
      <div style={stripStyle}>
        <div style={{ flex: '1 1 220px' }}>
          <div style={{ fontWeight: 600 }}>
            Яндекс Маркет
          </div>
          <div style={{ marginTop: 8, opacity: 0.7 }}>
            {loading ? 'Обновляем предложение...' : statusText}
          </div>
        </div>

      </div>
    );
  }

  return (
    <>
      {offers.map(offer => (
        <YandexMarketplaceStrip
          key={`${item.id}:${offer.url}`}
          offer={offer}
          recommendedSize={offer.recommended_size ?? null}
        />
      ))}
    </>
  );
}

function YandexMarketplaceStrip({
  offer,
  recommendedSize,
}: {
  offer: MarketplaceOffer;
  recommendedSize: string | null;
}) {
  const sizes = sortMarketplaceSizes(offer.available_sizes ?? []);

  const initialSize = recommendedSize
    ? sizes.find(size => size === recommendedSize) ?? null
    : null;

  const [selection, setSelection] = useState<{
    url: string;
    initialSize: string | null;
    size: string | null;
  }>({
    url: offer.url,
    initialSize,
    size: initialSize,
  });

  const resetSelection =
    selection.url !== offer.url ||
    selection.initialSize !== initialSize;

  const selectedSize = resetSelection
    ? initialSize
    : selection.size;

  if (resetSelection) {
    setSelection({
      url: offer.url,
      initialSize,
      size: initialSize,
    });
  }

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 12,
        padding: 14,
        border: '1px solid #e5e7eb',
        borderRadius: 12,
      }}
    >
      <div style={{ flex: '1 1 220px', minWidth: 0 }}>
        <div style={{ fontWeight: 600 }}>
          Яндекс Маркет
        </div>

        <div
          style={{
            fontSize: 18,
            fontWeight: 700,
            marginTop: 4,
          }}
        >
          {Math.round(offer.price).toLocaleString('ru-RU')} ₽
        </div>

        <div
          style={{
            marginTop: 8,
            fontSize: 12,
            opacity: 0.7,
          }}
        >
          Доступные размеры
        </div>

        {sizes.length ? (
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: 6,
              marginTop: 6,
            }}
          >
            {sizes.map(size => {
              const chosen = selectedSize === size;
              const recommended =
                recommendedSize !== null &&
                sizeEquivalent(size, recommendedSize);

              return (
                <button
                  key={size}
                  type="button"
                  aria-pressed={chosen}
                  onClick={() => setSelection({
                    url: offer.url,
                    initialSize,
                    size,
                  })}
                  style={{
                    padding: '5px 10px',
                    borderRadius: 8,
                    border: chosen
                      ? '2px solid #7c3aed'
                      : '1px solid #d1d5db',
                    background: chosen
                      ? '#f3e8ff'
                      : 'transparent',
                    color: 'inherit',
                    cursor: 'pointer',
                    fontWeight: chosen ? 700 : 400,
                  }}
                >
                  {size}{recommended ? ' ✓' : ''}
                </button>
              );
            })}
          </div>
        ) : (
          <div style={{ marginTop: 6, fontSize: 12 }}>
            Размеры не указаны — совпадение не подтверждено
          </div>
        )}

        {recommendedSize && sizes.length > 0 && !initialSize && (
          <div style={{ marginTop: 6, fontSize: 12 }}>
            Рекомендованный размер {recommendedSize} недоступен
          </div>
        )}

        {selectedSize && (
          <div style={{ marginTop: 6, fontSize: 12 }}>
            Выбран размер: {selectedSize}
          </div>
        )}

        <div
          style={{
            marginTop: 8,
            fontSize: 12,
            opacity: 0.7,
          }}
        >
          Сходство: {Math.round(offer.match_score * 100)}%
        </div>
      </div>

      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          gap: 8,
        }}
      >

        <a
          href={offer.url}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '9px 14px',
            border: '1px solid #d1d5db',
            borderRadius: 9,
            color: 'inherit',
            textDecoration: 'none',
            fontWeight: 600,
          }}
        >
          Открыть ЯМ ↗
        </a>
      </div>
    </div>
  );
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


// STYLELINK_ALTERNATIVE_SIZE_V1
function alternativeSizeNumbers(value: string): number[] | null {
  const s = value.trim().toUpperCase().replace(/^RU\s*/, '');

  const shoe = s.match(/^(\d{2})\s*[-–—]\s*\d+[.,]\d+\s*СМ$/);
  if (shoe) return [Number(shoe[1])];

  const height = s.match(
    /^(\d{2})\s*[-–—/]\s*(1\d{2}|2\d{2})$/
  );
  if (height) return [Number(height[1])];

  const one = s.match(/^(\d{2})$/);
  if (one) {
    const n = Number(one[1]);
    return n >= 30 && n <= 70 ? [n] : null;
  }

  const range = s.match(/^(\d{2})\s*[-–—]\s*(\d{2})$/);
  if (range) {
    const low = Number(range[1]);
    const high = Number(range[2]);
    if (low >= 30 && high <= 70 && high >= low && high - low <= 8) {
      return Array.from(
        { length: Math.floor((high - low) / 2) + 1 },
        (_, i) => low + i * 2
      );
    }
  }

  return null;
}

function sizeEquivalent(
  a: string,
  b: string
): boolean {
  const left = alternativeSizeNumbers(a);
  const right = alternativeSizeNumbers(b);

  if (left && right) {
    return left.some(n => right.includes(n));
  }

  return a.trim().toUpperCase() === b.trim().toUpperCase();
}

function GenerationResultProduct({
  item,
  outfitId,
  shoeSize,
}: IGenerationResultProductProps) {
  const { language, t } = useLanguage();
  // STYLELINK_MARKETPLACE_BADGES_V1
  const [hasYandexOffer, setHasYandexOffer] = useState(false);

  useEffect(() => {
    setHasYandexOffer(false);
  }, [item.id]);

  const isAccessory = item.category === 'accessory';

  // Категории обуви, которые могут прийти с backend/marketplace.
  const normalizedCategory = item.category?.trim().toLowerCase() ?? '';
  const isShoe = [
    'shoes',
    'shoe',
    'footwear',
    'обувь',
  ].includes(normalizedCategory);

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
  const initialSize = recommendedSize
    ? item.available_sizes?.find(size => sizeEquivalent(size, recommendedSize)) ?? null
    : null;
  const showFit = item.fit != null || recommendedSize != null;
  const fitConfig = item.fit?.fit_signal != null ? FIT_CONFIG[item.fit.fit_signal] : undefined;
  const isInsufficientFit = item.fit == null || item.fit.status === 'insufficient_evidence';
  const fitSummaryRu = isInsufficientFit
    ? recommendedSize
      ? shoeSizeFromAvailable
        ? 'По отзывам нет надежной оценки посадки. Размер выбран по вашему размеру обуви.'
        : 'По отзывам нет надежной оценки посадки. Размер подобран по размерной таблице.'
      : 'Недостаточно данных для подбора размера'
    : `По отзывам: ${fitConfig?.label ?? 'Есть информация о посадке'}`;
  const fitSummary = isInsufficientFit
    ? t(fitSummaryRu)
    : t('По отзывам: {fit}', { fit: t(fitConfig?.label ?? 'Есть информация о посадке') });
  const confidenceLabelRu = getConfidenceLabel(item.fit?.confidence);
  const confidenceLabel = item.fit?.confidence != null && confidenceLabelRu
    ? t('Уверенность: {percent}%', { percent: Math.round(item.fit.confidence * 100) })
    : null;
  const reviewsLabelRu = item.fit ? `Проанализировано: ${getReviewsLabel(item.fit.num_reviews)}` : null;
  const reviewsLabel = item.fit
    ? language === 'en'
      ? t('Проанализировано: {count} {word}', {
          count: item.fit.num_reviews,
          word: item.fit.num_reviews === 1 ? 'review' : 'reviews',
        })
      : reviewsLabelRu
    : null;


  const fitViewRef = useVisibleOnce<HTMLDivElement>(item.id + ':fit', () => {
    if (!showFit || !item.product_id) return;
    void sendExplanationView({
      session_id: getSessionId(), timestamp: new Date().toISOString(), device_type: getDeviceType(),
      outfitItems: [{ product_id: item.product_id, outfit_id: outfitId, outfit_item_id: item.id,
        initial_selected_size: initialSize, explanation_visible: true, explanation_summary: fitSummaryRu }],
    }).catch(() => undefined);
  });
  const viewRef = useVisibleOnce<HTMLDivElement>(item.id, () => {
    if (!item.product_id) return;
    void sendRecommendationView({
      session_id: getSessionId(), timestamp: new Date().toISOString(), device_type: getDeviceType(),
      outfitItems: [{ product_id: item.product_id, outfit_id: outfitId, outfit_item_id: item.id,
        initial_selected_size: initialSize, explanation_visible: showFit && isHalfVisible(fitViewRef.current),
        explanation_summary: showFit && isHalfVisible(fitViewRef.current) ? fitSummaryRu : null }],
    }).catch(() => undefined);
  });

  const [selection, setSelection] = useState({
    itemId: item.id,
    initialSize,
    size: initialSize,
  });
  const shouldResetSelection = selection.itemId !== item.id || selection.initialSize !== initialSize;
  const selectedSize = shouldResetSelection ? initialSize : selection.size;

  if (shouldResetSelection) {
    setSelection({ itemId: item.id, initialSize, size: initialSize });
  }


  const changeSize = (size: string) => {
    const previousSize = selectedSize;
    setSelection({ itemId: item.id, initialSize, size });

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
      explanation_summary: fitSummaryRu,
      explanation_text: item.fit?.explanation ?? null,
      explanation_meta: confidenceLabelRu ? `${confidenceLabelRu} · ${reviewsLabelRu}` : reviewsLabelRu,
      outfit_id: outfitId,
      outfit_item_id: item.id,
      timestamp: new Date().toISOString(),
    }).catch(() => undefined);
  };

  const handleBuy = (event: MouseEvent<HTMLAnchorElement>) => {
    const sizeForEvent = isAccessory ? 'not_applicable' : selectedSize;

    if (!sizeForEvent) {
      event.preventDefault();
      void message.warning(t('Выберите размер перед переходом к покупке.'));
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
      match: recommendedSize !== null && sizeEquivalent(sizeForEvent, recommendedSize),
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
                <Tag
                  className={styles.marketplace}
                  style={{
                    background: '#8A32E6',
                    color: '#FFFFFF',
                  }}
                >
                  {t(getMarketplaceLabel(item.marketplace))}
                </Tag>
                {hasYandexOffer && (
                  <Tag
                    className={styles.marketplace}
                    style={{
                      background: '#FFCC00',
                      color: '#211800',
                    }}
                  >
                    {t('Яндекс Маркет')}
                  </Tag>
                )}
                {item.brand?.trim() &&
                  !['unknown', 'не определён', 'не определен',
                    'не указан', 'без бренда'].includes(
                      item.brand.trim().toLowerCase()
                    ) && (
                    <Text className={styles.brand} ellipsis>
                      {item.brand.trim()}
                    </Text>
                  )}
              </div>
              <Text strong className={styles.name} title={item.name}>{item.name}</Text>
              <Text strong className={styles.price}>{Math.round(item.price).toLocaleString(language === 'en' ? 'en-US' : 'ru-RU')} ₽</Text>
            </div>

            <a
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.external}
              aria-label={t('Открыть {name}', { name: item.name })}
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

          {recommendedSize !== null && !item.available_sizes?.some(size => sizeEquivalent(size, recommendedSize)) && (
            <div className={styles.recommendation}>{t('Рекомендуемый размер:')} <strong>{recommendedSize}</strong></div>
          )}

          {showFit && (
            <div ref={fitViewRef}>
            {isInsufficientFit ? (
              <div className={styles.fitUnavailable}>
                <span className={[styles.fitLabel, styles.fitInfo].join(' ')}>
                  <InfoCircleOutlined />
                  <span>{fitSummary}</span>
                </span>
              </div>
            ) : (
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
                    <span>{fitSummary}</span>
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

                  </div>
                ),
              }]}
              />
            )}
            </div>
          )}
        </div>
      </div>
      {/* STYLELINK_MARKETPLACE_STRIPS_V1 */}
      <section
        aria-label="Где купить"
        style={{
          marginTop: 16,
          display: 'flex',
          flexDirection: 'column',
          gap: 10,
        }}
      >
        <strong style={{ fontSize: 16 }}>Где купить</strong>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 12,
            padding: 14,
            border: '1px solid #e5e7eb',
            borderRadius: 12,
          }}
        >
          <div style={{ flex: '1 1 220px', minWidth: 0 }}>
            <div style={{ fontWeight: 600 }}>Wildberries</div>

            <div style={{ fontSize: 18, fontWeight: 700, marginTop: 4 }}>
              {Math.round(item.price).toLocaleString('ru-RU')} ₽
            </div>

            {!isAccessory && (
              <>
                <div style={{ marginTop: 8, fontSize: 12, opacity: 0.7 }}>
                  Доступные размеры
                </div>

                <div style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: 6,
                  marginTop: 6,
                }}>
                  {sortMarketplaceSizes(item.available_sizes ?? []).map(size => {
                    const chosen = selectedSize === size;
                    const recommended = recommendedSize !== null
                      && sizeEquivalent(size, recommendedSize);

                    return (
                      <button
                        key={size}
                        type="button"
                        aria-pressed={chosen}
                        onClick={() => changeSize(size)}
                        style={{
                          padding: '5px 10px',
                          borderRadius: 8,
                          border: chosen
                            ? '2px solid #7c3aed'
                            : '1px solid #d1d5db',
                          background: chosen ? '#f3e8ff' : 'transparent',
                          color: 'inherit',
                          cursor: 'pointer',
                          fontWeight: chosen ? 700 : 400,
                        }}
                      >
                        {size}{recommended ? ' ✓' : ''}
                      </button>
                    );
                  })}
                </div>

                {recommendedSize !== null && !initialSize && (
                  <div style={{ marginTop: 6, fontSize: 12 }}>
                    Рекомендованный размер {recommendedSize} недоступен
                  </div>
                )}

                {selectedSize && (
                  <div style={{ marginTop: 6, fontSize: 12 }}>
                    Выбран размер: {selectedSize}
                  </div>
                )}
              </>
            )}
          </div>

          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={handleBuy}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '9px 14px',
              border: '1px solid #d1d5db',
              borderRadius: 9,
              color: 'inherit',
              textDecoration: 'none',
              fontWeight: 600,
            }}
          >
            Открыть WB ↗
          </a>
        </div>

        <MarketplaceAlternatives
          item={item}
          onAvailabilityChange={setHasYandexOffer}
        />
      </section>
    </article>
  );
}

export default GenerationResultProduct;
