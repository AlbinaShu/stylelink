export interface IGenerationForm {
  occasion: string | null;
  style: string | null;
  season: string | null;
  budget: number;
  gender: string | null;
  height: number | null;
  weight: number | null;
  shoe_size: number | null;
  chest: number | null;
  waist: number | null;
  hips: number | null;
  prompt: string;
}

export interface IGenerationOption {
  value: string;
  label: string;
}

export type GenerationStatus =
  | 'generating_queries'
  | 'searching_products'
  | 'forming_outfits'
  | 'collecting_fit_data'
  | 'predicting_fit'
  | 'completed'
  | 'failed';

export interface IGeneration {
  id: string;
  status: GenerationStatus;
  occasion: string | null;
  style: string | null;
  season: string | null;
  budget: number | null;
  shoe_size: number | null;
  prompt: string | null;
}

export interface IGenerationsPage {
  items: IGeneration[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export type MarketplaceId =
  | 'wildberries'
  | 'yandex_market'
  | 'ozon';

export interface IMarketplaceOffer {
  marketplace: MarketplaceId;
  product_id: string;
  name: string;
  brand: string | null;
  price: number;
  currency: 'RUB';
  image: string | null;
  url: string;
  available_sizes: string[];
  match_type: 'exact' | 'similar';
  match_score: number;
  verified_at: string;
}

export interface IOutfitItem {
  alternatives?: IMarketplaceOffer[];
  id: string;
  product_id: string;
  name: string;
  brand: string;
  price: number;
  image: string | null;
  marketplace: string;
  url: string;
  category: string | null;
  available_sizes: string[] | null;
  recommended_size: string | null;
  fit?: {
    status: 'predicted' | 'insufficient_evidence' | string;
    fit_signal: 'runs_small' | 'true_to_size' | 'runs_large' | null;
    confidence: number | null;
    num_reviews: number;
    num_fit_reviews: number;
    explanation: string | null;
    confidence_level: 'low' | 'medium' | 'high' | null;
  } | null;
}

export interface IOutfit {
  id: string;
  title: string;
  occasion: string | null;
  style: string | null;
  total_price: number;
  items: IOutfitItem[];
}
