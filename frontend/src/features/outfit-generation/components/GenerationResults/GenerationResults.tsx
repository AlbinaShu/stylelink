import type {
  IOutfit,
} from '../../types';

import GenerationResultCard from '../GenerationResultCard/GenerationResultCard';

import styles from './GenerationResults.module.css';

interface IGenerationResultsProps {
  outfits: IOutfit[];
}

function GenerationResults({
  outfits,
}: IGenerationResultsProps) {
  return (
    <div className={styles.results}>
      {outfits.map((outfit, index) => (
        <GenerationResultCard
          key={outfit.id}
          outfit={outfit}
          number={index + 1}
        />
      ))}
    </div>
  );
}

export default GenerationResults;