import { GlobalOutlined } from '@ant-design/icons';
import { Dropdown } from 'antd';
import { useLanguage, type Language } from '../../i18n/LanguageContext';
import styles from './LanguageSwitcher.module.css';

export default function LanguageSwitcher() {
  const { language, setLanguage, t } = useLanguage();

  return (
    <Dropdown
      trigger={['click']}
      menu={{
        selectable: true,
        selectedKeys: [language],
        onClick: ({ key }) => setLanguage(key as Language),
        items: [
          { key: 'ru', label: 'Русский' },
          { key: 'en', label: 'English' },
        ],
      }}
    >
      <button className={styles.switcher} type="button" aria-label={t('Язык')} title={t('Язык')}>
        <GlobalOutlined />
      </button>
    </Dropdown>
  );
}
