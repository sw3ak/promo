import {submitForm} from './lib/http.js';
import {parseQr, QrParseError} from './lib/qr.js';
import {
  validateAmount,
  validateFiscalInt,
  validateFn,
  validatePhoto,
  validatePurchasedAt,
} from './lib/validation.js';

const FIELDS = ['fn', 'fd', 'fp', 'purchased_at', 'amount'];
const NETWORK_ERROR =
    'Не удалось отправить чек. Проверьте подключение к интернету и попробуйте снова.';

class ReceiptForm {
  constructor(form) {
    this.form_ = form;
    this.card_ = form.closest('[data-receipt-card]');
    this.config_ = {
      start: form.dataset.promoStart,
      end: form.dataset.promoEnd,
      minAmount: Number(form.dataset.minAmount),
      photoMaxBytes: Number(form.dataset.photoMaxBytes),
    };
    this.touched_ = new Set();
    this.photoInput_ = form.elements.namedItem('photo');
    this.previewUrl_ = null;
  }

  init() {
    for (const name of FIELDS) {
      const input = this.input_(name);
      input.addEventListener('blur', () => {
        this.touched_.add(name);
        this.validateField_(name);
      });
      input.addEventListener('input', () => {
        this.syncEmptyState_(input);
        if (this.touched_.has(name)) this.validateField_(name);
      });
      this.syncEmptyState_(input);
    }
    this.form_.addEventListener('click', (event) => {
      const button = event.target.closest('[data-clear]');
      if (button) this.clearField_(button);
    });

    const qrInput = this.input_('qr_raw');
    qrInput.addEventListener('paste', () => {
      setTimeout(() => this.applyQr_(qrInput.value), 0);
    });
    qrInput.addEventListener('change', () => this.applyQr_(qrInput.value));

    this.photoInput_.addEventListener('change', () => this.onPhotoChange_());
    this.card_.querySelector('[data-photo-clear]')
        .addEventListener('click', (event) => {
          event.preventDefault();
          this.photoInput_.value = '';
          this.onPhotoChange_();
        });
    this.initDropzone_();

    this.form_.querySelector('[data-submit]')
        .addEventListener('mousedown', (event) => event.preventDefault());
    this.form_.addEventListener('submit', (event) => {
      event.preventDefault();
      this.submit_();
    });
    this.card_.querySelector('[data-register-more]')
        .addEventListener('click', (event) => {
          event.preventDefault();
          this.reset_();
        });
  }

  input_(name) {
    return this.form_.elements.namedItem(name);
  }

  errorFor_(name) {
    const value = this.input_(name).value;
    switch (name) {
      case 'fn':
        return validateFn(value);
      case 'fd':
        return validateFiscalInt(value, 'ФД');
      case 'fp':
        return validateFiscalInt(value, 'ФП');
      case 'purchased_at':
        return validatePurchasedAt(value, this.config_);
      case 'amount':
        return validateAmount(value, this.config_.minAmount);
      case 'photo':
        return validatePhoto(
            this.photoInput_.files?.[0] ?? null, this.config_.photoMaxBytes);
      default:
        return null;
    }
  }

  validateField_(name) {
    const message = this.errorFor_(name);
    this.showError_(name, message);
    return !message;
  }

  showError_(name, message) {
    const field = this.form_.querySelector(`[data-field="${name}"]`);
    if (!field) return;
    const error = field.querySelector('.field__error');
    field.classList.toggle('field--invalid', Boolean(message));
    error.hidden = !message;
    error.querySelector('[data-error-text]').textContent = message || '';
    const input = field.querySelector('input');
    if (message) {
      input.setAttribute('aria-invalid', 'true');
    } else {
      input.removeAttribute('aria-invalid');
    }
  }

  syncEmptyState_(input) {
    input.classList.toggle('is-empty', !input.value);
  }

  clearField_(button) {
    const input = button.closest('.field__control').querySelector('input');
    input.value = '';
    input.focus();
    this.showError_(input.name, null);
    this.syncEmptyState_(input);
  }

  applyQr_(raw) {
    if (!raw.trim()) {
      this.showError_('qr_raw', null);
      return;
    }
    let data;
    try {
      data = parseQr(raw);
    } catch (e) {
      if (!(e instanceof QrParseError)) throw e;
      this.showError_('qr_raw', e.message);
      return;
    }
    this.showError_('qr_raw', null);
    const values = {
      fn: data.fn,
      fd: data.fd,
      fp: data.fp,
      purchased_at: data.purchasedAt,
      amount: data.amount,
    };
    for (const name of FIELDS) {
      const input = this.input_(name);
      input.value = values[name];
      this.syncEmptyState_(input);
      this.touched_.add(name);
      this.validateField_(name);
    }
    this.announceQr_('Поля заполнены из QR-кода. Проверьте данные.');
  }

  announceQr_(text) {
    const field = this.form_.querySelector('[data-field="qr_raw"]');
    let status = field.querySelector('.qr__status');
    if (!status) {
      status = document.createElement('p');
      status.className = 'qr__status';
      status.setAttribute('role', 'status');
      field.append(status);
    }
    status.textContent = text;
  }

