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
    value: '5',
    label: 'образов за раз',
  },
  {
    value: '10',
    label: 'минут на подбор',
  },
  {
    value: 'WB',
    label: 'Wildberries',
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
    text: '5 готовых образов с вещами из Wildberries',
    icon: <ThunderboltOutlined />,
  },
  {
    number: '03',
    title: 'Купи в один клик',
    text: 'Все вещи с вашим размером и в рамках бюджета',
    icon: <ShoppingOutlined />,
  },
];

function LandingPage() {
  const navigate = useNavigate();

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

          <nav className={styles.nav} aria-label="Авторизация">
            <button
              type="button"
              className={styles.login}
              onClick={handleLogin}
            >
              Вход
            </button>

            <button
              type="button"
              className={styles.register}
              onClick={handleStart}
            >
              Регистрация
            </button>
          </nav>
        </div>
      </header>

      <main>
        <section className={styles.heroSection}>
          <div className={styles.hero}>
            <div className={styles.heroCopy}>
              <span className={styles.marketplace}>
                Wildberries
              </span>

              <h1 className={styles.heroTitle}>
                Подбери
                <br />
                5 образов
                <br />
                <span>за 10 минут</span>
              </h1>

              <p className={styles.description}>
                Вещи из Wildberries с гарантией бюджета и правильным размером.
              </p>

              <Button
                title="Начать подбор"
                onClick={handleStart}
                icon={<ClockCircleOutlined />}
                suffix={<ArrowRightOutlined />}
                className={styles.cta}
              />

              <div className={styles.stats}>
                {stats.map((stat) => (
                  <div className={styles.stat} key={stat.label}>
                    <strong>{stat.value}</strong>
                    <span>{stat.label}</span>
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
              Как работает
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
                      {step.title}
                    </div>

                    <div className={styles.stepText}>
                      {step.text}
                    </div>
                  </div>
                </article>
              ))}
            </div>

            <article className={styles.bottomCta}>
              <div className={styles.bottomCtaContent}>
                <span className={styles.bottomCtaLabel}>
                  Начни прямо сейчас
                </span>

                <h2>
                  Твой стиль — за 10
                  <br />
                  минут
                </h2>

                <button
                  type="button"
                  onClick={handleStart}
                >
                  <span>
                    Зарегистрироваться бесплатно
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
