const $ = (selector) => document.querySelector(selector);
const state = { documents: [], selected: new Set(), task: 'qa', busy: false, result: null, status: null };
const number = (n) => new Intl.NumberFormat('pt-BR').format(n);
let toastTimer;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  let data;
  try { data = await response.json(); } catch { throw new Error('O servidor retornou uma resposta inesperada.'); }
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Revise os campos e tente novamente.');
  return data;
}

function toast(message, error = false) {
  const node = $('#toast');
  node.textContent = message;
  node.className = error ? 'toast error' : 'toast';
  node.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { node.hidden = true; }, error ? 10000 : 5500);
}

function setBusy(busy, analyzing = false) {
  state.busy = busy;
  $('#submit-button').disabled = busy;
  $('#upload').disabled = busy;
  $('#demo-button').disabled = busy;
  document.querySelectorAll('.delete-document, .document-item input, .task-tab').forEach((n) => { n.disabled = busy; });
  $('#loading').hidden = !(busy && analyzing);
  if (busy && analyzing) {
    $('#welcome').hidden = true;
    $('#result').hidden = true;
    $('#loading-title').textContent = state.task === 'summary' ? 'Lendo o documento, parte a parte…' : 'Consultando o material…';
    $('#loading-description').textContent = state.task === 'summary'
      ? 'Cada trecho entra em um resumo parcial. Depois, reunimos as partes em uma síntese. Isso pode levar alguns minutos.'
      : 'Selecionando trechos relevantes e preparando uma resposta com fontes.';
  }
}

function renderDocuments() {
  const target = $('#documents');
  target.replaceChildren();
  $('#doc-count').textContent = state.documents.length;
  $('#library-empty').hidden = state.documents.length > 0;
  for (const doc of state.documents) {
    const row = element('div', `document-item${state.selected.has(doc.id) ? ' selected' : ''}`);
    const checkbox = element('input');
    checkbox.type = 'checkbox';
    checkbox.id = `doc-${doc.id}`;
    checkbox.checked = state.selected.has(doc.id);
    checkbox.disabled = state.busy;
    checkbox.addEventListener('change', () => {
      if (checkbox.checked) state.selected.add(doc.id); else state.selected.delete(doc.id);
      renderDocuments();
    });
    const label = element('label', 'document-info');
    label.htmlFor = checkbox.id;
    label.append(element('span', 'document-name', doc.name), element('small', '', `${number(doc.chunks)} trechos · ~${number(doc.tokens)} tokens`));
    const remove = element('button', 'delete-document', '×');
    remove.setAttribute('aria-label', `Remover ${doc.name}`);
    remove.disabled = state.busy;
    remove.addEventListener('click', async () => {
      setBusy(true);
      try {
        await api(`/api/documents/${encodeURIComponent(doc.id)}`, { method: 'DELETE' });
        state.selected.delete(doc.id);
        await loadDocuments();
        toast('Documento removido da biblioteca.');
      } catch (error) { toast(error.message, true); } finally { setBusy(false); }
    });
    row.append(checkbox, label, remove);
    target.append(row);
  }
  const count = state.selected.size;
  $('#selection-label').textContent = count ? `${count} documento${count > 1 ? 's' : ''} selecionado${count > 1 ? 's' : ''}` : 'Nenhum documento selecionado';
}

async function loadDocuments(newId) {
  state.documents = await api('/api/documents');
  const available = new Set(state.documents.map((d) => d.id));
  state.selected = new Set([...state.selected].filter((id) => available.has(id)));
  if (newId) state.selected.add(newId);
  renderDocuments();
}

function openSource(source) {
  $('#source-title').textContent = source.name;
  $('#source-meta').textContent = `Página/seção ${source.page} · Trecho ${source.position} · ~${number(source.tokens)} tokens`;
  $('#source-text').textContent = source.text;
  $('#source-dialog').showModal();
}

function traceDetails(trace) {
  const details = element('details');
  details.append(element('summary', '', 'Ver decisão de roteamento e chamadas'));
  if (!trace.length) details.append(element('p', 'muted', 'Sem chamada ao modelo: a busca não encontrou evidência lexical.'));
  trace.forEach((call, i) => {
    const row = element('div', 'trace-item');
    row.append(element('b', '', `${i + 1}. ${call.model} · ${call.status === 'simulated' ? 'simulado' : call.status === 'ok' ? 'concluído' : 'falhou'}`));
    row.append(element('p', '', call.reason));
    row.append(element('small', '', `Entrada estimada: ${number(call.estimated_input_tokens)} tokens · ${number(call.latency_ms || 0)} ms${call.input_tokens != null ? ` · Uso real: ${number(call.input_tokens)} entrada / ${number(call.output_tokens)} saída` : ''}`));
    details.append(row);
  });
  return details;
}

