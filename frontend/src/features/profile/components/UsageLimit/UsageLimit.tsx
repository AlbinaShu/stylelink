import { Alert, Button, Card, Flex, Progress, Spin, Typography } from 'antd';
import { Link } from 'react-router-dom';
import { useGenerationUsage } from '../../../outfit-generation/hooks/useGenerationUsage';
import styles from './UsageLimit.module.css';

const { Text } = Typography;

function UsageLimit() {
    const { usage, error, loading, reload } = useGenerationUsage();
    if (loading) return <Spin />;
    if (error || !usage) {
        return <Alert type="error" title="Не удалось загрузить лимит подборов"
            action={<Button onClick={() => void reload()}>Повторить</Button>} />;
    }
    return (
        <Card className={styles.card}>
            <Flex vertical gap={8}>
                <Flex justify="space-between" align="center">
                    <Text className={styles.label}>Использовано подборов</Text>
                    <Text className={styles.value}>{usage.used} / {usage.limit}</Text>
                </Flex>
                <Progress percent={Math.min(100, (usage.used / usage.limit) * 100)}
                    showInfo={false} strokeColor="var(--primary)"
                    trailColor="var(--surface-muted)" className={styles.progress} />
                <Text className={styles.description}>
                    {usage.exhausted
                        ? 'Бесплатные подборы закончились. Неудачные подборы не расходуют лимит.'
                        : 'Осталось бесплатных подборов: ' + usage.remaining + '.'}
                </Text>
                <Link to="/plans">Посмотреть тарифы</Link>
            </Flex>
        </Card>
    );
}
export default UsageLimit;
