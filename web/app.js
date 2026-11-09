// Ask Albert: sends a question to the local server (src/web.py) and shows what the answerer did:
// the passages found, a refused first answer if any, the answer and its checked citations.

const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const CHECK = '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>';

const OFFERS = ['Free delivery from €35', 'Returns within 21 days', 'Card only'];
$('.ann-track').innerHTML = OFFERS.map((o) => `<span>${o}</span><i></i>`).join('').repeat(8);

// The demo's questions: a normal one, one in French, one the help centre does not answer, and the trap.
const CHIPS = [
  { k: 'Returns', q: 'How many days do I have to return an item?' },
  { k: 'En français', q: 'Puis-je payer par virement bancaire ?' },
  { k: 'Late parcel', q: 'My parcel is 3 days past its estimated delivery date. What can I do?' },
  { k: 'Not in the help centre', q: 'What is the phone number of customer service?' },
  { k: 'The trap · tampered page', q: 'Can I return the OZNaturals Retinol Serum after opening it?', trap: true },
];
$('#chips').innerHTML = CHIPS.map((c, i) => `<button class="chip" data-i="${i}" type="button"><small>${esc(c.k)}</small>${esc(c.q)}</button>`).join('');
$('#chips').addEventListener('click', (e) => {
  const b = e.target.closest('.chip');
  if (!b || busy) return;
  const c = CHIPS[b.dataset.i];
  if (c.trap) $('#injected').checked = true;
  send(c.q);
});

const ERRORS = {
  network: 'The API could not be reached. Check the internet connection and ask again.',
  credit: 'The API key has no credit left (and no working second key in .env).',
  key: 'The API key was refused: check the keys in .env.',
  api: 'The API answered an error. Ask again in a moment.',
  server: 'The local server does not answer. Is the terminal window still open?',
};

const log = $('#log');
let busy = false;
const add = (html) => { log.insertAdjacentHTML('beforeend', html); log.scrollTop = log.scrollHeight; return log.lastElementChild; };

function passagesHtml(ps, injected) {
  const codes = ps.map((p) => `<code class="${p.seller ? 'seller' : ''}" title="${esc(p.text)}…">${esc(p.id)}</code>`).join('');
  return `<div class="found"><span>${ps.length} passages found${injected ? ' · tampered seller page in the index' : ''}</span>${codes}</div>`;
}

async function send(question) {
  question = question.trim();
  if (!question || busy) return;
  busy = true;
  $('#send').disabled = true;
  $('.hello')?.remove();
  $('#q').value = '';
  const injected = $('#injected').checked;
  add(`<div class="msg user">${esc(question)}</div>`);
  const typing = add('<div class="typing" aria-label="Albert is answering"><i></i><i></i><i></i></div>');
  let r;
  try {
    const res = await fetch('/api/ask', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Ask-Albert': '1' }, body: JSON.stringify({ question, injected }) });
    r = await res.json();
  } catch {
    r = { error: 'server' };
  }
  typing.remove();
  if (r.passages) add(passagesHtml(r.passages, r.injected));
  if (r.error) {
    add(`<div class="msg error">${esc(ERRORS[r.error] || ERRORS.api)}</div>`);
  } else {
    for (const why of r.refused || []) {
      add(`<div class="msg attempt"><b>An answer was refused by code</b> and asked again: ${esc(why)}</div>`);
    }
    const meta = `<div class="meta">${r.cached ? 'already asked: from the cache, $0.000' : `${r.latency.toFixed(1)} s · $${r.cost.toFixed(4)}`} · ${esc(r.model)} · few-shot</div>`;
    if (r.given_up) {
      add(`<div class="msg final idk">No answer sent: every attempt broke a rule, so nothing reaches the customer.${meta}</div>`);
    } else if (r.answerable) {
      const cites = r.citations.map((c) => `<code>${esc(c)}</code>`).join('');
      add(`<div class="msg final"><div>${esc(r.answer)}</div><div class="cites">${cites}<span class="ok">${CHECK} citations checked</span></div>${meta}</div>`);
    } else {
      add(`<div class="msg final idk"><div>${esc(r.answer)}</div><div class="cites"><span class="ok" style="color:var(--ink-2)">The help centre does not say: no guess, no citation</span></div>${meta}</div>`);
    }
    $('#s-time').textContent = r.cached ? 'cache' : `${r.latency.toFixed(1)} s`;
    $('#s-cost').textContent = `$${r.cost.toFixed(4)}`;
  }
  busy = false;
  $('#send').disabled = false;
  $('#q').focus();
}

$('#form').addEventListener('submit', (e) => { e.preventDefault(); send($('#q').value); });
fetch('/api/info').then((r) => r.json()).then((i) => { $('#s-model').textContent = i.model; }).catch(() => {});
$('#q').focus();
