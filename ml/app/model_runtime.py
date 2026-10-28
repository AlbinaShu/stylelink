import io
import hashlib
import os
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.schemas import OutfitContext, OutfitProduct


FASHION_MODEL = "patrickjohncyh/fashion-clip"
FASHION_REVISION = "7e3ba62ce16b379a1ab479346b66f192e76f51b7"
TRANSLATION_MODEL = "Helsinki-NLP/opus-mt-ru-en"
TRANSLATION_REVISION = "fbd6dc73284f95536648512cc21d57f19191961a"
FIT_MODEL = "MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli"
FIT_REVISION = "0a71e92a985b6e1ad1828cf67ce9c459639c1dca"
B2_MODEL_SHA256 = "eafa3939077a2a3e5b28b611bea4e330fc6ccd14341e0fe13a260803fdb7891e"
B2_MODEL_FILENAME = "B2_tfidf_logistic_regression.joblib"
B2_LABELS = {"no_signal", "runs_large", "runs_small", "true_to_size"}
FIT_LABELS = {
    "маломерит": "runs_small",
    "идет размер в размер": "true_to_size",
    "большемерит": "runs_large",
}
ALLOWED_IMAGE_HOSTS = tuple(
    host.strip().lower()
    for host in os.getenv(
        "ML_IMAGE_HOSTS", "yandex.net,yandex.ru,wbbasket.ru,wildberries.ru"
    ).split(",")
    if host.strip()
)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def _fetch_image(url: str):
    from PIL import Image

    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not any(
        host == allowed or host.endswith("." + allowed)
        for allowed in ALLOWED_IMAGE_HOSTS
    ):
        return None

    try:
        request = Request(url, headers={"User-Agent": "AI-StyleLink/1.0"})
        with build_opener(_NoRedirect).open(request, timeout=3) as response:
            if not response.headers.get_content_type().startswith("image/"):
                return None
            data = response.read(5_000_001)
        if len(data) > 5_000_000:
            return None
        Image.MAX_IMAGE_PIXELS = 20_000_000
        with Image.open(io.BytesIO(data)) as image:
            image.thumbnail((1024, 1024))
            return image.convert("RGB")
    except (OSError, ValueError):
        return None


class OutfitModels:
    def __init__(self) -> None:
        import torch
        from transformers import AutoTokenizer, CLIPModel, CLIPProcessor, MarianMTModel

        self.torch = torch
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.clip = CLIPModel.from_pretrained(
            FASHION_MODEL, revision=FASHION_REVISION, attn_implementation="eager"
        ).to(self.device).eval()
        self.processor = CLIPProcessor.from_pretrained(
            FASHION_MODEL, revision=FASHION_REVISION
        )
        self.translator = MarianMTModel.from_pretrained(
            TRANSLATION_MODEL, revision=TRANSLATION_REVISION
        ).to(self.device).eval()
        self.translation_tokenizer = AutoTokenizer.from_pretrained(
            TRANSLATION_MODEL, revision=TRANSLATION_REVISION
        )

    def _translate(self, texts: list[str]) -> list[str]:
        if not texts:
            return []
        result = texts.copy()
        russian = [(index, text) for index, text in enumerate(texts) if re.search(r"[А-Яа-яЁё]", text)]
        for start in range(0, len(russian), 16):
            batch = russian[start : start + 16]
            inputs = self.translation_tokenizer(
                [text for _, text in batch], return_tensors="pt", padding=True,
                truncation=True, max_length=128,
            ).to(self.device)
            with self.torch.inference_mode():
                output = self.translator.generate(**inputs, max_new_tokens=80, num_beams=2)
            for (index, _), translated in zip(
                batch, self.translation_tokenizer.batch_decode(output, skip_special_tokens=True)
            ):
                result[index] = translated
        return result

    def _encode_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), 16):
            inputs = self.processor(
                text=texts[start : start + 16], return_tensors="pt", padding=True,
                truncation=True, max_length=77,
            ).to(self.device)
            with self.torch.inference_mode():
                output = self.clip.get_text_features(**inputs)
                output = self.torch.nn.functional.normalize(output, dim=-1)
            vectors.extend(output.cpu().tolist())
        return vectors

    def _encode_images(self, images: list) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(images), 16):
            inputs = self.processor(
                images=images[start : start + 16], return_tensors="pt"
            ).to(self.device)
            with self.torch.inference_mode():
                output = self.clip.get_image_features(**inputs)
                output = self.torch.nn.functional.normalize(output, dim=-1)
            vectors.extend(output.cpu().tolist())
        return vectors

    def encode_request(
        self, products: list[OutfitProduct], context: OutfitContext
    ) -> tuple[dict, list[float]]:
        prompt = " ".join(
            text for text in (context.prompt, context.style, context.occasion) if text
        )
        query = self._translate([prompt])[0] if prompt else "fashion outfit"
        query_vector = self._encode_texts([query])[0]

        with ThreadPoolExecutor(max_workers=8) as pool:
            images = list(pool.map(lambda item: _fetch_image(str(item.image_url)), products))

        vectors = {}
        available = [(item, image) for item, image in zip(products, images) if image]
        for (item, _), vector in zip(
            available, self._encode_images([image for _, image in available])
        ):
            vectors[item.product_id] = vector

        missing = [item for item, image in zip(products, images) if image is None]
        if missing:
            descriptions = [
                f"{item.name}. {item.description or ''}"[:300] for item in missing
            ]
            translated = self._translate(descriptions)
            for item, vector in zip(missing, self._encode_texts(translated)):
                vectors[item.product_id] = vector
        return vectors, query_vector


