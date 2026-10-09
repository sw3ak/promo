export const FN_LENGTH = 16;
export const FISCAL_INT_MAX = 4294967295;
export const PHOTO_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_UTC_OFFSET_MS = 14 * 60 * 60 * 1000;
const MAX_AMOUNT = 99999999.99;

const DIGITS = /^[0-9]+$/;
const AMOUNT = /^[0-9]+(?:[.,][0-9]{1,2})?$/;
const DATETIME = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?$/;
const REQUIRED = 'Обязательное поле.';

export function stripSpaces(value) {
  return String(value ?? '').replace(/[\s ]+/g, '');
}

export function validateFn(value) {
  const fn = stripSpaces(value);
  if (!fn) return REQUIRED;
  if (!DIGITS.test(fn) || fn.length !== FN_LENGTH) {
    return 'ФН состоит ровно из 16 цифр.';
  }
  return null;
}

export function validateFiscalInt(value, label) {
  const digits = stripSpaces(value);
  if (!digits) return REQUIRED;
  if (!DIGITS.test(digits) || digits.length > 10) {
    return `${label} - число до 10 цифр.`;
  }
  const number = Number(digits);
  if (number < 1 || number > FISCAL_INT_MAX) {
    return `${label} должен быть от 1 до ${FISCAL_INT_MAX}.`;
  }
  return null;
}

export function parseAmount(value) {
  const text = stripSpaces(value).replace('₽', '');
  if (!AMOUNT.test(text)) return null;
  return Number(text.replace(',', '.'));
}

export function formatRub(value) {
  return Math.round(value).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
}

export function validateAmount(value, minAmount) {
  if (!stripSpaces(value)) return REQUIRED;
  const amount = parseAmount(value);
  if (amount === null) {
    return 'Введите сумму в рублях, например 1500 или 1500.50.';
  }
  if (amount > MAX_AMOUNT) return 'Слишком большая сумма.';
  if (amount < minAmount) {
    return `Минимальная сумма чека - ${formatRub(minAmount)} ₽.`;
  }
  return null;
}

export function parseDateTime(value) {
  const match = DATETIME.exec(String(value ?? '').trim());
  if (!match) return null;
  const [, y, mo, d, h, mi, s] = match.map((part) => Number(part ?? 0));
  const utcMs = Date.UTC(y, mo - 1, d, h, mi, s);
  const check = new Date(utcMs);
  if (check.getUTCMonth() !== mo - 1 || check.getUTCDate() !== d ||
      h > 23 || mi > 59 || s > 59) {
    return null;
  }
  return {date: match[0].slice(0, 10), utcMs};
}

export function validatePurchasedAt(value, {start, end, nowMs = Date.now()}) {
  if (!String(value ?? '').trim()) return REQUIRED;
  const parsed = parseDateTime(value);
  if (!parsed) return 'Введите дату и время покупки.';
  if (parsed.utcMs > nowMs + MAX_UTC_OFFSET_MS) {
    return 'Дата покупки не может быть в будущем.';
  }
  if (parsed.date < start || parsed.date > end) {
    return 'Покупка должна быть совершена в период акции: ' +
        `с ${toRuDate(start)} по ${toRuDate(end)}.`;
  }
  return null;
}

function toRuDate(isoDate) {
  return isoDate.split('-').reverse().join('.');
}

export function validatePhoto(file, maxBytes) {
  if (!file) return null;
  if (!PHOTO_TYPES.includes(file.type)) {
    return 'Поддерживаются только JPEG, PNG и WEBP.';
  }
  if (file.size > maxBytes) {
    return `Файл больше ${Math.floor(maxBytes / (1024 * 1024))} МБ.`;
  }
  return null;
}

export function validateReceipt(values, config) {
  const errors = {
    fn: validateFn(values.fn),
    fd: validateFiscalInt(values.fd, 'ФД'),
    fp: validateFiscalInt(values.fp, 'ФП'),
    purchased_at: validatePurchasedAt(values.purchased_at, config),
    amount: validateAmount(values.amount, config.minAmount),
    photo: validatePhoto(values.photo ?? null, config.photoMaxBytes),
  };
  return Object.fromEntries(
      Object.entries(errors).filter(([, message]) => message));
}
