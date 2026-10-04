document.addEventListener('alpine:init', () => {
  let authSdk, authInstance, currentUser;
  Alpine.data('clausewise', () => ({
    view: location.pathname === '/login' ? 'login' : location.pathname === '/workspace' ? 'workspace' : 'home',
    config: {firebase: null, ai_ready: false}, configLoaded: false, authReady: false,
    user: null, email: '', password: '', showPassword: false,
    authMode: 'login', authBusy: false, busy: false, error: '', message: '',
    file: null, consent: false, dragging: false, result: null, filter: 'All', operation: 0,
    get categories() { return [...new Set((this.result?.findings || []).map(f => f.category))]; },
    get filteredFindings() { return (this.result?.findings || []).filter(f => this.filter === 'All' || f.category === this.filter); },
    async init() {
      window.addEventListener('popstate', () => { this.view = location.pathname === '/login' ? 'login' : location.pathname === '/workspace' ? (this.user ? 'workspace' : 'login') : 'home'; });
      try {
        this.config = await this.json('/api/config');
        if (this.config.firebase) {
          const app = await import('https://www.gstatic.com/firebasejs/12.19.0/firebase-app.js');
          authSdk = await import('https://www.gstatic.com/firebasejs/12.19.0/firebase-auth.js');
          authInstance = authSdk.getAuth(app.initializeApp(this.config.firebase));
          await authSdk.setPersistence(authInstance, authSdk.browserSessionPersistence);
          authSdk.onAuthStateChanged(authInstance, user => {
            const wasSignedIn = !!this.user;
            currentUser = user;
            this.user = user ? {uid: user.uid, email: user.email} : null;
            this.authReady = true;
            if (!user && wasSignedIn) { this.operation++; this.result = null; this.file = null; this.consent = false; this.busy = false; this.go('login'); }
            if (!user && this.view === 'workspace') this.go('login');
            if (user && this.view === 'login') this.go('workspace');
          });
        } else if (this.view === 'workspace') this.go('login');
      } catch (error) { this.error = 'We could not connect to sign-in. Check your connection and refresh the page. The sample may still be available.'; }
      finally { this.configLoaded = true; }
    },
    go(view, updateUrl = true) {
      this.view = view; this.error = ''; this.message = '';
      this.$nextTick(() => window.ClauseMotion?.refresh());
      if (updateUrl) { history.pushState({}, '', view === 'home' ? '/' : view === 'results' ? '/#review' : '/' + view); window.scrollTo({top: 0, behavior: 'instant'}); }
    },
    openWorkspace() { this.go(this.user ? 'workspace' : 'login'); },
    setAuthMode(mode) { this.authMode = mode; this.error = ''; this.message = ''; this.password = ''; },
    async json(url, options) {
      const response = await fetch(url, options);
      let body;
      try { body = await response.json(); } catch { throw new Error('The server could not complete this request. Please try again.'); }
      if (!response.ok) throw new Error(body.error || 'Something went wrong. Please try again.');
      return body;
    },
    async authenticate() {
      if (!this.authReady || this.authBusy) return;
      this.error = ''; this.message = ''; this.authBusy = true;
      try {
        if (this.authMode === 'reset') {
          await authSdk.sendPasswordResetEmail(authInstance, this.email);
          this.message = 'If an account exists for this email, you’ll receive a password reset link.';
        } else if (this.authMode === 'signup') {
          await authSdk.createUserWithEmailAndPassword(authInstance, this.email, this.password);
          this.password = ''; this.go('workspace');
        } else {
          await authSdk.signInWithEmailAndPassword(authInstance, this.email, this.password);
          this.password = ''; this.go('workspace');
        }
      } catch (error) {
        const errors = {'auth/invalid-credential': 'Email or password is incorrect.', 'auth/invalid-email': 'Enter a valid email address.', 'auth/weak-password': 'Choose a stronger password with at least 8 characters.', 'auth/email-already-in-use': 'We could not create this account. Try signing in or resetting your password.', 'auth/too-many-requests': 'Too many attempts. Please wait a little and try again.', 'auth/network-request-failed': 'Check your internet connection and try again.'};
        this.error = errors[error.code] || 'Sign-in could not be completed. Check your details or try again later.';
      } finally { this.authBusy = false; }
    },
    async logout() {
      try { await authSdk.signOut(authInstance); this.operation++; this.result = null; this.file = null; this.consent = false; this.password = ''; this.busy = false; this.go('home'); }
      catch { this.error = 'Sign-out failed. Please try again.'; }
    },
    selectFile(file) {
      if (this.busy) return;
      this.error = ''; this.file = null;
      if (!file) return;
      if (!file.name.toLowerCase().endsWith('.pdf')) { this.error = 'Please choose a PDF file.'; return; }
      if (file.size > 10 * 1024 * 1024) { this.error = 'Choose a PDF smaller than 10 MB.'; return; }
      if (file.size === 0) { this.error = 'This file is empty. Choose another PDF.'; return; }
      this.file = file; this.consent = false;
    },
    async loadSample() {
      if (this.busy) return;
      this.busy = true; this.error = '';
      const op = ++this.operation;
      try { const data = await this.json('/api/sample'); if (op !== this.operation) return; this.result = data; this.filter = 'All'; this.go('results'); }
      catch (error) { this.error = error.message; }
      finally { if (op === this.operation) this.busy = false; }
    },
    async analyze() {
      if (!this.user) { this.go('login'); return; }
      if (!this.file || !this.consent || this.busy) return;
      this.busy = true; this.error = '';
      const op = ++this.operation;
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 150000);
      try {
        const token = await currentUser.getIdToken();
        const form = new FormData(); form.append('file', this.file);
        const data = await this.json('/api/analyze', {method: 'POST', headers: {Authorization: 'Bearer ' + token}, body: form, signal: controller.signal});
        if (op !== this.operation || !this.user) return;
        this.result = data; this.filter = 'All'; this.go('results');
      } catch (error) { if (op === this.operation) this.error = error.name === 'AbortError' ? 'This analysis took too long. Please retry with a shorter document.' : error.message; }
      finally { clearTimeout(timer); if (op === this.operation) this.busy = false; }
    },
    downloadReport() {
      if (!this.result) return;
      const bytes = Uint8Array.from(atob(this.result.report), c => c.charCodeAt(0));
      const url = URL.createObjectURL(new Blob([bytes], {type: 'application/pdf'}));
      const link = document.createElement('a'); link.href = url; link.download = this.result.sample ? 'Clausewise-sample-review.pdf' : 'Clausewise-agreement-review.pdf'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
  }));
});
