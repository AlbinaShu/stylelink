import { StarFilled } from '@ant-design/icons';
import styles from './Brand.module.css';

function Brand() {
  return (
    <div className={styles.brand}>
      <span className={styles.icon} aria-hidden="true">
        <StarFilled />
      </span>
      <span className={styles.name}>AI-StyleLink</span>
    </div>
  );
}

export default Brand;
