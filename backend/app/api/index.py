# The compact inline harness intentionally keeps HTML, CSS, and JavaScript in one asset.
# ruff: noqa: E501
INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Interview Studio WebSocket Harness</title>
<style>
body{font:16px system-ui;max-width:760px;margin:2rem auto;padding:0 1rem;background:#f5f7fb;color:#172033}
main{background:white;border:1px solid #dce2ee;border-radius:12px;padding:1rem}
#messages{min-height:300px;white-space:pre-wrap}.status{color:#526078}
form{display:flex;gap:.5rem}input{flex:1;padding:.75rem}button{padding:.75rem 1rem}
.user{color:#174ea6}.assistant{color:#176b3a}.error{color:#a11}
</style>
</head>
<body><main><h1>Interview Studio</h1><p id="status" class="status">Connecting…</p>
<section id="messages" aria-live="polite"></section>
<form id="form"><label for="answer">Your answer</label>
<input id="answer" autocomplete="off" disabled><button disabled>Send</button></form></main>
<script>
const status=document.querySelector('#status'),messages=document.querySelector('#messages');
const form=document.querySelector('#form'),input=document.querySelector('#answer'),button=form.querySelector('button');
const scheme=location.protocol==='https:'?'wss':'ws';
const ws=new WebSocket(`${scheme}://${location.host}/api/v1/interviews/browser-harness/ws`);
let assistant;
function line(kind,text){const p=document.createElement('p');p.className=kind;p.textContent=text;messages.append(p);return p}
ws.onopen=async()=>{status.textContent='Connected';
 try{const response=await fetch('/api/v1/interviews/browser-harness/history');
  if(!response.ok)throw new Error('History is unavailable');
  const history=await response.json();
  history.messages.forEach(message=>line(message.role,message.text));
  if(history.messages.length===0)ws.send(JSON.stringify({type:'session.start',payload:{}}));
  else{input.disabled=false;button.disabled=false;status.textContent='Connected · resumed'}
 }catch(error){line('error',error.message);ws.send(JSON.stringify({type:'session.start',payload:{}}))}
};
ws.onmessage=({data})=>{const event=JSON.parse(data);
 if(event.type==='session.ready'){input.disabled=false;button.disabled=false}
 if(event.type==='assistant.text.delta'){if(!assistant)assistant=line('assistant','');assistant.textContent+=event.payload.text}
 if(event.type==='assistant.text.completed'){assistant=null}
 if(event.type==='error'){line('error',event.payload.message)}
};
ws.onclose=()=>{status.textContent='Disconnected';input.disabled=true;button.disabled=true};
form.onsubmit=e=>{e.preventDefault();const text=input.value.trim();if(!text)return;
 line('user',text);ws.send(JSON.stringify({type:'user.text',payload:{text}}));input.value=''};
</script></body></html>"""