  onPhotoChange_() {
    const file = this.photoInput_.files?.[0] ?? null;
    const preview = this.card_.querySelector('[data-photo-preview]');
    const icon = this.card_.querySelector('[data-photo-icon]');
    const name = this.card_.querySelector('[data-photo-name]');
    const clear = this.card_.querySelector('[data-photo-clear]');
    if (this.previewUrl_) URL.revokeObjectURL(this.previewUrl_);
    this.previewUrl_ = null;

    const valid = this.validateField_('photo');
    if (!file || !valid) {
      preview.hidden = true;
      icon.hidden = false;
      name.textContent = file ? file.name : 'Выберите или перетащите фото';
      clear.hidden = !file;
      return;
    }
    this.previewUrl_ = URL.createObjectURL(file);
    preview.src = this.previewUrl_;
    preview.hidden = false;
    icon.hidden = true;
    name.textContent = file.name;
    clear.hidden = false;
    this.detectQr_(file);
  }

  async detectQr_(file) {
    if (!('BarcodeDetector' in window)) return;
    const hasData = FIELDS.some((name) => this.input_(name).value);
    if (hasData) return;
    try {
      const detector = new window.BarcodeDetector({formats: ['qr_code']});
      const bitmap = await createImageBitmap(file);
      const [code] = await detector.detect(bitmap);
      if (code?.rawValue) {
        this.form_.querySelector('details.qr').open = true;
        this.input_('qr_raw').value = code.rawValue;
        this.applyQr_(code.rawValue);
      }
    } catch {}
  }

  initDropzone_() {
    const zone = this.card_.querySelector('.upload');
    zone.addEventListener('dragover', (event) => {
      event.preventDefault();
      zone.classList.add('is-dragover');
    });
    zone.addEventListener('dragleave', () => {
      zone.classList.remove('is-dragover');
    });
    zone.addEventListener('drop', (event) => {
      event.preventDefault();
      zone.classList.remove('is-dragover');
      if (event.dataTransfer?.files.length) {
        this.photoInput_.files = event.dataTransfer.files;
        this.onPhotoChange_();
      }
    });
  }

  validateAll_() {
    let firstInvalid = null;
    for (const name of [...FIELDS, 'photo']) {
      this.touched_.add(name);
      if (!this.validateField_(name) && !firstInvalid) firstInvalid = name;
    }
    if (firstInvalid) this.input_(firstInvalid).focus();
    return !firstInvalid;
  }

  async submit_() {
    this.showAlert_(null);
    if (!this.validateAll_()) return;
    this.setBusy_(true);
    let result;
    try {
      result = await submitForm(this.form_);
    } catch (e) {
      this.showAlert_(NETWORK_ERROR);
      return;
    } finally {
      this.setBusy_(false);
    }
    if (result.status === 201) {
      this.showSuccess_(result.data);
      return;
    }
    const errors = result.data.errors || {};
    for (const [name, messages] of Object.entries(errors)) {
      if (name !== '__all__') this.showError_(name, messages[0]);
    }
    const message = errors.__all__?.[0] || result.data.message ||
        'Сервер не смог обработать чек. Попробуйте позже.';
    this.showAlert_(message);
    const firstName = Object.keys(errors).find((name) => name !== '__all__');
    if (firstName) this.input_(firstName)?.focus();
  }

  setBusy_(busy) {
    const button = this.form_.querySelector('[data-submit]');
    button.disabled = busy;
    button.querySelector('[data-submit-label]').textContent =
        busy ? 'Загружаем…' : 'Загрузить';
  }

  showAlert_(message) {
    const alert = this.card_.querySelector('[data-form-alert]');
    alert.hidden = !message;
    alert.querySelector('[data-form-alert-text]').textContent = message || '';
    if (message) alert.scrollIntoView({block: 'nearest', behavior: 'smooth'});
  }

  showSuccess_(data) {
    this.card_.querySelector('[data-form-view]').hidden = true;
    const view = this.card_.querySelector('[data-success-view]');
    view.querySelector('[data-success-title]').textContent =
        data.resubmitted ? 'Чек отправлен повторно' : 'Ваш чек загружен';
    view.hidden = false;
    view.focus();
  }

  reset_() {
    this.form_.reset();
    this.touched_.clear();
    for (const name of [...FIELDS, 'qr_raw', 'photo']) {
      this.showError_(name, null);
    }
    for (const name of FIELDS) this.syncEmptyState_(this.input_(name));
    this.form_.querySelector('.qr__status')?.remove();
    this.onPhotoChange_();
    this.card_.querySelector('[data-success-view]').hidden = true;
    this.card_.querySelector('[data-form-view]').hidden = false;
    this.input_('fn').focus();
  }
}

const formElement = document.querySelector('[data-receipt-form]');
if (formElement) {
  new ReceiptForm(formElement).init();
}
