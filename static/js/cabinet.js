import {getJson} from './lib/http.js';

const MAX_BACKOFF_MS = 5 * 60 * 1000;
const ICONS = {
  pending: '#i-clock',
  accepted: '#i-check-circle',
  rejected: '#i-x-circle',
};

class StatusPoller {
  constructor(root) {
    this.root_ = root;
    this.apiUrl_ = root.dataset.apiUrl;
    this.intervalMs_ = Math.max(5, Number(root.dataset.pollSeconds)) * 1000;
    this.delayMs_ = this.intervalMs_;
    this.timer_ = null;
  }

  start() {
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        this.stop_();
      } else {
        this.poll_();
      }
    });
    this.schedule_();
  }

  pendingIds_() {
    return [...this.root_.querySelectorAll('[data-status="pending"]')]
        .map((row) => row.dataset.receiptId);
  }

  schedule_() {
    this.stop_();
    if (!document.hidden && this.pendingIds_().length) {
      this.timer_ = window.setTimeout(() => this.poll_(), this.delayMs_);
    }
  }

  stop_() {
    if (this.timer_ !== null) window.clearTimeout(this.timer_);
    this.timer_ = null;
  }

  async poll_() {
    const ids = this.pendingIds_();
    if (!ids.length) return;
    const params = new URLSearchParams({ids: ids.join(','), page_size: '100'});
    try {
      const result = await getJson(`${this.apiUrl_}?${params}`);
      if (!result.ok) throw new Error(`HTTP ${result.status}`);
      result.data.results.forEach((receipt) => this.update_(receipt));
      this.delayMs_ = this.intervalMs_;
    } catch (e) {
      this.delayMs_ = Math.min(this.delayMs_ * 2, MAX_BACKOFF_MS);
    }
    this.schedule_();
  }

  update_(receipt) {
    const row = this.root_.querySelector(`[data-receipt-id="${receipt.id}"]`);
    if (!row || row.dataset.status === receipt.status) return;
    row.dataset.status = receipt.status;
    const badge = row.querySelector('[data-badge]');
    badge.className = `badge badge--${receipt.status}`;
    badge.querySelector('use').setAttribute('href', ICONS[receipt.status]);
    badge.querySelector('[data-badge-label]').textContent =
        receipt.status_display;
    row.querySelector('[data-info]').textContent = receipt.info;
    row.classList.remove('is-updated');
    void row.offsetWidth;
    row.classList.add('is-updated');
  }
}

const root = document.querySelector('[data-receipts]');
if (root) new StatusPoller(root).start();
