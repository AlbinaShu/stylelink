import {
  ArrowRightOutlined,
  ClockCircleOutlined,
  ShoppingOutlined,
  StarFilled,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { ReactNode } from 'react';
import Brand from '../../shared/ui/Brand/Brand';
import Button from '../../shared/ui/Button/Button';
import styles from './LandingPage.module.css';

interface IStep {
  number: string;
  title: string;
  text: string;
  icon: ReactNode;
}

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
    text: '5 готовых образов с вещами из WB, Ozon и Lamoda',
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

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <Brand />

          <nav className={styles.nav}>
            <button type="button" onClick={() => navigate('/auth')}>
              Вход
            </button>
            <button
              type="button"
              className={styles.register}
              onClick={() => navigate('/auth?mode=register')}
            >
              Регистрация
            </button>
          </nav>
        </div>
      </header>

      <main className={styles.content}>
        <section className={styles.hero}>
          <h1>
            Подбери 5 образов
            <br />
            <span>за 10 минут</span>
          </h1>

          <p className={styles.description}>
            Вещи из ассортимента ваших любимых маркетплейсов — с гарантией
            <br className={styles.desktopBreak} />
            бюджета и правильным размером.
          </p>

          <div className={styles.marketplaces}>
            <span className={`${styles.marketplace} ${styles.wb}`}>
              Wildberries
            </span>
          </div>

          <Button
            title="Начать подбор"
            onClick={() => navigate('/auth')}
            icon={<ClockCircleOutlined />}
            suffix={<ArrowRightOutlined />}
            className={styles.cta}
          />
        </section>

        <section className={styles.howItWorks}>
          <div className={styles.sectionLabel}>КАК РАБОТАЕТ</div>

          <div className={styles.steps}>
            {steps.map((step) => (
              <article className={styles.stepCard} key={step.number}>
                <div className={styles.stepIcon}>{step.icon}</div>
                <div className={styles.stepCopy}>
                  <div className={styles.stepTitle}>
                    <span>{step.number}</span>
                    {step.title}
                  </div>
                  <div className={styles.stepText}>{step.text}</div>
                </div>
              </article>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

export default LandingPage;
