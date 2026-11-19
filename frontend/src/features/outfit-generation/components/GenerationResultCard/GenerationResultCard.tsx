import { Tag, Typography } from 'antd';

import type { IOutfit } from '../../types';
import GenerationResultProduct from '../GenerationResultProduct/GenerationResultProduct';

import styles from './GenerationResultCard.module.css';
import { useLanguage, type Language } from '../../../../shared/i18n/LanguageContext';

const { Text } = Typography;

interface IGenerationResultCardProps {
    outfit: IOutfit;
    number: number;
    shoeSize: number | null;
}

const OCCASION_LABELS: Record<string, string> = {
    office: 'Офис',
    date: 'Свидание',
    walk: 'Прогулка',
    event: 'Мероприятие',
    travel: 'Путешествие',
};

const STYLE_LABELS: Record<string, string> = {
    business: 'Деловой',
    casual: 'Кэжуал',
    sport: 'Спортивный',
    romantic: 'Романтический',
};

function getItemsLabel(count: number, language: Language): string {
    if (language === 'en') return `${count} ${count === 1 ? 'item' : 'items'}`;
    const mod10 = count % 10;
    const mod100 = count % 100;

    if (mod10 === 1 && mod100 !== 11) {
        return `${count} вещь`;
    }

    if (
        mod10 >= 2 &&
        mod10 <= 4 &&
        (mod100 < 12 || mod100 > 14)
    ) {
        return `${count} вещи`;
    }

    return `${count} вещей`;
}

function GenerationResultCard({
    outfit,
    number,
    shoeSize,
}: IGenerationResultCardProps) {
    const { language, t } = useLanguage();
    const titleNumber = /^Образ (\d+)$/.exec(outfit.title)?.[1];
    const occasionLabel = outfit.occasion
        ? t(OCCASION_LABELS[outfit.occasion] ?? outfit.occasion)
        : null;

    const styleLabel = outfit.style
        ? t(STYLE_LABELS[outfit.style] ?? outfit.style)
        : null;

    return (
        <section className={styles.card}>
            <header className={styles.header}>
                <div className={styles.heading}>
                    <span className={styles.number}>
                        {String(number).padStart(
                            2,
                            '0',
                        )}
                    </span>

                    <div className={styles.titleBlock}>
                        <Text
                            strong
                            className={styles.title}
                        >
                            {titleNumber ? t('Образ {number}', { number: titleNumber }) : outfit.title}
                        </Text>

                        {(occasionLabel ||
                            styleLabel) && (
                                <div
                                    className={
                                        styles.meta
                                    }
                                >
                                    {occasionLabel && (
                                        <Text
                                            className={styles.occasion}
                                        >
                                            {occasionLabel}
                                        </Text>
                                    )}

                                    {occasionLabel &&
                                        styleLabel && (
                                            <span className={styles.separator}>
                                                ·
                                            </span>
                                        )}

                                    {styleLabel && (
                                        <Tag
                                            bordered={
                                                false
                                            }
                                            className={
                                                styles.styleTag
                                            }
                                        >
                                            {styleLabel}
                                        </Tag>
                                    )}
                                </div>
                            )}
                    </div>
                </div>

                <div className={styles.summary}>
                    <Text
                        strong
                        className={
                            styles.totalPrice
                        }
                    >
                        {Math.round(
                            outfit.total_price,
                        ).toLocaleString(
                            language === 'en' ? 'en-US' : 'ru-RU',
                        )}{' '}
                        ₽
                    </Text>

                    <Text
                        className={
                            styles.itemsCount
                        }
                    >
                        {getItemsLabel(
                            outfit.items.length,
                            language,
                        )}
                    </Text>
                </div>
            </header>

            <div className={styles.products}>
                {outfit.items.map((item) => (
                    <GenerationResultProduct
                        key={item.id}
                        item={item}
                        outfitId={outfit.id}
                        shoeSize={shoeSize}
                    />
                ))}
            </div>
        </section>
    );
}

export default GenerationResultCard;
