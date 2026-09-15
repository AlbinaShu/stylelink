import { Card, Empty, Typography } from 'antd';
import { FileTextOutlined } from '@ant-design/icons';

import styles from './RequestHistory.module.css';

const { Text } = Typography;

function RequestHistory() {
  return (
    <Card
      bordered
      className={styles.card}
    >
      <div className={styles.header}>
        <FileTextOutlined className={styles.headerIcon} />

        <div className={styles.headerText}>
          <Text strong>
            История запросов
          </Text>

          <Text type="secondary">
            0 подборов
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
              Нет истории запросов
            </Text>

            <Text type="secondary">
              После первого подбора образов
              <br />
              здесь появятся ваши запросы
            </Text>
          </div>
        }
      />
    </Card>
  );
}

export default RequestHistory;