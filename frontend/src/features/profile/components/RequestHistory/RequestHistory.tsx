import { Card, Empty, Typography } from 'antd';
import { FileTextOutlined } from '@ant-design/icons';

import styles from './RequestHistory.module.css';
import { useLanguage } from '../../../../shared/i18n/LanguageContext';

const { Text } = Typography;

function RequestHistory() {
  const { t } = useLanguage();
  return (
    <Card
      bordered
      className={styles.card}
    >
      <div className={styles.header}>
        <FileTextOutlined className={styles.headerIcon} />

        <div className={styles.headerText}>
          <Text strong>
            {t('История запросов')}
          </Text>

          <Text type="secondary">
            {t('0 подборов')}
          </Text>
        </div>
      </div>

      <Empty
        image={<FileTextOutlined className={styles.emptyIcon} />}
        imageStyle={{
          height: 'auto',
        }}
        description={
          <div className={styles.emptyDescription}>
            <Text className={styles.emptyTitle}>
              {t('Нет истории запросов')}
            </Text>

            <Text type="secondary">
              {t('После первого подбора образов')}
              <br />
              {t('здесь появятся ваши запросы')}
            </Text>
          </div>
        }
      />
    </Card>
  );
}

export default RequestHistory;
