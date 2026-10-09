const REQUIRED_KEYS = ['t', 's', 'fn', 'i', 'fp'];
const TIME = /^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})?$/;

export class QrParseError extends Error {}

export let QrData;

export function parseQr(raw) {
  const text = String(raw ?? '').trim().replace(/^\?/, '');
  const params = new Map();
  for (const [key, value] of new URLSearchParams(text)) {
    if (!params.has(key.toLowerCase())) {
      params.set(key.toLowerCase(), value.trim());
    }
  }
  const missing = REQUIRED_KEYS.filter((key) => !params.get(key));
  if (missing.length) {
    throw new QrParseError(
        `В строке QR-кода нет параметров: ${missing.join(', ')}.`);
  }
  const time = TIME.exec(params.get('t'));
  if (!time) throw new QrParseError('Неверная дата в QR-коде.');
  const [, y, mo, d, h, mi] = time;
  const amount = Number(params.get('s'));
  if (!Number.isFinite(amount)) {
    throw new QrParseError('Неверная сумма в QR-коде.');
  }
  return {
    fn: params.get('fn'),
    fd: params.get('i'),
    fp: params.get('fp'),
    purchasedAt: `${y}-${mo}-${d}T${h}:${mi}`,
    amount: amount.toFixed(2),
  };
}
