// Browser integration of multipart submission and retry; external services are mocked.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({headless:true});
  try {
    const page = await browser.newPage({reducedMotion:'reduce'});
    await page.addInitScript(() => {
      const original = window.fetch;
      window.fetch = async (...args) => {
        if (args[0] === '/api/analyze') {
          const file = args[1].body.get('file');
          window.uploadHeader = new TextDecoder().decode((await file.arrayBuffer()).slice(0, 5));
        }
        return original(...args);
      };
    });
    const errors=[]; page.on('pageerror', e=>errors.push(e.message));
    await page.route('**/api/config', r=>r.fulfill({json:{firebase:{projectId:'test'},ai_ready:true}}));
    await page.route('**/firebase-app.js', r=>r.fulfill({contentType:'application/javascript',body:'export const initializeApp = () => ({});'}));
    await page.route('**/firebase-auth.js', r=>r.fulfill({contentType:'application/javascript',body:`
      export const getAuth = () => ({});
      export const browserSessionPersistence = {};
      export const setPersistence = async () => {};
      export const onAuthStateChanged = (a, fn) => fn({uid:'test', email:'test@example.com',getIdToken:async()=> 'test-token'});
    `}));
    const base = process.env.BASE_URL || 'http://127.0.0.1:5001';
    const fixture = await (await page.request.get(base+'/api/sample')).json();
    fixture.sample=false;
    fixture.analysis_source='live_ai';
    fixture.document_hash = require('node:crypto').createHash('sha256').update(require('node:fs').readFileSync('output/pdf/Clausewise-Sample-Agreement.pdf')).digest('hex');
    let calls=0;
    await page.route('**/api/analyze', async route=>{
      const req=route.request();
      assert.equal(req.headers().authorization,'Bearer test-token');
      assert.ok(req.headers()['content-type'].includes('multipart/form-data'));
      // Chromium omits file bytes from intercepted postData; inspect the FormData File instead.
      assert.equal(await page.evaluate(()=>window.uploadHeader), '%PDF-');
      calls++;
      if(calls===1) await route.fulfill({status:413,contentType:'text/plain',body:'FUNCTION_PAYLOAD_TOO_LARGE'});
      else if(calls===2) await route.fulfill({json:{...fixture,sample:true}});
      else await route.fulfill({json:fixture});
    });
    await page.goto(base+'/workspace');
    await page.waitForFunction(()=>Alpine.$data(document.body).authReady);
    const path='output/pdf/Clausewise-Sample-Agreement.pdf';
    await page.locator('#pdf-file').setInputFiles(path);
    await page.locator('.consent input').check();
    await page.getByRole('button',{name:'Analyze agreement',exact:false}).last().click();
    await page.waitForFunction(()=>Alpine.$data(document.body).error.includes('hosting limit'));
    await page.locator('#pdf-file').setInputFiles(path);
    assert.equal(await page.locator('.consent input').isChecked(),false);
    await page.locator('.consent input').check();
    await page.getByRole('button',{name:'Analyze agreement',exact:false}).last().click();
    await page.waitForFunction(()=>Alpine.$data(document.body).error.includes('could not be matched'));
    assert.equal(await page.locator('.results').isVisible(),false);
    await page.getByRole('button',{name:'Analyze agreement',exact:false}).last().click();
    await page.locator('.finding').first().waitFor();
    assert.equal(calls,3); assert.equal(new URL(page.url()).pathname,'/workspace');
    assert.deepEqual(errors,[]);
    console.log('PASS: PDF multipart submission, hosting error, same-file retry, rejection of sample substitution, matched inline report.');
  } finally {await browser.close();}
})().catch(e=>{console.error(e.message);process.exit(1);});
