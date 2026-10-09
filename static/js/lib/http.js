export let JsonResult;

export function csrfToken(form = null) {
  const input = form?.querySelector('input[name="csrfmiddlewaretoken"]');
  if (input) return input.value;
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : '';
}

export async function submitForm(form) {
  const response = await fetch(form.action, {
    method: 'POST',
    body: new FormData(form),
    credentials: 'same-origin',
    headers: {
      'Accept': 'application/json',
      'X-CSRFToken': csrfToken(form),
      'X-Requested-With': 'fetch',
    },
  });
  return {ok: response.ok, status: response.status, data: await readJson(response)};
}

export async function getJson(url) {
  const response = await fetch(url, {
    credentials: 'same-origin',
    headers: {'Accept': 'application/json'},
  });
  return {ok: response.ok, status: response.status, data: await readJson(response)};
}

async function readJson(response) {
  const type = response.headers.get('Content-Type') || '';
  if (!type.includes('application/json')) return {};
  try {
    return await response.json();
  } catch (e) {
    return {};
  }
}
