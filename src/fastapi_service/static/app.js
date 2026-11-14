'use strict';

const $ = (selector) => document.querySelector(selector);
const dialog = $('#task-dialog');
let apiPrefix = '';
let token = null;
let editingId = null;
const statusLabels = {todo: '待办', in_progress: '进行中', done: '已完成'};

function notify(message, error = false) {
  const notice = $('#notice');
  notice.textContent = message;
  notice.classList.toggle('error', error);
  notice.hidden = false;
}

async function request(path, options = {}, authenticated = true) {
  const headers = new Headers(options.headers || {});
  if (authenticated && token) headers.set('Authorization', `Bearer ${token}`);
  const response = await fetch(`${apiPrefix}${path}`, {...options, headers});
  if (!response.ok) {
    if (response.status === 401 && authenticated) logout('登录已失效，请重新登录。');
    const data = await response.json().catch(() => null);
    throw new Error(data?.error?.message || data?.detail || `请求失败（${response.status}）`);
  }
  return response.status === 204 ? null : response.json();
}

function logout(message = '') {
  token = null;
  $('#workspace').hidden = true;
  $('#auth-panel').hidden = false;
  $('#logout').hidden = true;
  $('#current-user').textContent = '';
  $('#password').value = '';
  if (message) notify(message, true);
}

async function login() {
  const username = $('#username').value.trim();
  const password = $('#password').value;
  const result = await request('/auth/token', {
    method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: new URLSearchParams({username, password}),
  }, false);
  token = result.access_token;
  const user = await request('/auth/me');
  $('#current-user').textContent = user.username;
  $('#password').value = '';
  $('#auth-panel').hidden = true;
  $('#workspace').hidden = false;
  $('#logout').hidden = false;
  $('#notice').hidden = true;
  await loadTasks();
}

function render(tasks) {
  const body = $('#tasks');
  body.replaceChildren();
  $('#count').textContent = tasks.length;
  $('#empty').hidden = tasks.length !== 0;
  $('#table-wrap').hidden = tasks.length === 0;
  for (const task of tasks) {
    const row = document.createElement('tr');
    const title = document.createElement('td');
    const name = document.createElement('span');
    name.className = 'item-name';
    name.textContent = task.title;
    title.append(name);
    if (task.description) {
      const description = document.createElement('span');
      description.className = 'item-description';
      description.textContent = task.description;
      title.append(description);
    }
    const state = document.createElement('td');
    const badge = document.createElement('span');
    badge.className = `status-badge ${task.status}`;
    badge.textContent = statusLabels[task.status] || task.status;
    state.append(badge);
    const created = document.createElement('td');
    created.textContent = new Intl.DateTimeFormat('zh-CN', {dateStyle: 'medium', timeStyle: 'short'}).format(new Date(task.created_at));
    const actions = document.createElement('td');
    actions.className = 'actions';
    const edit = document.createElement('button');
    edit.type = 'button'; edit.className = 'text-button'; edit.textContent = '编辑';
    edit.setAttribute('aria-label', `编辑 ${task.title}`);
    edit.addEventListener('click', () => openForm(task));
    const remove = document.createElement('button');
    remove.type = 'button'; remove.className = 'text-button delete'; remove.textContent = '删除';
    remove.setAttribute('aria-label', `删除 ${task.title}`);
    remove.addEventListener('click', () => deleteTask(task));
    actions.append(edit, remove);
    row.append(title, state, created, actions);
    body.append(row);
  }
}

async function loadTasks() {
  $('#loading').hidden = false;
  $('#empty').hidden = true;
  $('#table-wrap').hidden = true;
  try {
    render(await request('/tasks'));
    return true;
  } catch (error) {
    $('#count').textContent = '—';
    notify(`无法加载任务：${error.message}`, true);
    return false;
  } finally {
    $('#loading').hidden = true;
  }
}

function openForm(task = null) {
  editingId = task?.id ?? null;
  $('#task-form').reset();
  $('#form-error').hidden = true;
  $('#dialog-title').textContent = task ? '编辑任务' : '新建任务';
  $('#title').value = task?.title ?? '';
  $('#description').value = task?.description ?? '';
  $('#status').value = task?.status ?? 'todo';
  dialog.showModal();
  $('#title').focus();
}

async function deleteTask(task) {
  if (!window.confirm(`确定删除“${task.title}”吗？此操作无法撤销。`)) return;
  try {
    await request(`/tasks/${task.id}`, {method: 'DELETE'});
    if (await loadTasks()) notify('任务已删除。');
  } catch (error) { notify(`删除失败：${error.message}`, true); }
}

$('#auth-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  $('#auth-error').hidden = true;
  try { await login(); } catch (error) { $('#auth-error').textContent = `登录失败：${error.message}`; $('#auth-error').hidden = false; }
});
$('#register').addEventListener('click', async () => {
  if (!$('#auth-form').reportValidity()) return;
  $('#auth-error').hidden = true;
  try {
    await request('/auth/register', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username: $('#username').value.trim(), password: $('#password').value})}, false);
    await login();
  } catch (error) { $('#auth-error').textContent = `注册或登录失败：${error.message}`; $('#auth-error').hidden = false; }
});
$('#task-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const title = $('#title').value.trim();
  if (!title) { $('#form-error').textContent = '请输入标题。'; $('#form-error').hidden = false; return; }
  $('#save').disabled = true;
  $('#form-error').hidden = true;
  try {
    const isEditing = editingId !== null;
    await request(isEditing ? `/tasks/${editingId}` : '/tasks', {
      method: isEditing ? 'PATCH' : 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({title, description: $('#description').value.trim() || null, status: $('#status').value}),
    });
    dialog.close();
    if (await loadTasks()) notify(isEditing ? '任务已更新。' : '任务已创建。');
  } catch (error) { $('#form-error').textContent = `保存失败：${error.message}`; $('#form-error').hidden = false; }
  finally { $('#save').disabled = false; }
});
$('#new-task').addEventListener('click', () => openForm());
$('#empty-create').addEventListener('click', () => openForm());
$('#close-dialog').addEventListener('click', () => dialog.close());
$('#cancel').addEventListener('click', () => dialog.close());
$('#logout').addEventListener('click', () => logout());
$('#refresh').addEventListener('click', () => { $('#notice').hidden = true; loadTasks(); });
fetch('/frontend-config').then((response) => { if (!response.ok) throw new Error('配置加载失败'); return response.json(); }).then((config) => { apiPrefix = config.api_prefix; logout(); }).catch(() => { $('#auth-panel').hidden = false; notify('无法加载应用配置，请刷新重试。', true); });
