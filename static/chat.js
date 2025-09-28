const msgs = document.getElementById('msgs');
const input = document.getElementById('msg');
const send  = document.getElementById('send');
const userId = 'guest'; // يمكنك توليد معرف من الكوكيز/الوقت

function add(role, text){
  const row = document.createElement('div');
  row.className = 'msg ' + (role === 'user' ? 'user' : 'bot');
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;
  row.appendChild(bubble);
  msgs.appendChild(row);
  msgs.scrollTop = msgs.scrollHeight;
}

async function ask(q){
  add('user', q);
  input.value = '';
  const resp = await fetch('/chat', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({message:q, user:userId})
  });
  const data = await resp.json();
  add('bot', data.answer || 'لم أفهم سؤالك.');
}

send.onclick = () => {
  const q = (input.value || '').trim();
  if (q) ask(q);
};
input.addEventListener('keydown', e => {
  if (e.key === 'Enter') send.click();
});
