# ML API

This directory contains the ML service currently used by the product. Its size-shift endpoint is an integration prototype based on a pretrained zero-shot NLI model, keyword filtering, equal-count aggregation, and fixed evidence thresholds.

The offline review-level comparison is complete: B0, B1, TF-IDF + Logistic Regression (B2), frozen ruBERT and frozen DistilRuBERT were evaluated on the same five frozen group folds. B2 was selected and frozen with a confidence/abstain threshold of `0.60`; it was then evaluated on 300 Yandex Market reviews. The item-level equal-weight versus informativeness-weighted comparison was also run as an exploratory pilot on 40 products. It did not select a winner because there is no independent item-level Gold Standard yet.

These research artifacts are **not integrated into this service yet**. Therefore, local website results still come from the zero-shot prototype described below, not from the selected B2 model.

Research results, limitations, and reproducibility links are maintained in [`../docs/research/`](../docs/research/README.md).

This service runs pretrained models without fine-tuning:

- [FashionCLIP 2.0](https://huggingface.co/patrickjohncyh/fashion-clip) embeds product images and compares them to the user's request. It was trained mainly on English fashion descriptions.
- [OPUS-MT ru-en](https://huggingface.co/Helsinki-NLP/opus-mt-ru-en) translates Russian requests and fallback product descriptions for FashionCLIP.
- [Multilingual MiniLM NLI](https://huggingface.co/MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli) classifies Russian fit-related reviews without task-specific training. This is not ruBERT. Model revisions are pinned in `app/model_runtime.py` for reproducibility.

`POST /api/v1/outfits` validates up to 100 products, considers the first eight in each category, and returns up to five category-complete outfits within budget. An outfit has a dress and shoes or a top, bottom and shoes; outerwear and accessories are optional. It uses FashionCLIP image vectors when an image is reachable and falls back to translated product text otherwise. The outfit score combines query relevance (80%) and mean pairwise embedding similarity (20%). Pairwise similarity is only a visual/semantic coherence proxy, **not** a trained outfit-compatibility model or a calibrated probability. The output contains no embeddings because the current backend contract does not ask for them.

`POST /v1/size-shift/predict` selects at most 20 distinct fit-related reviews per product, classifies them, and returns a product-level `fit_signal` only when at least three reviews have confident labels and at least 60% agree. `confidence` is an uncalibrated agreement/model-score heuristic. `recommended_size` stays null: the request has no user measurements or reliable size chart, so a personal S/M/L cannot be inferred.

The service loads weights before accepting requests. First startup downloads roughly 1-2 GB into a persistent Docker volume and may take several minutes; later starts reuse the cache. Failed downloads or model loading stop the container instead of silently reverting to stub answers. Product-image requests are HTTPS-only, do not follow redirects, and are restricted by `ML_IMAGE_HOSTS` (comma-separated domain suffixes, defaulting to Yandex Market and Wildberries image hosts). Missing or blocked images use the product-text fallback. On a Mac, Docker runs the models on CPU; running the API directly on macOS can use MPS/Metal.

From the `backend` directory:

```sh
docker compose up -d --build postgres ml
docker compose logs -f ml
```

When backend runs on the host, set in `backend/.env`:

```text
FASHION_CLIP_URL=http://127.0.0.1:8001
SIZE_SHIFT_URL=http://127.0.0.1:8001
```

For a backend container in the same Compose network, use `http://ml:8001` for both URLs. API docs are at `http://localhost:8001/docs` after the ML container becomes healthy. The backend timeout is currently 60 seconds; benchmark it with actual catalog images and review volumes before calling this production-ready.
