import { Card, Flex, Progress, Typography } from 'antd';

import styles from './UsageLimit.module.css';

const { Text } = Typography;

interface IUsage {
    used: number;
    limit: number;
    resetDate: string;
}

const usage: IUsage = {
    used: 5,
    limit: 5,
    resetDate: '1 октября',
};

function UsageLimit() {
    const percent = (usage.used / usage.limit) * 100;

    return (
        <Card className={styles.card}>
            <Flex
                vertical
                gap={8}
            >
                <Flex
                    justify="space-between"
                    align="center"
                >
                    <Text className={styles.label}>
                        Использовано подборов
                    </Text>

                    <Text className={styles.value}>
                        {usage.used} / {usage.limit}
                    </Text>
                </Flex>

                <Progress
                    percent={percent}
                    showInfo={false}
                    strokeColor="var(--primary)"
                    trailColor="var(--surface-muted)"
                    className={styles.progress}
                />

                <Text className={styles.description}>
                    Лимит исчерпан. Обновится {usage.resetDate}
                    {' '}
                    или перейдите на Pro.
                </Text>
            </Flex>
        </Card>
    );
}

export default UsageLimit;