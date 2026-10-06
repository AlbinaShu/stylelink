import {
    CheckOutlined,
    CrownOutlined,
} from '@ant-design/icons';
import {
    Button,
    Card,
    List,
    Space,
    Tag,
    Typography,
} from 'antd';

import styles from './SubscriptionPlans.module.css';

const { Title, Text } = Typography;

interface IPlan {
    title: string;
    price: string;
    description: string;
    features: string[];
    current?: boolean;
    popular?: boolean;
}

const plans: IPlan[] = [
    {
        title: 'Бесплатный',
        price: '0 ₽',
        description: 'Для знакомства с подбором образов',
        features: [
            '5 подборов образов',
            'Сохранение параметров тела',
            'История запросов',
        ],
        current: true,
    },
    {
        title: 'Pro',
        price: '490 ₽ / месяц',
        description: 'Больше возможностей для подбора',
        features: [
            'Безлимитные подборы',
            'Приоритетные рекомендации',
            'Больше вариантов образов',
        ],
        popular: true,
    },
];

function SubscriptionPlans() {
    return (
        <section className={styles.wrapper}>
            <div className={styles.heading}>
                <Title level={5}>
                    Тарифы
                </Title>
            </div>

            <div className={styles.cards}>
                {plans.map((plan) => (
                    <Card
                        key={plan.title}
                        className={[
                            styles.card,
                            plan.current ? styles.current : '',
                        ]
                            .filter(Boolean)
                            .join(' ')}
                    >
                        <Space
                            direction="vertical"
                            size={12}
                            className={styles.content}
                        >
                            <div className={styles.cardHeader}>
                                <div>
                                    <Space size={8}>
                                        <Title level={5}>
                                            {plan.title}
                                        </Title>

                                        {plan.popular && (
                                            <Tag
                                                color="magenta"
                                                icon={<CrownOutlined />}
                                            >
                                                Популярный
                                            </Tag>
                                        )}
                                    </Space>

                                    <Text className={styles.description}>
                                        {plan.description}
                                    </Text>
                                </div>

                                {plan.current && (
                                    <Tag color="default">
                                        Текущий
                                    </Tag>
                                )}
                            </div>

                            <div className={styles.price}>
                                {plan.price}
                            </div>

                            <List
                                className={styles.list}
                                size="small"
                                split={false}
                                dataSource={plan.features}
                                renderItem={(item) => (
                                    <List.Item>
                                        <Space size={8}>
                                            <CheckOutlined />

                                            <Text>
                                                {item}
                                            </Text>
                                        </Space>
                                    </List.Item>
                                )}
                            />

                            <Button
                                type={plan.current ? 'default' : 'primary'}
                                block
                                disabled={plan.current}
                                className={styles.button}
                            >
                                {plan.current
                                    ? 'Ваш тариф'
                                    : 'Подключить'}
                            </Button>
                        </Space>
                    </Card>
                ))}
            </div>
        </section>
    );
}

export default SubscriptionPlans;