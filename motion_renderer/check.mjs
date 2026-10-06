import * as core from '@motion-canvas/core';
import * as twoD from '@motion-canvas/2d';

const requiredCore = ['makeProject', 'createRef', 'all', 'waitFor'];
const required2d = ['makeScene2D', 'Rect', 'Txt', 'Img'];

const missing = [
  ...requiredCore.filter((name) => !(name in core)).map((name) => `core:${name}`),
  ...required2d.filter((name) => !(name in twoD)).map((name) => `2d:${name}`),
];

if (missing.length) {
  throw new Error(`Motion Canvas installation incomplete: ${missing.join(', ')}`);
}

console.log(JSON.stringify({
  renderer: 'motion-canvas',
  status: 'ready',
  coreExports: requiredCore,
  twoDExports: required2d,
}));
