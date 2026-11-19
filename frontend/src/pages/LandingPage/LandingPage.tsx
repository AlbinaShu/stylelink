import {
  ArrowRightOutlined,
  ClockCircleOutlined,
  ShoppingOutlined,
  StarFilled,
  ThunderboltOutlined,
} from '@ant-design/icons';
import type { ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';

import Brand from '../../shared/ui/Brand/Brand';
import Button from '../../shared/ui/Button/Button';
import LanguageSwitcher from '../../shared/ui/LanguageSwitcher/LanguageSwitcher';
import { useLanguage } from '../../shared/i18n/LanguageContext';
import styles from './LandingPage.module.css';

interface IStep {
  number: string;
  title: string;
  text: string;
  icon: ReactNode;
}

interface IStat {
  value: string;
  label: string;
}

const stats: IStat[] = [
  {
    value: 'до 5',
    label: 'образов за раз',
  },
  {
    value: 'Яндекс Маркет',
    label: 'подбор вещей для образов',
  },
  {
    value: 'ML',
    label: 'анализ отзывов',
  },
];

const steps: IStep[] = [
  {
    number: '01',
    title: 'Заполни анкету',
    text: 'Повод, стиль, бюджет и параметры — 2 минуты',
    icon: <StarFilled />,
  },
  {
    number: '02',
    title: 'ИИ подберёт образы',
    text: 'До 5 образов с вещами из Яндекс Маркета',
    icon: <ThunderboltOutlined />,
  },
  {
    number: '03',
    title: 'Купи в один клик',
    text: 'Ссылки на товары и сигналы о посадке из отзывов',
    icon: <ShoppingOutlined />,
  },
];

function LandingPage() {
  const navigate = useNavigate();
  const { t } = useLanguage();

  const handleLogin = () => {
    navigate('/auth');
  };

  const handleStart = () => {
    navigate('/auth?mode=register');
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <Brand />

          <nav className={styles.nav} aria-label={t('Авторизация')}>
            <LanguageSwitcher />
            <button
              type="button"
              className={styles.login}
              onClick={handleLogin}
            >
              {t('Вход')}
            </button>

            <button
              type="button"
              className={styles.register}
              onClick={handleStart}
            >
              {t('Регистрация')}
            </button>
          </nav>
        </div>
      </header>

      <main>
        <section className={styles.heroSection}>
          <div className={styles.hero}>
            <div className={styles.heroCopy}>
              <span className={styles.marketplace}>
                {t('Яндекс Маркет')}
              </span>

              <h1 className={styles.heroTitle}>
                {t('Подбери')}
                <br />
                {t('образы')}
                <br />
                <span>{t('под свой запрос')}</span>
              </h1>

              <p className={styles.description}>
                {t('Вещи из Яндекс Маркета в рамках бюджета. Посадку оцениваем по отзывам.')}
              </p>

              <Button
                title={t('Начать подбор')}
                onClick={handleStart}
                icon={<ClockCircleOutlined />}
                suffix={<ArrowRightOutlined />}
                className={styles.cta}
              />

              <div className={styles.stats}>
                {stats.map((stat) => (
                  <div className={styles.stat} key={stat.label}>
                    <strong>{t(stat.value)}</strong>
                    <span>{t(stat.label)}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className={styles.heroVisual} aria-hidden="true">
              <img
                className={styles.heroImage}
                src="/images/hero-woman.webp"
                alt=""
              />

              <img
                className={styles.accentImageTop}
                src="/images/green-woman.webp"
                alt=""
              />

              <img
                className={styles.accentImageBottom}
                src="/images/yellow-woman.webp"
                alt=""
              />
            </div>
          </div>
        </section>

        <section className={styles.howItWorks}>
          <div className={styles.sectionInner}>
            <div className={styles.sectionLabel}>
              {t('Как работает')}
            </div>

            <div className={styles.steps}>
              {steps.map((step) => (
                <article
                  className={styles.stepCard}
                  key={step.number}
                >
                  <div className={styles.stepIcon}>
                    {step.icon}
                  </div>

                  <div className={styles.stepCopy}>
                    <div className={styles.stepTitle}>
                      {/* <span>{step.number}</span> */}
                      {t(step.title)}
                    </div>

                    <div className={styles.stepText}>
                      {t(step.text)}
                    </div>
                  </div>
                </article>
              ))}
            </div>

            <article className={styles.bottomCta}>
              <div className={styles.bottomCtaContent}>
                <span className={styles.bottomCtaLabel}>
                  {t('Начни прямо сейчас')}
                </span>

                <h2>
                  {t('Твой стиль — за 10')}
                  <br />
                  {t('минут')}
                </h2>

                <button
                  type="button"
                  onClick={handleStart}
                >
                  <span>
                    {t('Зарегистрироваться бесплатно')}
                  </span>

                  <ArrowRightOutlined />
                </button>
              </div>
            </article>
          </div>
        </section>
      </main>
    </div>
  );
}

export default LandingPage;
