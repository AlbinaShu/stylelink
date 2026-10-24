import type {
  IOutfit,
} from '../../types';

import GenerationResultCard from '../GenerationResultCard/GenerationResultCard';

import styles from './GenerationResults.module.css';

interface IGenerationResultsProps {
  outfits: IOutfit[];
  shoeSize: number | null;
}

function GenerationResults({
  outfits,
  shoeSize,
}: IGenerationResultsProps) {
  return (
    <div className={styles.results}>
      {outfits.map((outfit, index) => (
        <GenerationResultCard
          key={outfit.id}
          outfit={outfit}
          number={index + 1}
          shoeSize={shoeSize}
        />
      ))}
    </div>
  );
}

export default GenerationResults;