function downloadResult() {
  const result = state.result;
  if (!result) return;
  const content = `# Lume · ${state.task === 'summary' ? 'Resumo' : 'Consulta'}\n\nModo: ${result.metrics.mode === 'demo' ? 'demonstração extrativa, sem LLM' : 'OpenRouter'}\n\n${result.answer}\n\n## Limitações\n${result.limitations.map((s) => `- ${s}`).join('\n')}\n\n## Fontes\n${result.sources.map((s) => `### ${s.name} · página/seção ${s.page} · trecho ${s.position}\n${s.text}`).join('\n\n')}\n\n## Métricas\n\n\`\`\`json\n${JSON.stringify(result.metrics, null, 2)}\n\`\`\`\n`;
  const url = URL.createObjectURL(new Blob([content], { type: 'text/markdown;charset=utf-8' }));
  const link = element('a');
  link.href = url; link.download = 'lume-analise.md'; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function renderResult(result) {
  state.result = result;
  const root = $('#result');
  root.replaceChildren();
  const heading = element('div', 'section-heading');
  heading.append(element('h2', '', state.task === 'qa' ? 'Uma leitura do seu material' : 'Do detalhe à síntese'));
  const download = element('button', 'outline-button', 'Exportar ↓');
  download.addEventListener('click', downloadResult);
  heading.append(download);
  root.append(heading, element('p', 'answer-label', result.metrics.mode === 'demo' ? 'DEMONSTRAÇÃO · EXTRAÇÃO LOCAL, SEM LLM' : 'RESPOSTA GERADA VIA OPENROUTER'));
  root.append(element('div', 'answer-body', result.answer));
  if (result.limitations.length) {
    const limits = element('div', 'limitations');
    result.limitations.forEach((text) => limits.append(element('p', '', text)));
    root.append(limits);
  }
  if (result.sources.length) {
    root.append(element('h3', 'sources-heading', `${result.sources.length} fontes indicadas · abra para conferir`));
    const grid = element('div', 'source-grid');
    result.sources.forEach((source, i) => {
      const button = element('button', 'source-button');
      button.append(element('b', '', `${i + 1}. ${source.name}`), element('small', '', `Página/seção ${source.page} · trecho ${source.position} ↗`));
      button.addEventListener('click', () => openSource(source));
      grid.append(button);
    });
    root.append(grid);
  }
  const metrics = result.metrics;
  const strip = element('div', 'metrics-strip');
  const items = [
    [`${metrics.selected_chunks}/${metrics.total_chunks}`, 'trechos processados'],
    [number(metrics.selected_tokens_estimated), 'tokens de conteúdo estimados'],
    [metrics.calls, metrics.mode === 'demo' ? 'chamadas simuladas' : 'tentativas de chamada'],
    [metrics.cost_usd == null ? '—' : `US$ ${metrics.cost_usd.toFixed(5)}`, 'custo informado pelo provedor'],
  ];
  items.forEach(([value, label]) => { const item = element('div'); item.append(element('strong', '', value), element('span', '', label)); strip.append(item); });
  root.append(strip, traceDetails(metrics.trace));
  if (result.sections.length) {
    const sections = element('details');
    sections.append(element('summary', '', `Resumos parciais · ${result.sections.length} partes`));
    result.sections.forEach((part) => { const node = element('div', 'section-summary'); node.append(element('strong', '', part.title), document.createTextNode(part.answer)); sections.append(node); });
    root.append(sections);
  }
  $('#welcome').hidden = true;
  root.hidden = false;
}

document.querySelectorAll('.task-tab').forEach((tab) => tab.addEventListener('click', () => {
  state.task = tab.dataset.task;
  document.querySelectorAll('.task-tab').forEach((n) => { const active = n === tab; n.classList.toggle('active', active); n.setAttribute('aria-selected', String(active)); });
  $('#task-panel').setAttribute('aria-labelledby', tab.id);
  const summary = state.task === 'summary';
  $('#question-label').textContent = summary ? 'Qual é o objetivo da sua leitura?' : 'O que você quer descobrir?';
  $('#question').placeholder = summary ? 'Ex.: Resuma os critérios, prazos e perspectivas para estudantes interessados no programa.' : 'Ex.: Quais são os prazos e critérios para solicitar uma bolsa?';
  $('#question').value = '';
  $('#composer-hint').textContent = summary ? 'Selecione um documento · até 120 trechos' : 'Respostas baseadas nos documentos selecionados';
  $('#submit-button').replaceChildren(document.createTextNode(summary ? 'Criar síntese ' : 'Encontrar resposta '), element('span', '', '↗'));
  $('#suggestions').hidden = summary;
  $('#result').hidden = true;
  $('#welcome').hidden = false;
  state.result = null;
}));

document.querySelectorAll('[data-prompt]').forEach((button) => button.addEventListener('click', () => {
  $('#question').value = button.dataset.prompt;
  $('#question').focus();
}));

$('#demo-button').addEventListener('click', async () => {
  setBusy(true);
  try {
    const doc = await api('/api/demo', { method: 'POST' });
    await loadDocuments(doc.id);
    $('#question').value = state.task === 'qa' ? 'Qual é o prazo para solicitar uma bolsa?' : 'Resuma os critérios, prazos e perspectivas para estudantes.';
    $('#question').focus();
    toast('Exemplo adicionado. Envie a pergunta para explorar o material.');
  } catch (error) { toast(error.message, true); } finally { setBusy(false); }
});

$('#upload').addEventListener('change', async (event) => {
  const files = [...event.target.files];
  if (!files.length) return;
  setBusy(true);
  try {
    for (const file of files) {
      if (file.size > 2000000) { toast(`${file.name}: o limite é de 2 MB.`, true); continue; }
      const form = new FormData(); form.append('file', file);
      const result = await api('/api/documents', { method: 'POST', body: form });
      await loadDocuments(result.id);
      toast(result.duplicate ? 'Este conteúdo já está na biblioteca.' : `${file.name} adicionado à biblioteca.`);
    }
  } catch (error) { toast(error.message, true); } finally { event.target.value = ''; setBusy(false); }
});

$('#analyze-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  if (state.busy) return;
  if (!state.selected.size) return toast('Adicione e selecione um documento na biblioteca.', true);
  if (state.task === 'summary' && state.selected.size !== 1) return toast('Para resumir, selecione exatamente um documento.', true);
  const question = $('#question').value.trim();
  if (question.length < 3) { $('#question').focus(); return toast('Escreva uma pergunta ou um objetivo de leitura.', true); }
  setBusy(true, true);
  try {
    const result = await api('/api/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ task: state.task, question, document_ids: [...state.selected] }) });
    renderResult(result);
  } catch (error) { toast(error.message, true); $('#welcome').hidden = false; }
  finally { setBusy(false); }
});

$('#question').addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) { event.preventDefault(); $('#analyze-form').requestSubmit(); }
});

