import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import test from 'node:test';
import ts from 'typescript';
import { translate, translations } from '../src/shared/i18n/translations.ts';

const sourceRoot = resolve(import.meta.dirname, '../src');

function sourceFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    return /\.tsx?$/.test(entry.name) && entry.name !== 'translations.ts' ? [path] : [];
  });
}

test('Russian remains the default source text', () => {
  assert.equal(translate('ru', 'Начать подбор'), 'Начать подбор');
  assert.equal(translate('ru', 'Образ {number}', { number: 2 }), 'Образ 2');
});

test('English text and interpolation are available', () => {
  assert.equal(translate('en', 'Начать подбор'), 'Create an outfit');
  assert.equal(translate('en', 'Образ {number}', { number: 2 }), 'Outfit 2');
});

test('every direct translation key has an English entry', () => {
  const missing = new Set();
  for (const path of sourceFiles(sourceRoot)) {
    const source = ts.createSourceFile(path, readFileSync(path, 'utf8'), ts.ScriptTarget.Latest, true);
    const visit = (node) => {
      if (ts.isCallExpression(node) && ts.isIdentifier(node.expression) && node.expression.text === 't') {
        const first = node.arguments[0];
        const candidates = first && ts.isConditionalExpression(first)
          ? [first.whenTrue, first.whenFalse] : [first];
        for (const candidate of candidates) {
          if (candidate && ts.isStringLiteral(candidate) && !(candidate.text in translations)) {
            missing.add(candidate.text);
          }
        }
      }
      ts.forEachChild(node, visit);
    };
    visit(source);
  }
  assert.deepEqual([...missing].sort(), []);
});

test('static interface option labels have English entries', () => {
  const optionFiles = [
    'pages/LandingPage/LandingPage.tsx',
    'shared/ui/AppBottomNav/AppBottomNav.tsx',
    'features/outfit-generation/components/GenerationForm/GenerationForm.tsx',
    'features/outfit-generation/components/GenerationHistory/GenerationHistory.tsx',
    'features/outfit-generation/components/GenerationLoading/GenerationLoading.tsx',
    'features/outfit-generation/components/GenerationResultCard/GenerationResultCard.tsx',
    'features/profile/components/ProfileMenu/ProfileMenu.tsx',
    'features/profile/components/SubscriptionPlans/SubscriptionPlans.tsx',
    'features/survey/configurations/survey-questions.ts',
  ];
  const missing = new Set();
  for (const file of optionFiles) {
    const path = join(sourceRoot, file);
    const source = ts.createSourceFile(path, readFileSync(path, 'utf8'), ts.ScriptTarget.Latest, true);
    const visit = (node) => {
      if (ts.isStringLiteral(node) && /[А-Яа-яЁё]/.test(node.text) && !(node.text in translations)) {
        missing.add(node.text);
      }
      ts.forEachChild(node, visit);
    };
    visit(source);
  }
  assert.deepEqual([...missing].sort(), []);
});
