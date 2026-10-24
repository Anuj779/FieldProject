// Exercise report language controls without external authentication or AI calls.
const vm = require('node:vm');
const fs = require('node:fs');
const assert = require('node:assert/strict');
let factory;
const context = {
  document: {addEventListener: (_, callback) => callback()},
  Alpine: {data: (_, callback) => {factory = callback;}},
  location: {pathname: '/workspace'}, window: {},
};
vm.runInNewContext(fs.readFileSync('static/app.js', 'utf8'), context);
(async () => {
  const state = factory();
  state.result = {document_hash:'one', language:'en', sample:false};
  state.file = {}; state.consent = true;
  state.reportLanguage = 'hi';
  let requested = '';
  state.analyze = async preserve => {assert.equal(preserve, true); requested = state.language;};
  await state.changeReportLanguage();
  assert.equal(requested, 'hi');
  state.reportCache['one:agreement:mr'] = {language:'mr', report:'marathi-pdf'};
  state.reportLanguage = 'mr';
  state.showReport = data => {state.result = data;};
  await state.changeReportLanguage();
  assert.equal(state.result.report, 'marathi-pdf');
  assert.equal(requested, 'hi'); // Cached language requires no AI request.
  console.log('PASS: language request and cached PDF switching');
})().catch(error => {console.error(error); process.exit(1);});