@dataclass(frozen=True)
class FitClassification:
    label: str
    confidence: float
    probabilities: dict[str, float]


class ZeroShotFitModel:
    backend = "zero_shot"

    def __init__(self) -> None:
        from transformers import pipeline

        self.classifier = pipeline(
            "zero-shot-classification", model=FIT_MODEL,
            revision=FIT_REVISION, device=-1,
        )

    def classify(self, texts: list[str]) -> list[FitClassification]:
        if not texts:
            return []
        output = self.classifier(
            texts,
            candidate_labels=list(FIT_LABELS),
            hypothesis_template="Одежда {}.",
            batch_size=16,
            truncation=True,
        )
        if isinstance(output, dict):
            output = [output]
        predictions = []
        for result in output:
            probabilities = {
                FIT_LABELS[label]: float(score)
                for label, score in zip(result["labels"], result["scores"])
            }
            winner = max(probabilities, key=probabilities.get)
            predictions.append(
                FitClassification(winner, probabilities[winner], probabilities)
            )
        return predictions


def _default_b2_model_path() -> Path:
    configured = os.getenv("B2_MODEL_PATH")
    if configured:
        return Path(configured).expanduser()
    container_path = Path("/app/models") / B2_MODEL_FILENAME
    if container_path.exists():
        return container_path
    project_root = Path(__file__).resolve().parents[2]
    return (
        project_root
        / "research/outputs/benchmarks/review_level/2026-10-24/models"
        / B2_MODEL_FILENAME
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class B2FitModel:
    backend = "b2"

    def __init__(self) -> None:
        import joblib

        self.path = _default_b2_model_path()
        if not self.path.is_file():
            raise RuntimeError(f"Frozen B2 model not found: {self.path}")
        actual_hash = _sha256(self.path)
        if actual_hash != B2_MODEL_SHA256:
            raise RuntimeError(
                "Frozen B2 model hash mismatch: "
                f"expected {B2_MODEL_SHA256}, got {actual_hash}"
            )
        self.classifier = joblib.load(self.path)
        classes = set(self.classifier.classes_)
        if classes != B2_LABELS:
            raise RuntimeError(f"Frozen B2 model has unexpected classes: {sorted(classes)}")

    def classify(self, texts: list[str]) -> list[FitClassification]:
        if not texts:
            return []
        matrix = self.classifier.predict_proba(texts)
        classes = list(self.classifier.classes_)
        predictions = []
        for values in matrix:
            probabilities = {
                label: float(values[classes.index(label)]) for label in classes
            }
            winner = max(probabilities, key=probabilities.get)
            predictions.append(
                FitClassification(winner, probabilities[winner], probabilities)
            )
        return predictions


@lru_cache(maxsize=1)
def get_outfit_models() -> OutfitModels:
    return OutfitModels()


@lru_cache(maxsize=1)
def get_fit_model() -> ZeroShotFitModel | B2FitModel:
    backend = os.getenv("FIT_MODEL_BACKEND", "b2").strip().lower()
    if backend == "b2":
        return B2FitModel()
    if backend == "zero_shot":
        return ZeroShotFitModel()
    raise RuntimeError(
        "FIT_MODEL_BACKEND must be either 'b2' or 'zero_shot', "
        f"got {backend!r}"
    )


def preload_models() -> None:
    get_outfit_models()
    get_fit_model()
