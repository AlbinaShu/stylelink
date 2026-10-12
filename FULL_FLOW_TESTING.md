# Full-flow local test

The app flow is: frontend form -> backend generation -> GigaChat search queries -> Yandex Market product cards -> ML outfits -> selected-product reviews -> ML fit signals -> backend results page.

1. Put real GigaChat credentials and a model name in `backend/.env`, using `backend/.env.example` as a template. SMTP credentials are also required for registering a new user through the UI. Do not commit the `.env` file.
2. From the repository root, start the full stack:

   ```sh
   docker compose -f backend/docker-compose.yml -f backend/docker-compose.full.yml up -d --build
   ```

3. Open `http://localhost:5173`, register or log in, and submit a request from "Подобрать образы". The page polls generation status and then shows product links and any fit signals.

Backend docs: `http://localhost:8000/docs`. ML docs: `http://localhost:8001/docs`.

The backend searches Yandex Market. On October 10, 2026, a live request reached GigaChat successfully and saved its search phrases, but product cards returned a CAPTCHA. The live marketplace flow therefore could not reach ML. The backend marks this as a failed generation rather than reporting an empty result. The ML service does not yet recommend a personal clothing size. If a generation fails, inspect `docker compose -f backend/docker-compose.yml -f backend/docker-compose.full.yml logs backend ml`.

An isolated smoke test with test product cards passed through backend HTTP, PostgreSQL, the real outfit and fit ML services, and the results API. It does not prove that live Yandex Market cards are accessible.

The local services bind to `127.0.0.1` only. Do not use placeholder credentials for a real user test. The Yandex Market CAPTCHA requires an agreed product-data source; an old affiliate `GET /search` API is no longer supported.
