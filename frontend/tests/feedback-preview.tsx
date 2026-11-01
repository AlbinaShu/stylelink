// Local browser fixture only; excluded from the production entrypoint.
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { ConfigProvider } from 'antd';
import GenerationFeedback from '../src/features/feedback/components/GenerationFeedback/GenerationFeedback';
import type { IFeedbackRating } from '../src/features/feedback/types';
import http from '../src/shared/api/http-client';
import '../src/styles/index.css';

const number = Number(new URLSearchParams(location.search).get('generation') ?? 1);
const generationId = 'preview-' + number;
type State = { service: IFeedbackRating | null; selection: Record<string, IFeedbackRating>; prompted: boolean; events: unknown[] };
const read = (): State => JSON.parse(localStorage.getItem('feedback-preview') ??
  '{"service":null,"selection":{},"prompted":false,"events":[]}');

http.defaults.adapter = async config => {
  const state = read();
  const url = config.url ?? '';
  const body = typeof config.data === 'string' ? JSON.parse(config.data) : config.data;
  let data: unknown;
  if (url.endsWith('/invitation')) {
    data = { show: number >= 3 && !state.service && !state.prompted };
    if ((data as { show: boolean }).show) state.prompted = true;
  } else if (url.endsWith('/events')) {
    state.events.push(body);
    data = { status: 'ok' };
  } else if (url.includes('/ratings/')) {
    if (sessionStorage.getItem('fail-feedback') === 'yes') throw new Error('Simulated network failure');
    const rating = { ...body, generation_id: generationId, generation_number: number };
    if (url.endsWith('/service')) state.service = rating;
    else state.selection[generationId] = rating;
    data = rating;
  } else {
    data = { generation_number: number, completed_count: number,
      selection: state.selection[generationId] ?? null, service: state.service,
      invitation_eligible: number >= 3 && !state.service && !state.prompted };
  }
  localStorage.setItem('feedback-preview', JSON.stringify(state));
  return { data, status: 200, statusText: 'OK', headers: {}, config };
};

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ConfigProvider theme={{ token: { colorPrimary: '#8B3045', borderRadius: 13, fontFamily: 'Inter, Arial, sans-serif' } }}>
      <main style={{ maxWidth: 760, margin: '24px auto', padding: '0 12px 48px' }}>
        <h1 style={{ fontSize: 24 }}>AI StyleLink</h1>
        <GenerationFeedback generationId={generationId}>
          <section style={{ background: '#f5ebe3', borderRadius: 14, padding: 24, marginTop: 12 }}>
            <h2>Подборка для офиса</h2>
            <p>Повседневный деловой стиль · Весна · До 15 000 ₽</p>
            <p>Результаты подбора — демонстрационный блок для проверки формы обратной связи.</p>
          </section>
        </GenerationFeedback>
      </main>
    </ConfigProvider>
  </StrictMode>,
);
