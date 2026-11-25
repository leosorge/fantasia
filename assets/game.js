const {questions}=JSON.parse(document.getElementById("data").textContent);
const canvas=document.getElementById("course");
const ctx=canvas.getContext("2d");
const gate=document.getElementById("gate");
const hud=document.getElementById("hud");
const floor=270;
const gates=questions.map((_,i)=>730+i*660);
const finish=gates.at(-1)+420;
let x,y,vy,coins,lives,stage,phase,objects,last;
function status(){hud.textContent="Monete "+coins+" · Scudi "+lives+" · Porte "+stage+"/"+questions.length;}
function panel(title,body){
  gate.replaceChildren();
  gate.hidden=false;
  const h=document.createElement("h2");h.textContent=title;
  const p=document.createElement("p");p.textContent=body;
  if(title)gate.append(h);
  gate.append(p);
}
function button(label,action){
  const b=document.createElement("button");b.type="button";b.textContent=label;b.onclick=action;gate.append(b);
}
function reset(){
  x=40;y=floor;vy=0;coins=0;lives=3;stage=0;last=0;phase="ready";
  objects=gates.flatMap((g,i)=>{
    const start=i===0?0:gates[i-1];
    return [{x:start+215,type:"spike"},{x:start+465,type:"spike"},
      ...[115,190,270,370,455,535,585].map((offset,j)=>({
        x:start+offset,y:[1,2,4,5].includes(j)?floor-57:floor-22,type:"coin"
      }))];
  });
  panel("","Salta gli ostacoli e raccogli monete. Rispondi ai checkpoint per raggiungere il traguardo.");
  button("Gioca",()=>{gate.hidden=true;phase="run";canvas.focus();requestAnimationFrame(loop);});
  status();paint();
}
function jump(){
  if(phase==="run"&&y>=floor){vy=-405;}
}
document.getElementById("jump").onclick=()=>{jump();canvas.focus();};
canvas.onpointerdown=jump;
window.addEventListener("keydown",event=>{
  if(["Space","ArrowUp"].includes(event.code)&&phase==="run"){event.preventDefault();jump();}
});
function end(won){
  phase="end";
  panel(won?"Traguardo!":"Missione interrotta",coins+" monete raccolte · "+stage+" checkpoint superati");
  button("Rigioca",reset);
}
function checkpoint(){
  phase="question";
  const q=questions[stage];
  panel("Checkpoint "+(stage+1),q.t);
  q.o.forEach((option,index)=>button(option,()=>{
    if(index!==q.answer)lives--;
    stage++;status();
    panel(index===q.answer?"Rotta confermata":"Scudo perso","Risposta corretta: "+q.o[q.answer]+".");
    if(lives===0){end(false);return;}
    button("Riparti",()=>{gate.hidden=true;phase="run";last=0;canvas.focus();requestAnimationFrame(loop);});
  }));
}
function loop(time){
  if(phase!=="run")return;
  const dt=last?Math.min((time-last)/1000,.035):0;last=time;
  x+=145*dt;vy+=960*dt;y=Math.min(floor,y+vy*dt);
  for(const obj of objects){
    if(obj.used||Math.abs(obj.x-x)>19)continue;
    if(obj.type==="coin"&&Math.abs(obj.y-(y-12))<21){obj.used=true;coins++;status();}
    if(obj.type==="spike"&&y>floor-23){obj.used=true;lives--;status();if(lives===0){end(false);break;}}
  }
  if(phase==="run"&&x>=gates[stage])checkpoint();
  else if(phase==="run"&&x>=finish)end(true);
  paint();
  if(phase==="run")requestAnimationFrame(loop);
}
function paint(){
  const w=canvas.width,h=canvas.height,cam=Math.max(0,x-103);
  ctx.fillStyle="#121841";ctx.fillRect(0,0,w,h);
  for(let i=0;i<36;i++){
    const sx=((i*163-cam*.24)%w+w)%w;
    ctx.fillStyle=i%5===0?"#93faff":"#6974a5";ctx.fillRect(sx,14+(i*53)%189,i%5===0?3:2,2);
  }
  ctx.fillStyle="#75449a";ctx.beginPath();ctx.arc(350-cam*.025,82,37,0,Math.PI*2);ctx.fill();
  ctx.fillStyle="#29376a";ctx.fillRect(0,floor,w,h-floor);
  ctx.fillStyle="#72f6d3";ctx.fillRect(0,floor,w,4);
  ctx.strokeStyle="#6b79b4";
  for(let i=-1;i<13;i++){ctx.beginPath();ctx.moveTo(i*44-cam%44,floor+8);ctx.lineTo(i*44-cam%44-30,h);ctx.stroke();}
  for(const obj of objects){
    const px=obj.x-cam;if(px<-30||px>w+30||obj.used)continue;
    if(obj.type==="coin"){
      ctx.fillStyle="#ffdb58";ctx.beginPath();ctx.arc(px,obj.y,8,0,Math.PI*2);ctx.fill();
      ctx.strokeStyle="#ad6c29";ctx.stroke();ctx.fillStyle="#fff0a2";ctx.fillRect(px-1,obj.y-4,2,8);
    }else{
      ctx.fillStyle="#ff7e85";ctx.beginPath();ctx.moveTo(px-14,floor);ctx.lineTo(px,floor-27);ctx.lineTo(px+14,floor);ctx.fill();
    }
  }
  for(const target of [...gates,finish]){
    const px=target-cam;if(px<-40||px>w+40)continue;
    ctx.strokeStyle=target===finish?"#ffe270":"#5ce3f1";ctx.lineWidth=5;
    ctx.strokeRect(px-12,floor-74,24,73);ctx.lineWidth=1;
  }
  const px=x-cam;
  ctx.fillStyle="#fdd769";ctx.fillRect(px-24,y-13,11,6);
  ctx.fillStyle="#bcf6ff";ctx.beginPath();ctx.moveTo(px+20,y-13);ctx.lineTo(px-13,y-28);ctx.lineTo(px-10,y-4);ctx.closePath();ctx.fill();
  ctx.fillStyle="#4376d8";ctx.fillRect(px-5,y-19,12,7);
}
reset();
