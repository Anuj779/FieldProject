// Browser speech synthesis. No API key or new service is required.
window.ClauseReader = (() => {
  let generation = 0, current = null;
  const supported = () => 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window;
  function stop() {
    generation++;
    if (supported()) speechSynthesis.cancel();
    current = null;
  }
  function sections(report) {
    const language = report.language || 'en';
    const entries = [];
    const add = (text, lang = language) => {
      if (!text) return;
      // Latin evidence/labels use an English voice, even in translated reports.
      if (!/[\u0900-\u097f]/.test(text)) lang = 'en';
      let chunk = '';
      for (const word of String(text).split(/\s+/)) {
        if (chunk.length + word.length > 220 && chunk) { entries.push({text: chunk, lang}); chunk = ''; }
        chunk += (chunk ? ' ' : '') + word;
      }
      if (chunk) entries.push({text: chunk, lang});
    };
    add(`Clausewise report. ${report.filename}. ${report.pages} pages. ${report.findings.length} findings.`, 'en');
    if (report.sample) add('Sample report. Fictional document with prepared explanations.', 'en');
    if (report.assessment) {
      const a = report.assessment;
      add(a.score == null ? 'Risk score unavailable.' : `Warning sign risk score: ${a.score} out of 100.`, 'en');
      for (const key of ['level', 'status', 'verdict', 'analysis_method', 'method']) add(a[key], 'en');
      for (const item of a.contributions || []) add(`${item.signal}: ${item.points} points.`, 'en');
      add('Confirm the offer with HR using contact details found independently on the employer official website. A score of zero does not establish authenticity.', 'en');
    }
    if (report.rejected) add(`${report.rejected} unsupported findings were excluded. This review may be incomplete.`, 'en');
    report.findings.forEach((f, i) => {
      add(`Finding ${i + 1}. Page ${f.page}.`, 'en');
      add(f.category_label || f.category); add(f.title); add(f.explanation);
      add('Original clause.', 'en'); add(f.quote);
      if (f.needs_clarification) { add('Ask the provider.', 'en'); add(f.question); }
    });
    add('End of report. Clausewise may make mistakes. Check the full document. This review does not establish legal enforceability or authenticity.', 'en');
    return entries;
  }
  function play(report, rate, update) {
    stop();
    if (!supported()) { update('error', 'Read aloud is not supported in this browser.'); return; }
    const queue = sections(report), voices = speechSynthesis.getVoices();
    const language = report.language || 'en';
    const select = lang => voices.find(v => v.lang.toLowerCase().startsWith(lang) && v.localService)
      || voices.find(v => v.lang.toLowerCase().startsWith(lang));
    if (language !== 'en' && !select(language)) {
      update('error', `No ${language === 'hi' ? 'Hindi' : 'Marathi'} voice is available. Install a matching system voice or use an English report.`);
      return;
    }
    const id = generation;
    let index = 0;
    function next() {
      if (id !== generation) return;
      if (index === queue.length) { current = null; update('idle', 'Finished reading the entire report.'); return; }
      const part = queue[index++];
      current = new SpeechSynthesisUtterance(part.text);
      current.lang = {en: 'en-IN', hi: 'hi-IN', mr: 'mr-IN'}[part.lang] || 'en-IN';
      const voice = select(part.lang);
      if (voice) current.voice = voice;
      current.rate = rate;
      current.onend = next;
      current.onerror = event => {
        if (id !== generation) return;
        stop(); update('error', 'Audio could not continue. Check your available voices and try again.');
      };
      update('playing', `Reading section ${index} of ${queue.length}`);
      speechSynthesis.speak(current);
    }
    next();
  }
  addEventListener('pagehide', stop);
  return {supported, sections, play, stop,
    pause: () => speechSynthesis.pause(), resume: () => speechSynthesis.resume()};
})();