$('#history-button').addEventListener('click', async () => {
  try {
    const runs = await api('/api/runs');
    const root = $('#history-list'); root.replaceChildren();
    if (!runs.length) root.append(element('p', 'muted', 'Suas análises aparecerão aqui.'));
    runs.forEach((run) => {
      const row = element('div', 'history-row');
      const date = new Date(`${run.created_at.replace(' ', 'T')}Z`);
      row.append(element('strong', '', `${run.task === 'qa' ? 'Consulta' : 'Resumo'} · ${run.status === 'ok' ? 'concluído' : 'falhou'} · ${run.mode === 'demo' ? 'demonstração' : 'OpenRouter'}`));
      row.append(element('small', '', `${date.toLocaleString('pt-BR')} · ${run.calls} tentativa(s) · ${number(run.latency_ms)} ms`), traceDetails(run.trace));
      root.append(row);
    });
    $('#history').hidden = false;
    $('#history').scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (error) { toast(error.message, true); }
});

$('#close-history').addEventListener('click', () => { $('#history').hidden = true; });
$('#close-source').addEventListener('click', () => $('#source-dialog').close());
$('#close-settings').addEventListener('click', () => $('#settings-dialog').close());
$('#settings-button').addEventListener('click', () => $('#settings-dialog').showModal());
for (const dialog of document.querySelectorAll('dialog')) dialog.addEventListener('click', (event) => { if (event.target === dialog) { const box = dialog.getBoundingClientRect(); if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) dialog.close(); } });

async function init() {
  try {
    const [status, docs] = await Promise.all([api('/api/status'), api('/api/documents')]);
    state.status = status; state.documents = docs; state.selected = new Set(docs.map((d) => d.id));
    renderDocuments();
    $('#mode-badge').textContent = status.mode === 'demo' ? 'Demonstração · sem LLM' : 'OpenRouter configurado';
    $('#mode-description').textContent = status.mode === 'demo' ? 'Modo demonstração ativo. As respostas são trechos extraídos localmente.' : 'Chave do OpenRouter configurada. As análises enviam os trechos selecionados ao provedor externo.';
    $('#context-budget').textContent = number(status.input_budget);
    const models = $('#model-list');
    for (const [key, title] of [['fast', 'Perguntas factuais e resumos parciais'], ['deep', 'Análise e síntese global'], ['fallback', 'Modelo de fallback']]) {
      const row = element('div', 'model-row'); row.append(element('span', '', title), document.createTextNode(status.models[key])); models.append(row);
    }
  } catch (error) { $('#mode-badge').textContent = 'Sem conexão'; toast(error.message, true); }
}
init();
